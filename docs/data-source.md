# Źródło danych meczowych

Terminarz, wyniki i drużyny pobieramy automatycznie z zewnętrznego API. Ten dokument wyjaśnia, które API wybraliśmy i dlaczego, czego ono nie obejmuje oraz jak kod tłumaczy jego dane na nasz model.

## Dlaczego football-data.org

Założenie projektu to zero kosztów stałych, więc szukaliśmy darmowego źródła, które pokryje Ligę Mistrzów, Ekstraklasę, Ligę Narodów i ligi top 5. Takiego źródła nie ma. Porównaliśmy:

- **football-data.org, plan darmowy** — Liga Mistrzów, Premier League, LaLiga, Serie A, Bundesliga, Ligue 1 (plus Championship, Eredivisie, Primeira Liga, Brasileirão, Euro, Mundial). Limit 10 zapytań na minutę, wyniki z opóźnieniem. Brak Ekstraklasy i Ligi Narodów.
- **API-Football** — obejmuje wszystko, ale darmowy plan nie daje dostępu do bieżącego sezonu; najtańszy płatny to ok. 19 USD/mies.
- **TheSportsDB** — ma Ekstraklasę, ale darmowy klucz zwraca tylko kilka meczów sezonu; pełne dane za ok. 9 USD/mies.
- **Nieoficjalne API ESPN** — nieudokumentowane, bez gwarancji, a dla Ekstraklasy zwraca błąd.

Wybraliśmy football-data.org, bo za darmo pokrywa 6 z 8 docelowych rozgrywek, ma przewidywalny limit i porządną dokumentację, a dane Mundialu i tak pochodziły z tego źródła. Ekstraklasa i Liga Narodów są w bazie jako nieaktywne rozgrywki bez dostawcy. Kod jest przygotowany na drugiego dostawcę, więc włączenie ich później to dopisanie adaptera i jedna zmiana w tabeli `competitions` (decyzja w [decisions.md](decisions.md), wpis 010).

Klucz API ustawia się w zmiennej środowiskowej `FOOTBALL_API_KEY` — nigdy w kodzie.

## Warstwa dostawcy

Kod komunikacji z API mieszka w [`services/providers/`](../mundial-backend/services/providers/). `base.py` definiuje wspólny interfejs `FootballProvider` i neutralne struktury danych (`ProviderMatch`, `ProviderTeam`, `ProviderSeason`) — reszta aplikacji zna tylko je, nie format konkretnego API. `football_data.py` to implementacja dla football-data.org, a `registry.py` zwraca dostawcę po nazwie zapisanej w `competitions.provider`.

Interfejs ma cztery operacje: bieżący sezon rozgrywki, wszystkie mecze sezonu, mecze z okna dat (dla wielu rozgrywek naraz — jedno zapytanie zamiast sześciu) i mecze po identyfikatorach.

`football_data.py` jest podzielony na dwie części. Czyste funkcje tłumaczą odpowiedź API na nasz model i są testowane na nagranych prawdziwych odpowiedziach (`tests/fixtures/providers/football_data/`), bez sieci. Klient HTTP pilnuje limitu: czyta nagłówki `X-Requests-Available-Minute` i `X-RequestCounter-Reset`, czeka, gdy limit się wyczerpie, a przy błędzie 429 lub 5xx ponawia zapytanie do trzech razy z rosnącą przerwą. Długie okna dat dzieli na kawałki po 10 dni (limit API).

## Jak tłumaczymy dane

Statusy: `SCHEDULED` i `TIMED` → `scheduled` (przy `SCHEDULED` godzina nie jest jeszcze potwierdzona), `IN_PLAY`, `PAUSED`, `EXTRA_TIME`, `PENALTY_SHOOTOUT` → `live`, a `FINISHED`, `POSTPONED`, `SUSPENDED`, `CANCELLED`, `AWARDED` → odpowiednio `finished`, `postponed`, `suspended`, `cancelled`, `awarded`.

Fazy: `REGULAR_SEASON` → `regular`, `LEAGUE_STAGE` → `league_phase`, `GROUP_STAGE` → `group`, warianty baraży → `playoff`, `LAST_32`/`LAST_16` → `round_of_32`/`round_of_16`, `QUARTER_FINALS`, `SEMI_FINALS`, `THIRD_PLACE`, `FINAL` → odpowiednio `quarter`, `semi`, `third_place`, `final`. Nieznana faza trafia do `other` z ostrzeżeniem w logach. Nazwy rund powstają po polsku: „Kolejka 12”, „Faza ligowa – kolejka 3”, „Ćwierćfinał”.

Nazwy reprezentacji tłumaczymy na polski (`services/translations.py`), nazwy klubów zostają oryginalne.

### Wynik a dogrywka i karne

To najważniejsza pułapka tego API. Pole `score.fullTime` **zawiera gole z dogrywki i z serii rzutów karnych**. Przykład z Mundialu 2026, Niemcy – Paragwaj w 1/16 finału:

```json
{"duration": "PENALTY_SHOOTOUT",
 "fullTime":    {"home": 4, "away": 5},
 "regularTime": {"home": 1, "away": 1},
 "extraTime":   {"home": 0, "away": 0},
 "penalties":   {"home": 3, "away": 4}}
```

Mecz skończył się 1:1, a `fullTime` mówi 4:5. Dlatego wynik do punktacji bierzemy z `regularTime`, gdy mecz miał dogrywkę lub karne, a z `fullTime` tylko przy `duration = REGULAR`. Wynik po dogrywce to `regularTime + extraTime` (bo `extraTime` to same gole z dogrywki), a karne zapisujemy osobno.

Stara wersja aplikacji zapisywała `fullTime`, więc 9 meczów pucharowych Mundialu (4 z karnymi, 5 z dogrywką) mogło zostać zapisanych i rozliczonych z zawyżonym wynikiem. Archiwum nie jest przeliczane automatycznie; to, czy je poprawić, jest osobną decyzją.
