"""Provider sync: seasons, rounds, teams, matches and results from the data provider.

Three kinds of run (each one writes a row in sync_runs):
  season  - current season + every match of it, for each active competition
  window  - matches from a few days around today, all competitions in one request
  rescore - matches scored in the last 24 h, in case the provider corrected a result

All decisions live in domain/sync_plan.py (pure), all SQL in db/queries/sync.py.
This module glues them to the provider. It is blocking code: the scheduler and
the admin endpoint run it in a worker thread.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from db.queries import sync as q
from db.queries.results import score_match, void_match_predictions
from domain import sync_plan as plan
from domain.rescore import RESCORE_WINDOW_HOURS
from services.providers import get_provider

logger = logging.getLogger(__name__)

RUN_KINDS = ("season", "window", "rescore")

SCHEDULER_TICK_SECONDS = 60
SCHEDULER_START_DELAY_SECONDS = 10

# keep sync_runs.error readable
MAX_ERROR_LENGTH = 2000

SyncBusy = q.SyncBusy


class UnknownCompetition(Exception):
    pass


class CompetitionNotSyncable(Exception):
    # inactive or without a provider
    pass


@dataclass
class Counters:
    upserted: int = 0   # match rows written
    scored: int = 0     # matches (re)scored
    skipped: int = 0    # matches we decided not to write

    def add(self, other: "Counters") -> None:
        self.upserted += other.upserted
        self.scored += other.scored
        self.skipped += other.skipped


class RequestMeter:
    # counts provider requests made during one run (delta of provider.requests_made)

    def __init__(self):
        self._start: dict[str, int] = {}
        self._providers: dict[str, object] = {}

    def provider(self, name: str):
        if name not in self._providers:
            provider = get_provider(name)
            self._providers[name] = provider
            self._start[name] = getattr(provider, "requests_made", 0)
        return self._providers[name]

    def total(self) -> int:
        return sum(getattr(p, "requests_made", 0) - self._start[n] for n, p in self._providers.items())


# ---------- champion ----------

def resolve_champion(season_id: int, team_id: int) -> dict | None:
    # scores league bonus "champion" answers of this season
    # kept as a small wrapper so tests can swap it out
    from db.queries.league_bonus import resolve_season_champion

    return resolve_season_champion(season_id, team_id)


def check_champion(season_id: int, api_winner_external_id: str | None = None) -> bool:
    # finds the season winner and resolves the champion questions, True when we called resolve_champion
    context = q.get_season_context(season_id)
    if context is None or context["status"] == "archived":
        return False

    questions = q.list_champion_questions(season_id)
    if not questions:
        return False

    api_team_id = None
    if api_winner_external_id is not None:
        api_team_id = q.get_team_id_by_external_id(context["provider"], api_winner_external_id)
        if api_team_id is None:
            logger.warning("season %s winner %s is not in teams yet", season_id, api_winner_external_id)

    final_team_id = None
    if context["kind"] in ("cup", "national_cup"):
        final = q.get_final_match(season_id)
        if final is not None:
            side = plan.match_winner_side(
                final["decided_by"], final["home_goals"], final["away_goals"],
                final["home_goals_et"], final["away_goals_et"], final["home_pens"], final["away_pens"],
            )
            if side is not None:
                final_team_id = final["home_team_id"] if side == "home" else final["away_team_id"]

    champion = plan.pick_champion(context["kind"], api_team_id, final_team_id)
    if champion is None:
        return False

    # nothing to do when every question already points at this team
    if all(question["resolved_team_id"] == champion for question in questions):
        return False

    result = resolve_champion(season_id, champion)
    logger.info("season %s champion is team %s -> %s", season_id, champion, result)
    return True


def _check_champion_safely(season_id: int, api_winner_external_id: str | None = None) -> None:
    # the champion is a bonus on top of the sync: whatever goes wrong here (database,
    # league bonus code) must not fail the competition's sync or lose its counters.
    # it is tried again on the next run, as long as the questions stay unresolved
    try:
        check_champion(season_id, api_winner_external_id)
    except Exception:
        logger.exception("champion check of season %s failed", season_id)


# ---------- writing provider matches ----------

def apply_matches(cur, season_id: int, provider_name: str, matches: list, now: datetime) -> Counters:
    # one season's matches, inside the caller's transaction:
    # teams + season_teams, rounds, matches, then scoring / voiding where the plan says so
    counters = Counters()
    if not matches:
        return counters

    existing = q.list_existing_matches(cur, provider_name, [m.external_id for m in matches])

    plans = []
    for m in matches:
        row = existing.get(m.external_id)
        current = None
        if row is not None:
            current = plan.ExistingMatch(
                row["status"], row["home_goals"], row["away_goals"], row["scored_at"],
                row["decided_by"], row["home_goals_et"], row["away_goals_et"], row["home_pens"], row["away_pens"],
            )
        incoming = plan.IncomingMatch(
            status=m.status, home_goals=m.home_goals, away_goals=m.away_goals,
            teams_known=m.home is not None and m.away is not None,
            kickoff_known=m.kickoff_at is not None,
            decided_by=m.decided_by, home_goals_et=m.home_goals_et, away_goals_et=m.away_goals_et,
            home_pens=m.home_pens, away_pens=m.away_pens,
        )
        match_plan = plan.plan_match_update(current, incoming, now)
        if match_plan.action == "skip":
            counters.skipped += 1
        if match_plan.warn:
            logger.warning("match %s: %s (status %s)", m.external_id, match_plan.reason, m.status)
        plans.append(match_plan)

    team_ids = _upsert_teams(cur, season_id, provider_name, matches)
    round_ids = _upsert_rounds(cur, season_id, matches, plans)

    rows = []
    touched_ids = []
    extras_rows = []
    for m, match_plan in zip(matches, plans):
        if match_plan.action == "touch":
            touched_ids.append(existing[m.external_id]["id"])
        elif match_plan.action == "meta":
            extras_rows.append((
                existing[m.external_id]["id"], m.decided_by, m.home_goals_et, m.away_goals_et, m.home_pens, m.away_pens,
            ))
        elif match_plan.action in ("insert", "full"):
            # a new row that is already finished has no predictions: stamp scored_at with the
            # kickoff so it stays outside the rescore window (like migration 006 does)
            scored_at = m.kickoff_at if match_plan.action == "insert" and m.status == "finished" else None
            rows.append((
                season_id, round_ids[plan.round_key(m.phase, m.matchday)], provider_name, m.external_id,
                team_ids[m.home.external_id], team_ids[m.away.external_id],
                m.kickoff_at, m.kickoff_confirmed, m.status,
                m.home_goals, m.away_goals, m.home_goals_et, m.away_goals_et, m.home_pens, m.away_pens,
                m.decided_by, scored_at,
            ))

    match_ids = q.upsert_matches(cur, rows)
    q.touch_matches(cur, touched_ids)
    q.update_match_extras(cur, extras_rows)
    counters.upserted = len(match_ids) + len(extras_rows)

    for m, match_plan in zip(matches, plans):
        if match_plan.score:
            score_match(cur, match_ids[m.external_id], m.home_goals, m.away_goals)
            counters.scored += 1
        if match_plan.void:
            void_match_predictions(cur, match_ids[m.external_id])
    return counters


def _upsert_teams(cur, season_id: int, provider_name: str, matches: list) -> dict[str, int]:
    team_rows: dict[str, tuple] = {}
    groups: dict[str, str] = {}
    for m in matches:
        if m.home is None or m.away is None:
            continue
        for team in (m.home, m.away):
            team_rows[team.external_id] = (
                provider_name, team.external_id, team.name, team.short_name, team.crest_url, team.is_national,
            )
            if m.phase == "group" and m.group_name:
                groups[team.external_id] = m.group_name

    team_ids = q.upsert_teams(cur, list(team_rows.values()))
    q.upsert_season_teams(cur, [(season_id, team_id, groups.get(ext)) for ext, team_id in team_ids.items()])
    return team_ids


def _upsert_rounds(cur, season_id: int, matches: list, plans: list) -> dict[tuple, int]:
    # only matches that get written need a round
    round_rows: dict[tuple, tuple] = {}
    for m, match_plan in zip(matches, plans):
        if match_plan.action not in ("insert", "full"):
            continue
        key = plan.round_key(m.phase, m.matchday)
        if key not in round_rows:
            round_rows[key] = (season_id, key[0], key[1], m.round_name, plan.round_sort_order(*key))
    return q.upsert_rounds(cur, list(round_rows.values()))


def _score_leftovers(code: str | None) -> int:
    # finished + full score + never scored: normally nothing, a safety net after a crash
    with q.transaction() as cur:
        rows = q.list_unscored_finished(cur, code)
        for row in rows:
            score_match(cur, row["id"], row["home_goals"], row["away_goals"])
    if rows:
        logger.info("scored %d leftover finished matches", len(rows))
    return len(rows)


# ---------- the three kinds of run ----------

def _sync_competition_season(comp: dict, meter: RequestMeter, now: datetime) -> Counters:
    provider = meter.provider(comp["provider"])
    season = provider.get_current_season(comp["provider_ref"])

    # an archived season is never touched, so don't download its matches (the big request)
    with q.transaction() as cur:
        stored = q.get_season_for_sync(cur, comp["id"], season.provider_ref, season.label)
    if stored is not None and stored["status"] == "archived":
        logger.warning("%s season %s is archived, not syncing it", comp["code"], season.label)
        return Counters()

    matches = provider.get_season_matches(comp["provider_ref"], season.provider_ref)
    today = now.astimezone(UTC).date()

    with q.transaction() as cur:
        # read again inside the write transaction, the status may have changed meanwhile
        stored = q.get_season_for_sync(cur, comp["id"], season.provider_ref, season.label)
        stored_status = stored["status"] if stored else None
        if stored_status == "archived":
            return Counters()

        status = plan.season_status(stored_status, season.starts_on, season.ends_on, season.is_current, today)
        if stored is None:
            season_id = q.insert_season(
                cur, comp["id"], season.label, season.provider_ref,
                season.starts_on, season.ends_on, status, comp["default_scoring_profile_id"],
            )
            logger.info("%s: new season %s (%s)", comp["code"], season.label, status)
        else:
            season_id = stored["id"]
            q.update_season(cur, season_id, season.provider_ref, season.starts_on, season.ends_on, status)
            if status != stored_status:
                logger.info("%s: season %s is now %s", comp["code"], season.label, status)

        # one active season per competition: the new one pushes the old one to the archive
        if status == "active":
            archived = q.archive_other_active_seasons(cur, comp["id"], season_id)
            if archived:
                logger.info("%s: archived %d older season(s)", comp["code"], archived)

        counters = apply_matches(cur, season_id, provider.name, matches, now)

    _check_champion_safely(season_id, season.winner_external_id)
    logger.info("%s season sync: %d written, %d scored", comp["code"], counters.upserted, counters.scored)
    return counters


def _run_season(comps: list[dict], meter: RequestMeter, now: datetime, errors: list[str]) -> Counters:
    total = Counters()
    for comp in comps:
        try:
            total.add(_sync_competition_season(comp, meter, now))
        except Exception as exc:
            # one broken competition must not stop the others
            logger.exception("season sync of %s failed", comp["code"])
            errors.append(f"{comp['code']}: {exc}")
    return total


def _apply_for_season(comp: dict, season_ref: str | None, matches: list, provider_name: str, now: datetime) -> Counters:
    # matches of one competition + season from a window run
    season = q.get_open_season_by_ref(comp["id"], season_ref) if season_ref else None
    if season is None:
        logger.info("%s: no open season %s in the database, %d matches left out", comp["code"], season_ref, len(matches))
        return Counters(skipped=len(matches))

    with q.transaction() as cur:
        counters = apply_matches(cur, season["id"], provider_name, matches, now)

    if any(m.phase == "final" and m.status == "finished" for m in matches):
        _check_champion_safely(season["id"])
    return counters


def _is_busy(now: datetime) -> bool:
    rows = q.list_busy_match_candidates(now - plan.BUSY_AFTER_KICKOFF, now + plan.IMMINENT_BEFORE_KICKOFF)
    return plan.has_live_or_imminent(rows, now)


def _run_window(comps: list[dict], meter: RequestMeter, now: datetime, errors: list[str]) -> Counters:
    total = Counters()
    busy = _is_busy(now)
    date_from, date_to = plan.window_dates(now, busy)
    logger.info("window %s .. %s (%s)", date_from, date_to, "live or imminent" if busy else "idle")

    by_provider: dict[str, list[dict]] = {}
    for comp in comps:
        by_provider.setdefault(comp["provider"], []).append(comp)

    for provider_name, group in by_provider.items():
        provider = meter.provider(provider_name)
        by_ref = {c["provider_ref"]: c for c in group}
        try:
            matches = provider.get_matches_window(list(by_ref), date_from, date_to)
        except Exception as exc:
            logger.exception("window request to %s failed", provider_name)
            errors.append(f"{provider_name}: {exc}")
            continue

        grouped: dict[tuple, list] = {}
        for m in matches:
            comp = by_ref.get(m.competition_ref)
            if comp is not None:
                grouped.setdefault((comp["id"], m.season_ref), []).append(m)

        for (comp_id, season_ref), season_matches in grouped.items():
            comp = next(c for c in group if c["id"] == comp_id)
            try:
                total.add(_apply_for_season(comp, season_ref, season_matches, provider_name, now))
            except Exception as exc:
                logger.exception("window sync of %s failed", comp["code"])
                errors.append(f"{comp['code']}: {exc}")
    return total


def _run_rescore(code: str | None, meter: RequestMeter, now: datetime, errors: list[str]) -> Counters:
    total = Counters()
    candidates = q.list_rescore_candidates(code, RESCORE_WINDOW_HOURS)

    by_provider: dict[str, list[dict]] = {}
    for row in candidates:
        by_provider.setdefault(row["provider"], []).append(row)

    for provider_name, rows in by_provider.items():
        provider = meter.provider(provider_name)
        season_of = {r["external_id"]: r["season_id"] for r in rows}
        try:
            matches = provider.get_matches_by_ids(list(season_of))
        except Exception as exc:
            logger.exception("rescore request to %s failed", provider_name)
            errors.append(f"{provider_name}: {exc}")
            continue

        by_season: dict[int, list] = {}
        for m in matches:
            season_id = season_of.get(m.external_id)
            if season_id is not None:
                by_season.setdefault(season_id, []).append(m)

        for season_id, season_matches in by_season.items():
            try:
                with q.transaction() as cur:
                    total.add(apply_matches(cur, season_id, provider_name, season_matches, now))
                if any(m.phase == "final" and m.status == "finished" for m in season_matches):
                    _check_champion_safely(season_id)
            except Exception as exc:
                logger.exception("rescore of season %s failed", season_id)
                errors.append(f"season {season_id}: {exc}")
    return total


# ---------- entry point ----------

def run_sync(kind: str, competition_code: str | None = None, now: datetime | None = None) -> dict:
    """Run one sync and return its sync_runs row.

    Raises SyncBusy when another run is in progress, UnknownCompetition /
    CompetitionNotSyncable for a bad competition code. Errors during the run
    are logged and stored in the row, never raised.
    """
    if kind not in RUN_KINDS:
        raise ValueError(f"unknown sync kind: {kind}")
    now = now or datetime.now(UTC)

    comps = q.list_sync_competitions(competition_code)
    competition_id = None
    if competition_code is not None:
        if not comps:
            if q.get_competition_by_code(competition_code) is None:
                raise UnknownCompetition(competition_code)
            raise CompetitionNotSyncable(competition_code)
        competition_id = comps[0]["id"]

    run_id = q.start_run(kind, competition_id, plan.STALE_RUN_MINUTES)
    meter = RequestMeter()
    counters = Counters()
    errors: list[str] = []
    try:
        if kind == "season":
            counters = _run_season(comps, meter, now, errors)
        elif kind == "window":
            counters = _run_window(comps, meter, now, errors)
        else:
            counters = _run_rescore(competition_code, meter, now, errors)
        counters.scored += _score_leftovers(competition_code)
    except Exception as exc:
        logger.exception("sync run %s (%s) failed", run_id, kind)
        errors.append(str(exc))

    status = "error" if errors else "ok"
    error_text = "; ".join(errors)[:MAX_ERROR_LENGTH] if errors else None
    try:
        q.finish_run(run_id, status, meter.total(), counters.upserted, counters.scored, error_text)
    except Exception:
        # the row stays 'running' and is cleaned up as stale later
        logger.exception("could not close sync run %s", run_id)
    logger.info(
        "sync run %s (%s) %s: %d requests, %d written, %d scored",
        run_id, kind, status, meter.total(), counters.upserted, counters.scored,
    )
    return q.get_run(run_id)


# ---------- scheduler ----------

def load_scheduler_state(now: datetime) -> plan.SchedulerState:
    last = q.get_last_runs()

    def last_of(kind: str) -> plan.LastRun | None:
        row = last.get(kind)
        return plan.LastRun(row["started_at"], row["status"], row["consecutive_errors"]) if row else None

    return plan.SchedulerState(
        now=now,
        last_season=last_of("season"),
        last_window=last_of("window"),
        last_rescore=last_of("rescore"),
        busy=_is_busy(now),
        competitions_without_season=q.count_competitions_without_season(),
        rescore_candidates=len(q.list_rescore_candidates(None, RESCORE_WINDOW_HOURS)),
    )


def scheduler_tick(now: datetime | None = None) -> str | None:
    # decide from the persisted history what is due and run it, returns the kind that ran
    now = now or datetime.now(UTC)
    kind = plan.decide_next_run(load_scheduler_state(now))
    if kind is None:
        return None
    try:
        run_sync(kind, None, now=now)
    except SyncBusy:
        logger.info("sync %s is due but another run is in progress", kind)
        return None
    return kind


async def run_scheduler(tick_seconds: int = SCHEDULER_TICK_SECONDS, start_delay: int = SCHEDULER_START_DELAY_SECONDS):
    # background loop started from main.py, never raises (except on cancel)
    logger.info("sync scheduler started")
    await asyncio.sleep(start_delay)
    while True:
        try:
            # to_thread so blocking http + sql never freezes the event loop
            await asyncio.to_thread(scheduler_tick)
        except Exception:
            logger.exception("sync scheduler tick failed")
        await asyncio.sleep(tick_seconds)
