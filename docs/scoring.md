# Punktacja i blokada typów

Ten dokument opisuje zasady, według których typ zamienia się w punkty, kiedy można typować i jak rozstrzygamy remisy w rankingu. Cała ta logika to czyste funkcje w [`mundial-backend/domain/`](../mundial-backend/domain/) — bez bazy i bez HTTP, więc każdą regułę da się przetestować jednym wywołaniem funkcji.

## Trzy progi

Za każdy rozliczony mecz typ dostaje punkty za najwyższy trafiony próg:

- **dokładny wynik** — typ 2:1, wynik 2:1;
- **różnica bramek** — typ 2:1, wynik 3:2 (obie różnice +1);
- **wynik meczu** (kto wygrał albo remis) — typ 2:1, wynik 4:0;
- pudło — typ 2:1, wynik 0:2.

Trafiony remis, który nie jest dokładny (typ 1:1, wynik 2:2), zawsze dostaje punkty za różnicę bramek (0 = 0), nigdy tylko za wynik. Tak było od początku i tak zostaje.

Który próg trafiono, mówi `classify_hit()` w `domain/scoring.py` (zwraca `exact`, `diff`, `tendency` albo `miss`), a ile to punktów — `calculate_points()`, która dostaje reguły jako argument. Wartości punktów nie są w kodzie, tylko w profilu punktacji sezonu (tabela w [data-model.md](data-model.md#typy-i-punkty)). `pick_rule()` wybiera z profilu wiersz dla fazy meczu, a jeśli go nie ma — wiersz `default`. Przykład: mecz 1/8 finału Ligi Mistrzów (profil `uefa_cup`, faza `round_of_16`), typ 2:1, wynik 3:2 → próg `diff` → 4 punkty. Ten sam typ w 12. kolejce Premier League (profil `league_default`, faza `regular`, brak osobnego wiersza → `default`) → 3 punkty.

## Liczy się wynik po 90 minutach

Punktujemy wynik po regulaminowym czasie gry z doliczonym czasem. Dogrywka i rzuty karne nie mają znaczenia — finał 1:1 po 90 minutach rozstrzygnięty w karnych to dla typera remis 1:1. Dwumecz to dwa osobne mecze i dwa osobne typy. Skąd bierzemy ten wynik z API, opisuje [data-source.md](data-source.md#wynik-a-dogrywka-i-karne).

## Kiedy można typować

Typ można dodać lub zmienić tylko wtedy, gdy mecz ma status `scheduled`, a jego godzina rozpoczęcia jest w przyszłości (`is_prediction_allowed()` w `domain/predictions.py`, korzysta z `is_open_for_predictions()` w `domain/match_status.py`). Dokładnie w chwili rozpoczęcia jest już za późno. Czas porównujemy w UTC; daty bez strefy czasowej traktujemy jako UTC.

Mecz przełożony (`postponed`) albo przerwany (`suspended`) jest zablokowany, dopóki nie dostanie nowego terminu — wtedy wraca do `scheduled` i typowanie znowu się otwiera. Mecz odwołany (`cancelled`) albo zakończony walkowerem (`awarded`) unieważnia typy: nie dostają punktów i nie liczą się do rankingu (`voids_predictions()`).

Ta sama reguła działa w API w dwóch miejscach. `POST /predictions` sprawdza ją przy każdym zapisie i odrzuca typ kodem 409, gdy mecz jest zamknięty — z komunikatem zależnym od powodu (`prediction_block_reason()` w `domain/prediction_lock.py`: mecz już się rozpoczął, zakończył, został przełożony/przerwany albo odwołany). Listy meczów (`GET /seasons/{id}/matches`, `GET /feed`) pokazują wynik tej samej funkcji w polu `can_predict`, więc front nie musi liczyć czasu ani statusu po swojej stronie. Typ można zmieniać do godziny rozpoczęcia; mecz z `kickoff_confirmed = false` też otwiera się i zamyka według zapisanej godziny.

## Korekty wyników

Dostawcy danych czasem poprawiają wynik po fakcie. Dlatego przez 24 godziny od naliczenia punktów synchronizacja sprawdza zakończone mecze jeszcze raz i jeśli wynik po 90 minutach się zmienił, przelicza typy od nowa (`should_rescore()` w `domain/rescore.py`; długość okna to jedna stała, `RESCORE_WINDOW_HOURS`, której używa też synchronizacja do wyboru meczów do sprawdzenia). Liczenie jest deterministyczne, więc ponowne przeliczenie zawsze daje ten sam wynik dla tych samych danych. Archiwum Mundialu nie jest przeliczane.

## Remisy w rankingu

Ranking sortuje po sumie punktów, przy równej sumie — po liczbie dokładnych trafień, potem po liczbie trafionych różnic bramek, a na końcu alfabetycznie po nicku (`sort_ranking()` w `domain/ranking.py`). Gracze równi w punktach, dokładnych trafieniach i różnicach dzielą miejsce, a kolejne miejsce jest pomijane (1, 1, 3).

## Co liczy się w rankingach

Ranking to zapytanie, nie tabela. Zapytania w `db/queries/ranking.py` sumują po użytkowniku punkty, liczbę dokładnych trafień i różnic oraz liczbę rozliczonych typów — wyłącznie z meczów o statusie `finished`. Typy meczów odwołanych, walkowerów, trwających, przełożonych i niezagranych nie liczą się nigdzie, nawet gdyby miały jakieś punkty. Kolejność i miejsca zawsze ustala `sort_ranking()`, więc każdy ranking w aplikacji rozstrzyga remisy tak samo.

- **Ranking sezonu** (`GET /seasons/{id}/ranking`) obejmuje każdego, kto typował choć jeden mecz tego sezonu. Dla archiwum Mundialu dolicza dawne bonusy globalne (mistrz, awanse z grup) przypisane do sezonu, dlatego sumy są identyczne jak w starym `GET /ranking` — pilnuje tego test integracyjny na danych Mundialu. Użytkownik, który miał tylko bonusy, też się tam znajdzie.
- **Ranking ligi prywatnej** (`GET /leagues/{id}/ranking`) pokazuje wszystkich członków, także z zerem punktów. Z `season_id` liczy jeden sezon (musi należeć do rozgrywki z zakresu ligi), bez niego sumuje wszystkie sezony `active` z zakresu ligi. Do punktów z meczów dochodzą punkty z bonusów ligowych tej ligi (`league_bonus_answers`) za wybrane sezony — bonusy innych lig nigdy się nie mieszają.
- **Zakres ligi** to lista rozgrywek w `private_league_competitions`; pusta lista oznacza wszystkie rozgrywki.
- **Stare rankingi** (`GET /ranking`, `GET /ranking/{league_id}`) są archiwum Mundialu 2026: punkty z meczów liczą tylko typy meczów sezonu `WC 2026` (sezon znajdowany joinem po kodzie rozgrywki i etykiecie, bez zaszytych id), stare bonusy globalne liczą się jak dotąd. Rozliczone typy nowych rozgrywek ich nie zmieniają. Podobnie stare `GET /matches` i `GET /matches/teams` pokazują tylko mecze i drużyny tego sezonu, a `GET /matches/{id}` oraz odpowiedzi wpisania wyniku działają dla każdego meczu (dla meczów nowych rozgrywek pole `stage` to faza rundy).

Runda „bieżąca” (`is_current` w `GET /seasons/{id}/rounds`) to pierwsza runda, w której jest jeszcze mecz do rozegrania, a gdy takiej nie ma — ostatnia runda z meczami (`mark_current_round()` w `domain/competitions.py`). Do rozegrania liczą się tylko mecze `scheduled` i `live` (`PENDING_STATUSES`): mecz odwołany, rozstrzygnięty walkowerem, przełożony albo przerwany nie trzyma rundy jako bieżącej, bo nie ma dla niego terminu, na który trzeba czekać — przełożony mecz sprzed miesięcy nie przypina wskaźnika do starej kolejki. Gdy taki mecz dostanie nowy termin i wróci do `scheduled`, jego runda znowu ma coś do rozegrania.

## Bonusy w ligach prywatnych

Właściciel ligi może dodać pytanie bonusowe, na razie „kto wygra sezon” wybranej rozgrywki, z własną liczbą punktów (1–100) i terminem odpowiedzi. Pytanie dotyczy jednego sezonu o statusie `upcoming` albo `active` (dla zakończonego sezonu zwycięzca jest już znany), a rozgrywka tego sezonu musi mieścić się w zakresie ligi (brak wierszy w `private_league_competitions` = wszystkie rozgrywki). Termin musi leżeć w przyszłości, a w jednej lidze może być tylko jedno pytanie na sezon (`is_deadline_in_future()`, `is_season_status_allowed()`, `is_points_valid()`, `is_competition_in_scope()`).

Odpowiadać można do terminu (wyłącznie przed nim — `is_bonus_answer_allowed()`); odpowiedź można zmieniać do tej samej chwili, a wybrana drużyna musi grać w sezonie pytania (`season_teams`). Do terminu nikt nie widzi cudzych odpowiedzi — API oddaje wtedy pustą listę `answers` (także właścicielowi), od terminu pełną (`are_answers_visible()`). Właściciel może usunąć pytanie tylko przed terminem (`can_delete_question()`), razem z nim znikają odpowiedzi.

Rozstrzygnięcie robi `resolve_season_champion(season_id, team_id)` w `db/queries/league_bonus.py`: w jednej transakcji ustawia zwycięzcę wszystkim pytaniom `champion` tego sezonu (we wszystkich ligach) i punktuje odpowiedzi przez `calculate_champion_answer_points()` — trafiona dostaje punkty pytania, nietrafiona zero (`domain/league_bonus.py`). Wywołanie jest idempotentne: ta sama drużyna drugi raz niczego nie zmienia (zostaje też pierwotne `resolved_at`), a inna drużyna działa jak korekta i przelicza punkty od nowa. Wywołuje ją ręcznie admin (`POST /admin/seasons/{id}/champion`), a synchronizacja wywoła tę samą funkcję po wykryciu mistrza sezonu. Odpowiedź złożona na już rozstrzygnięte pytanie (gdy termin jeszcze nie minął) dostaje punkty od razu.

Punkty z bonusu liczą się tylko w rankingu tej ligi (suma `league_bonus_answers.points_awarded` członków ligi dla pytań tej ligi).

## Stan wdrożenia

Funkcje opisane wyżej są gotowe i przetestowane (`tests/test_scoring.py`, `test_predictions.py`, `test_match_status.py`, `test_match_results.py`, `test_rescore.py`, `test_ranking_domain.py`, `test_league_bonus.py`, `test_sync_plan.py`, `test_prediction_lock.py`, `test_competitions_domain.py`). Punkty liczy jedna funkcja w warstwie bazy, `score_match()` w `db/queries/results.py`: bierze regułę z profilu punktacji sezonu (przez rundę meczu), zapisuje `points_awarded` i `hit_type` każdego typu i ustawia `scored_at`. Korzystają z niej trzy ścieżki: ręczne wpisanie wyniku (`finalize_match`), odzyskiwanie punktów (`recalculate_points`) i automatyczna synchronizacja z dostawcą ([data-source.md](data-source.md#synchronizacja)). Mecz zakończony rozlicza się raz; później typy przelicza się tylko wtedy, gdy dostawca skoryguje wynik w ciągu 24 godzin (`should_rescore()`), przy czym oryginalne `scored_at` zostaje, więc okno korekt się nie przedłuża. Mecze odwołane i zakończone walkowerem synchronizacja zeruje (`points_awarded` i `hit_type` na `NULL`). Tabela `scoring_rules` z wersji mundialowej nie jest już czytana przy rozliczaniu.
