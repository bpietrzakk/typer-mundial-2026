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

## Korekty wyników

Dostawcy danych czasem poprawiają wynik po fakcie. Dlatego przez 24 godziny od naliczenia punktów synchronizacja sprawdza zakończone mecze jeszcze raz i jeśli wynik po 90 minutach się zmienił, przelicza typy od nowa (`should_rescore()` w `domain/rescore.py`). Liczenie jest deterministyczne, więc ponowne przeliczenie zawsze daje ten sam wynik dla tych samych danych. Archiwum Mundialu nie jest przeliczane.

## Remisy w rankingu

Ranking sortuje po sumie punktów, przy równej sumie — po liczbie dokładnych trafień, potem po liczbie trafionych różnic bramek, a na końcu alfabetycznie po nicku (`sort_ranking()` w `domain/ranking.py`). Gracze równi w punktach, dokładnych trafieniach i różnicach dzielą miejsce, a kolejne miejsce jest pomijane (1, 1, 3).

## Bonusy w ligach prywatnych

Właściciel ligi może dodać pytanie bonusowe, na razie „kto wygra sezon” wybranej rozgrywki, z własną liczbą punktów i terminem odpowiedzi. Odpowiadać można do terminu (wyłącznie przed nim — `is_bonus_answer_allowed()`), a po rozstrzygnięciu trafna odpowiedź dostaje ustalone punkty, nietrafiona zero (`domain/league_bonus.py`). Punkty z bonusu liczą się tylko w rankingu tej ligi.

## Stan wdrożenia

Funkcje opisane wyżej są gotowe i przetestowane (`tests/test_scoring.py`, `test_predictions.py`, `test_match_status.py`, `test_match_results.py`, `test_rescore.py`, `test_ranking_domain.py`, `test_league_bonus.py`). Ręczne wpisanie wyniku i rozliczanie meczów Mundialu wciąż korzysta ze starej ścieżki (`db/queries/results.py` z tabelą `scoring_rules`); przejście na profile punktacji następuje razem z automatyczną synchronizacją.
