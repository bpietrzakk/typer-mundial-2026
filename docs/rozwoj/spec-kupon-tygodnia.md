# Specyfikacja: Kupon tygodnia

Szkic do dyskusji (bartek + Daniel), 30.10.2026. Wynika z trzeciej rundy testów w
[`pomysly.md`](pomysly.md#trzecia-runda-zwykły-gość-który-niczego-nie-zna-2810-wieczór) i z
[`analiza-biznesowa.md`](analiza-biznesowa.md). Nic z tego nie jest jeszcze zaimplementowane.

---

## Po co

Dziś nowy gracz widzi „68 meczów czeka na Twój typ”, z czego większość go nie obchodzi, i zamyka
aplikację. Kupon tygodnia daje każdej lidze **małą, wspólną porcję meczów** (domyślnie 10), które
wszyscy w lidze typują w danym tygodniu. Licznik zmienia się na „3 z 10”, czyli coś, co da się skończyć.

Ten sam mechanizm w wersji firmowej to „mecze turnieju” albo „mecze tygodnia działu”, więc
budujemy fundament pod B2B.

## Zasady dla gracza (wersja do wyświetlenia w aplikacji)

- Co tydzień liga ma kupon: ok. 10 meczów od poniedziałku do niedzieli.
- Kupon układa się sam z najciekawszych meczów rozgrywek ligi albo układa go organizator.
- Każdy mecz zamyka się o swojej godzinie rozpoczęcia, tak jak dziś.
- W lidze z trybem „tylko kupon” do rankingu liczą się wyłącznie mecze z kuponu. Wszyscy grają
  na tych samych meczach, więc jest uczciwie.
- Inne mecze nadal można typować („Typuj więcej”). Liczą się w rankingach rozgrywek, ale nie w
  rankingu tej ligi.

---

## Decyzje do podjęcia (proponuję odpowiedzi)

| Pytanie | Propozycja | Dlaczego |
|---|---|---|
| Czy kupon zmienia ranking ligi? | Tak, nowe ustawienie ligi `ranking_mode`: `scope` (jak dziś) albo `coupon`. **Nowe ligi domyślnie `coupon`, istniejące zostają `scope`.** | Nie zmieniamy zasad lidze w trakcie sezonu |
| Tydzień od kiedy do kiedy? | Poniedziałek 00:00 – niedziela 23:59 czasu polskiego | Kolejki lig grają pt–pn, ale poniedziałkowy mecz zamyka poprzedni kupon. To akceptowalne, a prostsze niż „kolejka” wspólna dla kilku lig |
| Ile meczów? | Domyślnie 10, organizator ustawia 5–15 | 10 to ok. 3 minuty typowania |
| Kiedy kupon powstaje? | Automatycznie w poniedziałek o 06:00 (scheduler synchronizacji) | Gracze widzą go od rana |
| Co może organizator? | Dodać lub usunąć mecz, dopóki ten mecz się nie zaczął. Meczu, który już się zaczął, nie da się ani dodać, ani usunąć | Nie da się zmienić kuponu „pod wynik” |
| Co z tygodniem bez meczów (przerwa reprezentacyjna)? | Kupon pusty, a na ekranie komunikat „przerwa na reprezentacje, wracamy w sobotę 14.11” | Lepsze niż losowe mecze z dziwnych lig |
| Gracz w kilku ligach | Start pokazuje sumę kuponów. Mecz z dwóch kuponów jest typowany raz (typ jest per mecz, tak jak dziś), z etykietą lig | `predictions` już jest per użytkownik i mecz, nic nie trzeba zmieniać |

---

## Automatyczny dobór meczów (czysta funkcja)

`domain/coupon.py`, zero I/O, zgodnie z zasadą nr 1 z CLAUDE.md. Testy w
`tests/test_coupon.py` **przed** implementacją.

```python
def pick_coupon(candidates: list[CouponCandidate], size: int = 10,
                max_per_competition: int = 4) -> list[int]:
    """returns match ids for the weekly coupon, best first"""
```

`CouponCandidate` (dane przygotowuje warstwa `db/`): `match_id`, `competition_code`, `phase`,
`kickoff_at`, `home_rank`, `away_rank` (miejsce w tabeli sezonu albo `None`), `is_derby`.

**Punktacja kandydata** (im więcej, tym lepiej):

| Składnik | Punkty |
|---|---|
| Liga Mistrzów: faza pucharowa / faza ligowa | +6 / +3 |
| Obie drużyny w top 6 tabeli | +5 |
| Jedna drużyna w top 4 | +2 |
| Derby (stała lista par w kodzie, np. Arsenal–Tottenham, Real–Atlético, Milan–Inter) | +4 |
| Mała różnica miejsc w tabeli (≤ 3) | +1 |
| Mecz w sobotę lub niedzielę | +1 |

Potem wybieramy po kolei najlepszych kandydatów, pilnując `max_per_competition` (żeby nie było
10 meczów Premier League), a przy remisie wybieramy wcześniejszy mecz.

**Skąd miejsce w tabeli:** nie mamy tabel z API, ale mamy wyniki. Tabelę sezonu liczymy z
zakończonych meczów w `matches` (3/1/0 pkt, potem bilans i bramki), w jednym zapytaniu w
`db/queries/coupon.py`. Na początku sezonu (mniej niż 3 kolejki) `rank = None` i liczy się tylko
rozgrywka, derby i weekend. Tabela przyda się też później jako kontekst przy meczu (P1 w `pomysly.md`).

Przypadki do testów: pusta lista, mniej kandydatów niż `size`, limit na rozgrywkę, remis
punktów, same `rank=None`, liga z jedną rozgrywką (wtedy limit nie może zablokować kuponu, więc
`max_per_competition` ignorujemy, gdy jest tylko jedna rozgrywka).

---

## Model danych (migracja `008_league_coupons.sql`)

```sql
-- 008_league_coupons.sql
-- data: 2026-XX-XX, autor: ...

ALTER TABLE private_leagues
    ADD COLUMN ranking_mode TEXT NOT NULL DEFAULT 'scope'
        CHECK (ranking_mode IN ('scope', 'coupon')),
    ADD COLUMN coupon_size SMALLINT NOT NULL DEFAULT 10
        CHECK (coupon_size BETWEEN 5 AND 15),
    ADD COLUMN coupon_auto BOOLEAN NOT NULL DEFAULT TRUE;

CREATE TABLE league_coupons (
    id                 BIGSERIAL PRIMARY KEY,
    private_league_id  BIGINT NOT NULL REFERENCES private_leagues(id) ON DELETE CASCADE,
    week_start         DATE NOT NULL,          -- monday, polish time
    created_by         TEXT NOT NULL CHECK (created_by IN ('auto', 'owner')),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (private_league_id, week_start)
);

CREATE TABLE league_coupon_matches (
    coupon_id  BIGINT NOT NULL REFERENCES league_coupons(id) ON DELETE CASCADE,
    match_id   BIGINT NOT NULL REFERENCES matches(id),
    added_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (coupon_id, match_id)
);
CREATE INDEX ON league_coupon_matches (match_id);
```

Nowe ligi: front przy tworzeniu wysyła `ranking_mode='coupon'`. Default w bazie zostaje
`scope`, żeby migracja nie zmieniła zasad istniejącym ligom.

**Ranking ligi w trybie `coupon`:** to samo zapytanie co dziś, z dodatkowym `JOIN
league_coupon_matches lcm ON lcm.match_id = p.match_id JOIN league_coupons lc ON lc.id =
lcm.coupon_id AND lc.private_league_id = %s`. Bonusy ligi liczą się bez zmian.

---

## API (kontrakt do dopisania w `api-contract.md`)

| Metoda | Ścieżka | Kto | Co |
|---|---|---|---|
| GET | `/leagues/{id}/coupon?week=YYYY-MM-DD` | członek | kupon tygodnia (domyślnie bieżący): mecze, mój typ, liczba typujących; po rozpoczęciu meczu także typy członków (patrz P0.2 w `pomysly.md`) |
| PUT | `/leagues/{id}/coupon` | właściciel | `{match_ids: [...]}`, walidacja: tylko przyszłe mecze, nie można usuwać rozpoczętych, rozmiar 5–15 → 409 z polskim komunikatem |
| POST | `/leagues/{id}/coupon/regenerate` | właściciel | ułóż od nowa automatem (zostawia rozpoczęte mecze) |
| GET | `/me/coupon` | zalogowany | suma kuponów wszystkich moich lig na ten tydzień: mecze z etykietami lig, licznik `typed/total`, najbliższe zamknięcie. **To jest nowy Start.** |
| PATCH | `/leagues/{id}` | właściciel | dochodzą pola `ranking_mode`, `coupon_size`, `coupon_auto` |

Schematy Pydantic w `schemas/models.py`, SQL w nowym module `db/queries/coupon.py`.

**Generowanie w tle:** w schedulerze synchronizacji (`services/sync`) raz na godzinę sprawdzamy:
jest poniedziałek po 06:00 i liga z `coupon_auto=true` nie ma kuponu na ten tydzień? Wtedy
generujemy. Idempotentne dzięki `UNIQUE (private_league_id, week_start)`, więc restart czy dwa
przebiegi nie zrobią dwóch kuponów.

---

## Ekrany

**Start (gracz z ligą)**
```
┌────────────────────────────────────┐
│ Twój kupon · 30.10–5.11            │
│ ███████░░░  7 z 10                 │
│ najbliższy zamyka się za 2 h 15 min│
├────────────────────────────────────┤
│ pt 21:00  Villarreal  [2]:[1]  Esp │ ✓
│ sob 13:30 Chelsea     [ ]:[ ]  MUN │
│ sob 18:30 Arsenal     [ ]:[ ]  TOT │ DERBY
│ …                                  │
│ [ Typuj więcej meczów → ]          │
└────────────────────────────────────┘
```
- Jeden wiersz na mecz, autozapis po wpisaniu obu liczb (z drobnym „✓”). Podpowiedź „0” w
  drugim polu jest szara, dopóki gracz jej nie potwierdzi (patrz trzecia runda).
- Gracz bez ligi: zamiast kuponu ligi kupon „Hity tygodnia” z tego samego algorytmu na
  obserwowanych rozgrywkach, plus zachęta „Załóż ligę i zaproś znajomych”.

**Liga:** na górze kupon tygodnia z paskiem „kto już wytypował (5/8)”. Dla właściciela
przyciski „Edytuj kupon” i „Przypomnij resztę”. Ten drugi to na start po prostu link do skopiowania na
grupę: „Zostały 3 godziny, wytypuj: czutka.app/l/BFKE832S”.

**Tworzenie ligi:** krok „Co typujecie?”: [Kupon tygodnia z hitów (polecane)] [Wybrane
rozgrywki, wszystkie mecze] i wybór rozgrywek.

---

## Kolejność wdrożenia (małe kroki, zgodnie z CLAUDE.md)

1. `domain/coupon.py` + `tests/test_coupon.py` (najpierw testy).
2. Migracja 008 + `db/queries/coupon.py` (tabela ligowa z wyników, kupon CRUD) + testy na Postgresie w CI.
3. Endpointy GET/PUT/regenerate + generowanie w schedulerze.
4. Ranking ligi z `ranking_mode`.
5. Front: kupon na Starcie i w lidze (z autozapisem), potem edytor organizatora i krok w tworzeniu ligi.
6. `GET /me/coupon` i nowy Start.

Szacunek [S]: kroki 1–4 to ok. 2–3 wieczory, a front ok. 3–4 wieczory.

## Jak sprawdzimy, czy działa

- Odsetek członków lig, którzy wytypowali **cały** kupon w danym tygodniu (cel ≥ 40% po 6 tygodniach).
- Odsetek lig, w których ktoś typował w ostatnim tygodniu.
- Ile razy organizator edytuje kupon. Jeśli prawie nigdy, to automat jest dość dobry.

Te trzy liczby da się policzyć jednym zapytaniem SQL na tabelach `predictions` i
`league_coupon_matches`, bez żadnej analityki zewnętrznej.

## Otwarte pytania

- Czy w trybie `coupon` pozwalać na „Joker” (podwójne punkty za jeden mecz kuponu)? To naturalne
  rozszerzenie (P1 w `pomysly.md`), ale dopiero po sprawdzeniu, czy kupon w ogóle działa.
- Lista derbów: utrzymywana w kodzie czy w tabeli edytowanej w panelu admina? Na start w kodzie.
- Faza pucharowa LM ma tygodnie z samymi meczami LM we wtorki i środy. Czy w takim tygodniu limit
  `max_per_competition` ma być wyższy? Na start: tak, gdy faza ≥ 1/8, limit dla LM = 8.
