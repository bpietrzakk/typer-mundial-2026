# Kontrakt API — wiele rozgrywek (czutka)

Wspólna umowa dla backendu i frontu na etap „synchronizacja → endpointy → front → bonusy ligowe”.
Model danych: [data-model.md](data-model.md), zasady punktacji: [scoring.md](scoring.md), źródło danych: [data-source.md](data-source.md).

Zasady ogólne:
- Wszystkie endpointy wymagają zalogowania (cookie `access_token`), chyba że napisano inaczej. Brak → 401.
- „Admin” = `get_admin_user` (email w `ADMIN_EMAILS`). „Właściciel ligi” = `private_leagues.owner_user_id`. „Członek ligi” = wiersz w `private_league_members`.
- Komunikaty błędów (`detail`) po polsku. Daty w ISO 8601 UTC.
- Stare endpointy (`GET /matches`, `GET /ranking`, `GET /ranking/{league_id}`, `/bonus/*`, `/matches/bootstrap`) zostają bez zmian jako archiwum Mundialu, dopóki front z nich nie zrezygnuje.

## Wspólne kształty

```jsonc
// Team
{ "id": 1, "name": "Arsenal", "short_name": "ARS", "crest_url": "https://..." }

// CompetitionRef
{ "id": 2, "code": "EPL", "name": "Premier League" }

// SeasonRef
{ "id": 5, "label": "2026/27", "status": "active" }   // upcoming | active | archived

// MyPrediction (null gdy brak typu)
{ "pred_home": 2, "pred_away": 1, "points_awarded": 3, "hit_type": "diff" }  // points/hit_type null do rozliczenia

// Match
{
  "id": 1201,
  "competition": CompetitionRef,
  "season_id": 5,
  "round": { "id": 77, "phase": "regular", "matchday": 9, "name": "Kolejka 9" },
  "kickoff_at": "2026-10-31T15:00:00Z",
  "kickoff_confirmed": true,
  "status": "scheduled",          // scheduled | live | finished | postponed | suspended | cancelled | awarded
  "home_team": Team,
  "away_team": Team,
  "home_goals": null, "away_goals": null,          // finished = wynik po 90 min, live = bieżący
  "home_goals_et": null, "away_goals_et": null,    // po dogrywce (gdy była)
  "home_pens": null, "away_pens": null,
  "decided_by": null,                              // regular | extra_time | penalties
  "can_predict": true,                             // domain.match_status.is_open_for_predictions
  "my_prediction": MyPrediction | null
}

// RankingEntry (nowe rankingi)
{ "rank": 1, "user_id": 3, "nick": "ola", "total_points": 41, "exact_hits": 4, "diff_hits": 6, "scored_predictions": 20 }
```

Sortowanie i miejsca w rankingu: zawsze `domain.ranking.sort_ranking` (punkty, dokładne, różnice, nick; remisy dzielą miejsce 1,1,3).
Typy meczów `cancelled` / `awarded` nie liczą się nigdzie.

## Rozgrywki, sezony, mecze — agent B

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/competitions` | Rozgrywki widoczne w aplikacji: `is_active = true` albo mające jakikolwiek sezon. Kolejność `sort_order`. |
| POST | `/competitions/{id}/follow` | Obserwuj (idempotentne) → 204. Nieznana rozgrywka → 404. |
| DELETE | `/competitions/{id}/follow` | Przestań obserwować (idempotentne) → 204. |
| GET | `/competitions/{id}/seasons` | Sezony rozgrywki, najnowszy pierwszy. |
| GET | `/seasons/{id}` | Szczegóły sezonu. |
| GET | `/seasons/{id}/rounds` | Rundy sezonu w kolejności `sort_order`, potem `matchday`. |
| GET | `/seasons/{id}/matches?round_id=` | Mecze sezonu (opcjonalnie jednej rundy), po `kickoff_at`. Lista `Match`. |
| GET | `/seasons/{id}/teams` | Drużyny sezonu (`season_teams`), po nazwie. Lista `Team` + `group_name`. |
| GET | `/seasons/{id}/ranking` | Ranking sezonu (wszyscy użytkownicy z ≥1 typem w sezonie). Dla archiwum Mundialu dolicza stare bonusy (`bonus_predictions`, `group_advance_predictions` z tym `season_id`), żeby sumy były takie jak w starym rankingu. |
| GET | `/feed?days=7` | Mecze z obserwowanych rozgrywek (gdy użytkownik nic nie obserwuje — ze wszystkich aktywnych) z oknem: od teraz − 3 h do teraz + `days` dni (1–30, domyślnie 7), plus wszystkie `live`. Lista `Match`. |
| POST | `/predictions` | Bez zmian w body. Zmiana: odrzuca 409 każdy mecz, dla którego `is_prediction_allowed(kickoff_at, now, status)` = false (dziś da się typować mecz przełożony). Odpowiedź dostaje `hit_type`. |
| GET | `/predictions/mine?season_id=` | Jak dziś + pola `season_id`, `competition_code`, `round_name`, `hit_type`. Bez `season_id` — wszystkie typy. |

```jsonc
// GET /competitions → lista
{ "id": 2, "code": "EPL", "name": "Premier League", "country": "Anglia", "kind": "league",
  "logo_url": null, "is_active": true, "is_followed": false,
  "current_season": SeasonRef | null }   // sezon active, a gdy brak — najnowszy

// GET /competitions/{id}/seasons, GET /seasons/{id}
{ "id": 5, "label": "2026/27", "status": "active", "starts_on": "2026-08-21", "ends_on": "2027-05-30",
  "competition": CompetitionRef }

// GET /seasons/{id}/rounds
{ "id": 77, "phase": "regular", "matchday": 9, "name": "Kolejka 9", "sort_order": 9,
  "match_count": 10, "finished_count": 0,
  "first_kickoff": "2026-10-31T12:30:00Z", "last_kickoff": "2026-11-02T16:30:00Z",
  "is_current": true }   // dokładnie jedna runda w sezonie (gdy sezon ma mecze): pierwsza z meczem scheduled/live, a gdy brak — ostatnia runda z meczami
```

### Ligi prywatne — zakres i ranking (agent B)

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/leagues/{id}/competitions` | Zakres ligi: `{"all": true, "competitions": []}` gdy brak wierszy, inaczej `all=false` i lista `CompetitionRef`. Członek ligi, inaczej 403. |
| PUT | `/leagues/{id}/competitions` | Body `{"competition_ids": [2, 3]}` (pusta lista = wszystkie). Tylko właściciel (403). Nieznane id → 422. Zwraca to co GET. |
| GET | `/leagues/{id}/ranking?season_id=` | Członek ligi (403). Z `season_id`: ranking tego sezonu (sezon musi należeć do rozgrywki z zakresu ligi, inaczej 422) + punkty bonusów ligowych tej ligi dla tego sezonu. Bez `season_id`: suma ze wszystkich sezonów `active` w zakresie ligi + bonusy ligowe tych sezonów. Lista `RankingEntry`, wszyscy członkowie (także z 0 pkt). |

## Bonusy ligowe — agent D

Pytanie (`league_bonus_questions`) dotyczy jednego sezonu, na razie `kind = "champion"`.

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/leagues/{id}/bonus-questions` | Członek ligi (403). Lista pytań, najnowszy termin pierwszy. |
| POST | `/leagues/{id}/bonus-questions` | Właściciel (403). Body `{"season_id", "kind": "champion", "points": 1..100, "deadline_at"}`. `deadline_at` w przyszłości (422), sezon `upcoming`/`active` (422), rozgrywka sezonu w zakresie ligi (422). Duplikat (liga, sezon, kind) → 409. → 201 z pytaniem. |
| DELETE | `/leagues/{id}/bonus-questions/{qid}` | Właściciel, tylko przed terminem (409 po terminie) → 204. |
| PUT | `/leagues/{id}/bonus-questions/{qid}/answer` | Członek. Body `{"team_id"}`. Tylko przed terminem (409, `domain.league_bonus.is_bonus_answer_allowed`). Drużyna musi być w `season_teams` sezonu (422). Upsert → 200 z `my_answer`. |
| POST | `/admin/seasons/{id}/champion` | Admin. Body `{"team_id"}` — ręczne rozstrzygnięcie / korekta. Wywołuje `resolve_season_champion`. → `{"questions_resolved": n, "answers_scored": m}`. |

```jsonc
// pytanie
{ "id": 4,
  "season": { "id": 5, "label": "2026/27", "competition": CompetitionRef },
  "kind": "champion", "points": 20,
  "deadline_at": "2026-11-30T22:59:59Z", "is_open": true,
  "resolved_team": Team | null, "resolved_at": null,
  "my_answer": { "team": Team, "points_awarded": null } | null,
  "answers": [ { "user_id": 3, "nick": "ola", "team": Team, "points_awarded": null } ] }
  // answers: pusta lista przed terminem (nie zdradzamy typów), pełna po terminie
```

Funkcja dla synchronizacji (własność D, woła ją A):
`db.queries.league_bonus.resolve_season_champion(season_id: int, team_id: int) -> dict` — ustawia `resolved_team_id`/`resolved_at` wszystkim pytaniom `champion` tego sezonu i punktuje odpowiedzi (`domain.league_bonus.calculate_champion_answer_points`). Idempotentna; inna drużyna niż zapisana = korekta, przelicza od nowa. Zwraca `{"questions_resolved", "answers_scored"}`.

## Synchronizacja — agent A

Job w tle w `main.py` (zastępuje stary `_poll_results` Mundialu), praca w wątku (`asyncio.to_thread`), blokada w bazie (jeden wiersz `running` w `sync_runs`, migracja 007), żeby dwa procesy nie synchronizowały naraz. Wyłączany przez `SYNC_ENABLED=false`; bez `FOOTBALL_API_KEY` nie startuje.

Rodzaje przebiegów (każdy zapisuje wiersz w `sync_runs`):
- `season` — dla każdej aktywnej rozgrywki z dostawcą: bieżący sezon → upsert `seasons` (poprzedni `active` tej rozgrywki → `archived`), wszystkie mecze sezonu → upsert `teams`, `season_teams`, `rounds`, `matches`. Przy starcie, gdy rozgrywka nie ma aktywnego sezonu, i raz na dobę.
- `window` — mecze z okna dat dla wszystkich aktywnych rozgrywek jednym zapytaniem (dzielone po 10 dni): co 5 min, gdy jest mecz `live` albo mecz z `kickoff_at` w [teraz − 3 h, teraz + 15 min] niezakończony; w przeciwnym razie co 60 min z oknem [wczoraj, +7 dni].
- `rescore` — mecze z `scored_at` w ostatnich 24 h → `get_matches_by_ids`; zmiana wyniku po 90 min (`domain.rescore.should_rescore`) → przeliczenie typów.
- Po każdym upsercie: mecz `finished` z `scored_at IS NULL` → rozliczenie (ta sama ścieżka co `finalize_match`: profil sezonu, `hit_type`, `scored_at`); mecz `cancelled`/`awarded` → typy `points_awarded = NULL`, `hit_type = NULL`.
- Mecze bez znanych obu drużyn (placeholdery fazy pucharowej) są pomijane, dopóki dostawca nie poda drużyn.
- Mecz już rozliczony nigdy nie wraca do `scheduled`/`live` (ignorujemy taki stan od dostawcy, z ostrzeżeniem w logu).
- Mistrz sezonu: `winner` sezonu z API, a dla pucharu zakończony mecz `final` (zwycięzca z uwzględnieniem dogrywki i karnych). Wykryty mistrz → `resolve_season_champion(season_id, team_id)`.

| Metoda | Ścieżka | Opis |
|---|---|---|
| POST | `/admin/sync/run` | Admin. Body `{"kind": "season" \| "window" \| "rescore", "competition_code": null}`. Uruchamia przebieg synchronicznie (w wątku), zwraca wiersz `sync_runs`. Gdy inny przebieg trwa → 409. |
| GET | `/admin/sync/runs?limit=20` | Admin. Ostatnie przebiegi, najnowszy pierwszy. |
| GET | `/admin/competitions` | Admin. Wszystkie rozgrywki: pola z `GET /competitions` + `provider`, `provider_ref`, `last_sync_at`, `last_sync_status`. |
| PATCH | `/admin/competitions/{id}` | Admin. Body `{"is_active": bool}`. Rozgrywka bez dostawcy nie może być włączona (422). |

```jsonc
// sync_runs
{ "id": 12, "kind": "window", "competition_code": null, "status": "ok",
  "started_at": "...", "finished_at": "...", "requests_used": 1,
  "matches_upserted": 14, "matches_scored": 3, "error": null }
```

## Podział plików (żeby agenci się nie zderzali)

| Właściciel | Pliki |
|---|---|
| A | `services/sync.py`, `domain/sync_plan.py` (+ wykrywanie mistrza), `db/queries/sync.py`, `db/queries/results.py`, `routers/admin_sync.py`, `services/providers/*`, `main.py` (job + rejestracja routerów), migracja `007_*` jeśli potrzebna |
| B | `routers/competitions.py` (też `/seasons/*`, `/feed`), `db/queries/competitions.py`, `db/queries/ranking.py` (nowe funkcje, stare zostają), `routers/predictions.py`, `db/queries/predictions.py`, `routers/leagues.py` + `db/queries/leagues.py` (zakres i ranking ligi), migracja `008_*` |
| D | `routers/league_bonus.py`, `db/queries/league_bonus.py`, `domain/league_bonus.py`, migracja `009_*` |
| wspólne | `schemas/models.py` — każdy dopisuje własną sekcję na końcu pliku (`# --- <obszar> ---`). `main.py` — B i D dodają tylko swoje `include_router`. `db/queries/__init__.py` — nikt nie dotyka; nowe funkcje importujemy z modułu (`from db.queries.sync import ...`). |
