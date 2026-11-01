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

// CompetitionRef (logo_url = emblem z football-data, null gdy brak; front ładuje go przez /img/crest)
{ "id": 2, "code": "EPL", "name": "Premier League", "logo_url": "https://crests.football-data.org/PL.png" }

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
  "my_prediction": MyPrediction | null,
  "provisional_points": null,                      // tylko live + mój typ: „gdyby się teraz skończyło” (domain.live_points), nigdy nie zapisywane
  "provisional_hit_type": null                     // exact | diff | tendency | miss, jak wyżej
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
| GET | `/matches/{id}/context` | Kontekst do typowania (z naszych wyników, `domain.match_context`). Dla obu drużyn: miejsce w tabeli sezonu (tylko fazy `regular`/`league_phase`; `rank: null` gdy drużyna ma < 3 mecze, `points: null` gdy nie gra w tabeli), forma z ostatnich 5 zakończonych meczów sezonu (`W`/`R`/`P`, od najnowszego, bez tego meczu), do 3 ostatnich meczów bezpośrednich z całej bazy. Nieznany mecz → 404 „Mecz nie istnieje”. |
| GET | `/seasons/{id}/teams` | Drużyny sezonu (`season_teams`), po nazwie. Lista `Team` + `group_name`. |
| GET | `/seasons/{id}/ranking` | Ranking sezonu (wszyscy użytkownicy z ≥1 typem w sezonie). Dla archiwum Mundialu dolicza stare bonusy (`bonus_predictions`, `group_advance_predictions` z tym `season_id`), żeby sumy były takie jak w starym rankingu. |
| GET | `/feed?days=7` | Mecze z obserwowanych rozgrywek (gdy użytkownik nic nie obserwuje — ze wszystkich aktywnych) z oknem: od teraz − 3 h do teraz + `days` dni (1–30, domyślnie 7), plus wszystkie `live`. Lista `Match`. |
| POST | `/predictions` | Bez zmian w body. Zmiana: odrzuca 409 każdy mecz, dla którego `is_prediction_allowed(kickoff_at, now, status)` = false (dziś da się typować mecz przełożony). Odpowiedź dostaje `hit_type`. |
| GET | `/predictions/mine?season_id=` | Jak dziś + pola `season_id`, `competition_code`, `round_name`, `hit_type`. Bez `season_id` — wszystkie typy. |

```jsonc
// GET /competitions → lista
{ "id": 2, "code": "EPL", "name": "Premier League", "country": "Anglia", "kind": "league",
  "logo_url": "https://crests.football-data.org/PL.png", "is_active": true, "is_followed": false,
  "current_season": SeasonRef | null }   // sezon active, a gdy brak — najnowszy

// GET /competitions/{id}/seasons, GET /seasons/{id}
{ "id": 5, "label": "2026/27", "status": "active", "starts_on": "2026-08-21", "ends_on": "2027-05-30",
  "competition": CompetitionRef }

// GET /matches/{id}/context
{
  "match_id": 1201,
  "home": { "team_id": 1, "rank": 4, "points": 1, "played": 4, "form": ["P", "P", "P", "R"] },
  "away": { "team_id": 2, "rank": 1, "points": 12, "played": 4, "form": ["W", "W", "W", "W"] },
  "head_to_head": [ { "match_id": 990, "kickoff_at": "2026-10-09T15:00:00Z",
                      "home_team_id": 2, "away_team_id": 1, "home_goals": 1, "away_goals": 0 } ]
}

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
| GET | `/leagues/preview/{code}` | **Publiczny, bez logowania** — podgląd zaproszenia. Kod porównywany bez względu na wielkość liter. Zwraca `{"name": str, "owner_nick": str, "member_count": int, "competitions": [str]}` (polskie nazwy rozgrywek z zakresu ligi; pusta lista = wszystkie rozgrywki). Bez id, maili i kodu. Nieznany kod → 404 `"Nie znaleziono ligi z tym kodem"`. |
| GET | `/leagues/{id}/ranking?season_id=` | Członek ligi (403). Z `season_id`: ranking tego sezonu (sezon musi należeć do rozgrywki z zakresu ligi, inaczej 422) + punkty bonusów ligowych tej ligi dla tego sezonu. Bez `season_id`: suma ze wszystkich sezonów `active` w zakresie ligi + bonusy ligowe tych sezonów. Lista `RankingEntry`, wszyscy członkowie (także z 0 pkt), plus tabela na żywo: `live_points` (punkty „gdyby się teraz skończyło” z meczów `live` w zakresie ligi; w trybie `coupon` tylko mecze z kuponów, joker ×2), `live_total` = `total_points` + `live_points`, `live_rank` = miejsce wg `live_total` (ten sam tiebreak). Bez meczu live: `live_points: 0`, `live_total`/`live_rank` = `null`. Kolejność i `rank` zawsze oficjalne (`domain/ranking.with_live_ranking`). |
| GET | `/leagues/{id}/badges?season_id=` | Członek ligi (403, nieznana liga 404). Sezony jak w rankingu ligi (z `season_id` jeden sezon z zakresu, inaczej 404/422; bez — aktywne sezony z zakresu). Liczone w locie (`domain/league_badges.py`), bez tabeli. Zwraca `{"unit": "round"\|"coupon", "finished_picks": int, "badges": [{"code", "title", "emoji", "description", "user_ids": [int], "value": int}], "streaks": [{"user_id", "nick", "current_rounds", "best_rounds", "current_matches"}]}`. `unit`: w trybie `scope` jednostką serii jest kolejka (`rounds`, tylko te, które ktoś z ligi typował), w trybie `coupon` kupon tygodnia (i liczą się tylko mecze z kuponów). Seria „bez pudła” = kolejne zakończone jednostki, w których każdy rozliczony typ dał > 0 pkt; brak typu w jednostce przerywa serię, jednostki z meczem `scheduled`/`live`/`suspended` są pomijane. `current_matches` = ile ostatnich rozliczonych typów z rzędu za > 0 pkt. Odznaki (kolejność stała, remis = wszyscy dostają, brak odznaki gdy nikt się nie kwalifikuje): `exact_king` (najwięcej dokładnych), `prophet` (najlepsza skuteczność w %, min. 10 rozliczonych typów), `contrarian` (najwięcej trafionych rozstrzygnięć, które typowała mniej niż połowa typujących ligi), `streak` (najdłuższa seria, min. 2), `grumbler` (najwięcej typów za 0 pkt). |

## Bonusy ligowe — agent D

Pytanie (`league_bonus_questions`) dotyczy jednego sezonu. Rodzaje (`kind`): `champion` („kto wygra sezon”, rozstrzyga synchronizacja / admin aplikacji, jedno na sezon w lidze) i `team_pick` (migracja 010: własna treść `title` od właściciela, `answers_count` = ile drużyn wybiera gracz i ile może być poprawnych, rozstrzyga właściciel; dowolnie wiele na sezon). Odpowiedź gracza = jeden wiersz `league_bonus_answers` na wybraną drużynę, punkty za każdą trafioną (`domain.league_bonus.calculate_pick_points`).

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/leagues/{id}/bonus-questions` | Członek ligi (403). Lista pytań, najnowszy termin pierwszy. |
| POST | `/leagues/{id}/bonus-questions` | Właściciel (403). Body `{"season_id", "kind": "champion" \| "team_pick", "points": 1..100, "deadline_at", "title": null, "answers_count": 1}`. `team_pick`: `title` 3–120 znaków po przycięciu (422 „Podaj treść pytania” / długość), `answers_count` 1–10 (422); `champion`: `answers_count` musi być 1, `title` ignorowany. `deadline_at` w przyszłości (422), sezon `upcoming`/`active` (422), rozgrywka sezonu w zakresie ligi (422). Drugie pytanie `champion` o ten sam sezon w lidze → 409. → 201 z pytaniem. |
| DELETE | `/leagues/{id}/bonus-questions/{qid}` | Właściciel, tylko przed terminem (409 po terminie) → 204. |
| PUT | `/leagues/{id}/bonus-questions/{qid}/answer` | Członek. Body `{"team_ids": [..]}` (albo stare `{"team_id"}` = jedna drużyna). Dokładnie `answers_count` różnych drużyn (422 „Wybierz dokładnie N drużyn” / „Każda drużyna może być wybrana tylko raz”). Tylko przed terminem (409, `domain.league_bonus.is_bonus_answer_allowed`). Każda drużyna musi być w `season_teams` sezonu (422). Odpowiedź zastępowana w całości → 200 z `my_answer`. |
| POST | `/leagues/{id}/bonus-questions/{qid}/resolve` | Właściciel (403), tylko `team_pick` (422 dla `champion`), tylko po terminie (409). Body `{"team_ids": [..]}` — od 1 do `answers_count` różnych drużyn z sezonu (422). Zapisuje poprawne drużyny, `resolved_at`, punktuje każdą wybraną drużynę graczy; ponowne wywołanie = korekta. → 200 z pytaniem. |
| POST | `/admin/seasons/{id}/champion` | Admin. Body `{"team_id"}` — ręczne rozstrzygnięcie / korekta. Wywołuje `resolve_season_champion`. → `{"questions_resolved": n, "answers_scored": m}`. |

```jsonc
// pytanie
{ "id": 4,
  "season": { "id": 5, "label": "2026/27", "competition": CompetitionRef },
  "kind": "champion",              // champion | team_pick
  "title": null,                   // team_pick: "Kto spadnie z Premier League?"
  "answers_count": 1,              // ile drużyn wybiera gracz
  "points": 20,                    // team_pick: za każdą trafioną drużynę
  "deadline_at": "2026-11-30T22:59:59Z", "is_open": true,
  "resolved_team": Team | null,    // pierwsza z resolved_teams
  "resolved_teams": [ Team ],      // champion: mistrz, team_pick: poprawne drużyny
  "resolved_at": null,
  "my_answer": { "team": Team, "teams": [ Team ], "points_awarded": null } | null,   // points = suma
  "answers": [ { "user_id": 3, "nick": "ola", "team": Team, "teams": [ Team ], "points_awarded": null } ] }
  // answers: pusta lista przed terminem (nie zdradzamy typów), pełna po terminie, jeden wpis na gracza
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

## Kupon tygodnia

Specyfikacja: [rozwoj/spec-kupon-tygodnia.md](rozwoj/spec-kupon-tygodnia.md). Tydzień = poniedziałek 00:00 – niedziela 23:59 czasu polskiego (`domain.coupon.week_start`). Dobór meczów: `domain.coupon.pick_coupon`, SQL: `db/queries/coupon.py`, sklejanie: `services/coupons.py`.
„Organizator” = właściciel ligi albo członek z `is_admin`. Nieznana liga → 404, nie członek → 403, nie organizator → 403.

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/leagues/{id}/coupon?week=YYYY-MM-DD` | Członek. `week` = dowolny dzień tygodnia (domyślnie bieżący). Gdy kuponu na **bieżący** tydzień brak, a liga ma `coupon_auto=true`, powstaje w locie (idempotentnie, `UNIQUE (liga, tydzień)`). Tydzień bez meczów = brak kuponu (`coupon_id: null`, `matches: []`) — front pokazuje „przerwa”. Typy członków (`member_predictions`) tylko dla meczów po `kickoff_at` (bez przełożonych). |
| PUT | `/leagues/{id}/coupon` | Organizator, tylko bieżący tydzień. Body `{"match_ids": [...]}` = pełna nowa lista. 422: rozmiar spoza 5–15 („Kupon musi mieć od 5 do 15 meczów”), nieznany mecz, mecz spoza zakresu ligi, mecz spoza tygodnia. 409: dodanie meczu, który już się zaczął (albo przełożonego), usunięcie meczu, który już się zaczął. Zwraca to co GET (`created_by: "owner"`). |
| POST | `/leagues/{id}/coupon/regenerate` | Organizator. Automat układa bieżący tydzień od nowa (rozmiar `coupon_size`), rozpoczęte mecze zostają. `created_by: "auto"`. Zwraca to co GET. |
| GET | `/me/coupon` | Zalogowany. Suma kuponów wszystkich moich lig na bieżący tydzień (brakujące auto-kupony powstają w locie), mecz raz z listą lig. Bez żadnej ligi: „Hity tygodnia” (`source: "hits"`) — `pick_coupon` na obserwowanych rozgrywkach (gdy nic nie obserwuje — wszystkie aktywne), z rozpoczętymi meczami tygodnia, żeby lista nie malała. |
| PATCH | `/leagues/{id}/settings` | Właściciel. Dochodzą pola `ranking_mode` (`scope`/`coupon`), `coupon_size` (5–15), `coupon_auto`. Zmienia się tylko to, co jest w body (`prize_pool_per_person: null` nadal kasuje pulę). → 204. |
| POST | `/leagues` | Opcjonalnie `ranking_mode`, `coupon_size`, `competition_ids` (zakres; nieznane id → 422, liga nie powstaje). Bez nich: domyślne z bazy (`scope`, 10). |
| GET | `/leagues/{id}`, `POST /leagues`, `POST /leagues/join` | Odpowiedź ligi ma pola `ranking_mode`, `coupon_size`, `coupon_auto`. |
| GET | `/leagues/{id}/ranking` | W trybie `coupon` punkty za mecze liczą się tylko z meczów z kuponów tej ligi (bonusy ligowe bez zmian), a mecz-joker członka liczy się ×2. |
| PUT | `/leagues/{id}/coupon/joker` | Członek. Body `{"match_id"}`. Joker bieżącego tygodnia: stawia albo przenosi (`domain.joker.check_joker_set`). 409: liga w trybie `scope` („Joker działa tylko w lidze, w której ranking liczy mecze z kuponu”), mecz już się zaczął, obecny joker stoi na meczu, który się zaczął (nie da się przenieść), joker zmieniony równolegle. 422: mecz spoza kuponu tego tygodnia. Zwraca to co GET kuponu. |
| DELETE | `/leagues/{id}/coupon/joker` | Członek. Zdejmuje jokera bieżącego tygodnia (brak jokera = nic się nie dzieje). 409: tryb `scope` albo mecz z jokerem już się zaczął. Zwraca to co GET kuponu. |
| PUT | `/leagues/{id}/matches/{match_id}/reactions` | Członek. Body `{"target_user_id", "emoji"}`. Emoji pod typem innego członka (`domain.reactions.check_reaction`), jedno na (liga, mecz, autor typu, reagujący) — inne emoji zastępuje poprzednie, to samo jeszcze raz nic nie zmienia. Dozwolone: 🔥 😂 🤡 👏 😱 🙈 (`REACTION_EMOJI`). 422: emoji spoza zestawu („Nie ma takiej reakcji”), własny typ („Nie można reagować na własny typ”). 404: nieznany mecz, mecz spoza kuponów ligi („Tego meczu nie ma na kuponie ligi”), autor nie jest członkiem albo nie typował („Ten gracz nie typował tego meczu”). 409: mecz się jeszcze nie zaczął / przełożony („Na typy można reagować dopiero po rozpoczęciu meczu”). Zwraca `{"match_id", "target_user_id", "reactions": {"🔥": 2}, "my_reaction": "🔥"}`. |
| DELETE | `/leagues/{id}/matches/{match_id}/reactions` | Członek. Body `{"target_user_id"}` (`emoji` opcjonalne, ignorowane). Cofa moją reakcję (brak = nic się nie dzieje). Zwraca to co PUT. Front: drugi klik w to samo emoji = DELETE. |

**Joker** (migracja 010, `domain/joker.py`): raz na kupon (tydzień) członek ligi w trybie `coupon` oznacza jeden mecz kuponu; punkty za ten mecz liczą się ×2 w rankingu ligi (tryb `coupon`) i w wynikach tygodnia (`members[].total_points`, `members[].provisional_points`). `predictions.points_awarded`, rankingi rozgrywek i `member_predictions[].points_awarded` się nie zmieniają. Ligi `scope` ignorują jokery (także zapisane wcześniej). Cudzy joker widoczny dopiero po starcie meczu (`is_joker` w `member_predictions`).

**Reakcje pod typem** (migracja 011, `domain/reactions.py`): każdy typ w `member_predictions` ma `reactions` (emoji → liczba, kolejność jak `REACTION_EMOJI`, `{}` bez reakcji) i `my_reaction` (moje emoji albo `null`). Widać je tylko razem z typami, czyli po starcie meczu.

Generowanie w tle: scheduler synchronizacji (`services/sync.run_scheduler`) co tick woła `services.coupons.coupon_tick`, który najwyżej raz na godzinę, od poniedziałku 06:00 czasu PL, tworzy brakujące kupony lig z `coupon_auto=true`.

```jsonc
// GET /leagues/{id}/coupon (także odpowiedź PUT i regenerate)
{
  "league_id": 1, "week_start": "2026-11-02", "week_end": "2026-11-08",
  "is_current_week": true,
  "coupon_id": 7,                // null = brak kuponu w tym tygodniu
  "created_by": "auto",          // auto | owner | null
  "ranking_mode": "coupon", "coupon_size": 10, "coupon_auto": true,
  "can_edit": true,              // organizator i bieżący tydzień
  "my_joker_match_id": 1205,     // mój joker tego tygodnia, null bez jokera / w lidze scope
  "total": 10,
  "matches": [ Match + {
      "typed_count": 2,          // ilu członków wytypowało
      "member_count": 3,
      "predictions_visible": true,   // mecz się zaczął
      "member_predictions": [ { "user_id": 3, "nick": "ola", "pred_home": 2, "pred_away": 1,
                                "points_awarded": 5, "hit_type": "exact",
                                "provisional_points": null, "provisional_hit_type": null,
                                "is_joker": false,
                                "reactions": { "🤡": 2 }, "my_reaction": "🤡" } ],  // [] przed startem; provisional_* tylko live (bez ×2)
      "league_summary": {        // „średni typ ligi” z member_predictions (domain/league_picks.py), null przed startem / bez typów
        "count": 2, "avg_home": 1.5, "avg_away": 1.0,
        "home_wins": 1, "draws": 1, "away_wins": 0,
        "home_pct": 50, "draw_pct": 50, "away_pct": 0,   // sumują się do 100
        "top_scores": [ { "home": 2, "away": 1 } ],     // najczęstszy dokładny wynik (remisy w liczbie = kilka), [] gdy każdy typ inny
        "top_count": 2 }
  } ],
  "members": [                   // posortowani jak ranking (punkty tygodnia), wszyscy członkowie
    { "rank": 1, "user_id": 3, "nick": "ola", "typed": 7, "total": 10,
      "total_points": 12, "exact_hits": 1, "diff_hits": 2, "scored_predictions": 4,
      "provisional_points": 3 }  // suma „gdyby się teraz skończyło” z meczów live (joker ×2), NIE wliczona w total_points ani w sortowanie
  ]
}

// PUT /leagues/{id}/coupon
{ "match_ids": [1201, 1202, 1205, 1210, 1213] }

// GET /me/coupon
{
  "source": "leagues",           // leagues | hits
  "week_start": "2026-11-02", "week_end": "2026-11-08",
  "typed": 3, "total": 10,
  "next_deadline": "2026-11-04T20:00:00Z",   // najbliższy otwarty mecz bez mojego typu, null gdy brak
  "matches": [ Match + { "leagues": [ { "id": 1, "name": "Biuro",
                                        "ranking_mode": "coupon", "is_my_joker": false } ] } ]   // [] dla hits
}

// PUT /leagues/{id}/coupon/joker
{ "match_id": 1205 }

// PATCH /leagues/{id}/settings (każde pole opcjonalne)
{ "ranking_mode": "coupon", "coupon_size": 8, "coupon_auto": true, "prize_pool_per_person": 20 }

// POST /leagues
{ "name": "Biuro", "ranking_mode": "coupon", "coupon_size": 10, "competition_ids": [2, 5] }
```

## Obrazki — proxy herbów

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/img/crest?url=` | Publiczny (bez logowania). Zwraca obrazek spod `url`, ale tylko `https://crests.football-data.org/...` (inny host, schemat, port albo login w URL → **400** „Niedozwolony adres obrazka”). Pobiera raz przez `httpx` (timeout 5 s, bez przekierowań, tylko `image/*` do 2 MB), potem serwuje z pamięci (LRU, 500 obrazków) albo z dysku (`CREST_CACHE_DIR`, domyślnie katalog tymczasowy systemu, `/tmp/czutka-crests`). Odpowiedź: oryginalny `Content-Type` + `Cache-Control: public, max-age=604800, immutable`. Błąd po stronie football-data (status ≠ 200, nie obrazek, timeout) → **502** „Nie udało się pobrać obrazka”, bez zapisu do cache. |

Front buduje adres w `src/utils/imageProxy.js`: `${VITE_API_URL || '/api'}/img/crest?url=<encodeURIComponent(crest_url)>`; adresy spoza football-data idą bez zmian. Service worker przepuszcza te żądania do zwykłego cache przeglądarki.

## Podział plików (żeby agenci się nie zderzali)

| Właściciel | Pliki |
|---|---|
| A | `services/sync.py`, `domain/sync_plan.py` (+ wykrywanie mistrza), `db/queries/sync.py`, `db/queries/results.py`, `routers/admin_sync.py`, `services/providers/*`, `main.py` (job + rejestracja routerów), migracja `007_*` jeśli potrzebna |
| B | `routers/competitions.py` (też `/seasons/*`, `/feed`), `db/queries/competitions.py`, `db/queries/ranking.py` (nowe funkcje, stare zostają), `routers/predictions.py`, `db/queries/predictions.py`, `routers/leagues.py` + `db/queries/leagues.py` (zakres i ranking ligi), migracja `008_*` |
| D | `routers/league_bonus.py`, `db/queries/league_bonus.py`, `domain/league_bonus.py`, migracja `009_*` |
| wspólne | `schemas/models.py` — każdy dopisuje własną sekcję na końcu pliku (`# --- <obszar> ---`). `main.py` — B i D dodają tylko swoje `include_router`. `db/queries/__init__.py` — nikt nie dotyka; nowe funkcje importujemy z modułu (`from db.queries.sync import ...`). |
