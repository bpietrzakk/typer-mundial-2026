# Migracje bazy

Schemat bazy powstaje z plików SQL w [`mundial-backend/db/migrations/`](../mundial-backend/db/migrations/), aplikowanych po kolei. Ten dokument opisuje, jak działa runner migracji, jak cofnąć zmianę i jak bezpiecznie przeprowadzić migrację na produkcji.

## Jak to działa

Każda zmiana schematu to nowy plik `NNN_nazwa.sql` z datą i autorem w nagłówku. Starych plików nigdy się nie edytuje — produkcja ma je już zaaplikowane.

Migracje aplikuje [`db/migrate.py`](../mundial-backend/db/migrate.py). Robi to samo przy każdym starcie backendu (`main.py`), więc deploy nowej wersji z nowym plikiem migracji sam zaktualizuje bazę. Runner prowadzi rejestr w tabeli `schema_migrations` (nazwa pliku + data), więc każdy plik wykonuje się dokładnie raz. Każdy plik idzie w **jednej transakcji** jako jedno polecenie — jeśli coś w środku się wysypie, PostgreSQL cofa cały plik i baza zostaje w stanie sprzed migracji. Dodatkowo runner bierze blokadę doradczą (`pg_advisory_xact_lock`), żeby dwie instancje backendu startujące naraz nie aplikowały migracji równolegle.

Ręcznie:

```bash
cd mundial-backend
uv run python -m db.migrate               # zaaplikuj wszystkie oczekujące
uv run python -m db.migrate --until 004   # tylko do 004 włącznie
uv run python -m db.migrate --reset       # DEV: wyczyść bazę i zaaplikuj od zera (pyta o YES)
uv run python -m db.migrate --down 005    # cofnij migrację 005 (pyta o YES)
```

`./scripts/migrate.sh` to cienka nakładka na to samo polecenie.

## Expand → contract

Duże zmiany schematu robimy w dwóch krokach. Najpierw migracja **expand** tylko dodaje: nowe tabele, nowe kolumny, wypełnienie ich danymi. Stare kolumny zostają, więc stary kod dalej działa, a cofnięcie jest bezpieczne. Dopiero gdy nowa wersja kodu działa na produkcji i nic nie czyta starych kolumn, migracja **contract** je usuwa.

Przykład: `005_multi_competition.sql` dodała rozgrywki, sezony i rundy oraz przepisała do nich dane Mundialu, ale `matches.stage` i tabela `scoring_rules` nadal istnieją ([data-model.md](data-model.md) ma pełną listę).

`006_archived_scored_at.sql` ustawia `scored_at` meczów z archiwalnych sezonów na godzinę rozpoczęcia meczu (005 wpisała tam `NOW()`), żeby 24-godzinne okno ponownego przeliczania nie objęło zakończonego Mundialu.

`007_sync_run_lock.sql` dodaje tylko indeks: unikalny indeks częściowy `uq_sync_runs_one_running` na `sync_runs (status) WHERE status = 'running'`. Dopuszcza co najwyżej jeden wiersz „trwającego” przebiegu synchronizacji, więc dwa procesy nie synchronizują naraz (blokada doradcza odpada, bo Neon za pulerem transakcji nie trzyma blokad sesyjnych; szczegóły w [data-source.md](data-source.md#jeden-przebieg-naraz)). Zanim indeks powstanie, migracja oznacza ewentualne wiersze `running` jako błąd — inaczej indeks by się nie zbudował.

## Cofanie (rollback)

Do każdej migracji, która zmienia istniejące tabele, jest plik cofający w `db/migrations/rollback/NNN_nazwa.down.sql`. Runner nigdy nie wykonuje go sam — tylko przez `--down NNN`. Plik cofający 005 usuwa dane spoza Mundialu, odtwarza dokładnie schemat sprzed 005 i kasuje wpis z `schema_migrations`. Cofamy od najnowszej: najpierw `--down 007` (usuwa indeks blokady synchronizacji, wiersze `sync_runs` zostają), potem `--down 006`, potem `--down 005`.

Na produkcji pierwszą linią obrony nie jest jednak plik cofający, tylko kopia bazy zrobiona tuż przed migracją. Neon pozwala zrobić gałąź bazy (branch) w kilka sekund — jeśli po migracji coś jest nie tak, przełącza się aplikację z powrotem na gałąź sprzed migracji.

## Sprawdzanie, że dane się nie zmieniły

[`scripts/verify_migration.py`](../mundial-backend/scripts/verify_migration.py) robi „zdjęcie” danych, które nie mogą się zmienić: liczby użytkowników, typów, meczów i lig, sumy punktów każdego użytkownika (z meczów i bonusów), pełny ranking globalny i sumę kontrolną wszystkich typów. Działa na schemacie sprzed i po migracji.

```bash
uv run python scripts/verify_migration.py snapshot --out before.json
uv run python -m db.migrate
uv run python scripts/verify_migration.py snapshot --out after.json
uv run python scripts/verify_migration.py compare before.json after.json   # kod wyjścia 1 = różnica
```

## Procedura na produkcji

1. Zrób gałąź bazy w Neon z produkcji (to jest kopia zapasowa i jednocześnie środowisko testowe).
2. Na kopii: `snapshot`, migracja, `snapshot`, `compare`. Uruchom backend wskazując kopię i przeklikaj aplikację.
3. Sprawdź na produkcji, że istnieją ograniczenia, które migracja usuwa po nazwie:
   `SELECT conname FROM pg_constraint WHERE conname IN ('teams_external_id_key','matches_external_id_key','matches_status_check','matches_stage_check');` — powinny być 4 wiersze.
4. Deploy. Backend przy starcie zaaplikuje migrację.
5. Jeszcze raz `snapshot` i `compare` z wynikiem z punktu 2.

## Testy migracji

Testy w [`tests/integration/`](../mundial-backend/tests/integration/) uruchamiają migracje na prawdziwym PostgreSQL. Każdy test dostaje świeżą bazę, wgrywa syntetyczny Mundial (użytkownicy, mecze od grup po finał rozliczone prawdziwym kodem, bonusy, liga prywatna) i sprawdza m.in., że po migracji 005 ranking i punkty są identyczne, że cofnięcie przywraca dokładnie stary schemat i że ponowne uruchomienie runnera nic nie robi.

Lokalnie potrzebny jest osobny kontener z bazą testową:

```bash
docker run -d --name czutka-test-db -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=test -p 55432:5432 postgres:16
RUN_DB_TESTS=1 uv run pytest -q
```

Bez `RUN_DB_TESTS=1` testy integracyjne są pomijane. W CI baza testowa startuje automatycznie ([ci-cd.md](ci-cd.md)).
