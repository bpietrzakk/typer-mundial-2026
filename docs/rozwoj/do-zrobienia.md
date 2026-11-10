# Do zrobienia

Krótka lista otwartych rzeczy. Historia testów i to, co już zrobione, jest w
[pomysly.md](pomysly.md). Stan na 01.11.2026, po wdrożeniu wersji multi-competition.

## Ręcznie (bartek)

- [ ] **Sentry:** darmowe konto, dwa projekty (FastAPI i React), oba DSN do zmiennych na
  Renderze i Vercelu. Potem podpięcie SDK w kodzie (wyłączone, gdy DSN pusty).

## Na później (decyzje z 10.11.2026)

- [ ] **Domena `czutka.uk` w Resend** (SPF/DKIM w Cloudflare), potem `EMAIL_FROM="czutka <hej@czutka.uk>"`.
  Bez tego maile (reset hasła, weryfikacja) docierają tylko do właściciela konta Resend.
  Nie pilne, dopóki nikt nie zapomina hasła.
- [ ] **Nocny backup bazy**: GitHub Actions → `pg_dump -Fc` → szyfrowanie → Cloudflare R2 (10 GB za darmo),
  raz w miesiącu test odtworzenia na branchu Neona. Wymaga konta R2 i sekretów w GitHubie.
- [ ] **Docker bez roota i CSP.**
  - Docker bez roota: kontener backendu działa dziś jako `root`. Gdyby ktoś przejął aplikację,
    miałby w kontenerze pełne uprawnienia. Poprawka: osobny użytkownik w `Dockerfile` (`USER app`),
    przypięta wersja obrazu `uv`, usunięty nieużywany `postgresql-client`.
  - CSP (Content-Security-Policy): nagłówek, który mówi przeglądarce, skąd strona może ładować
    skrypty, style i obrazki. Chroni przed wstrzyknięciem cudzego skryptu (XSS). Trzeba dobrać
    listę źródeł (Google Fonts, herby przez `/img/crest`), inaczej coś przestanie się ładować.
- Odrzucone 10.11: przypomnienia i podsumowania mailem (na razie nie), usunięcie BTTS / over 2,5
  z panelu statystyk (zostają).

## Pomysły

- **Karta meczu jako fiszka.** Przód zostaje jak teraz (drużyny, godzina, pola wyniku).
  Kliknięcie poza polami odwraca kartę:
  - przed meczem tył pokazuje formę drużyn, miejsce w tabeli i mecze bezpośrednie,
  - po gwizdku typy znajomych, średni typ ligi, reakcje i wyjaśnienie punktów.

  Zastępuje ikonę „i” i rozwijane „Typy ligi”. Uwaga na zmienną wysokość karty, klik w pola
  wyniku (nie może odwracać) i `prefers-reduced-motion`. Najpierw jedna karta w kuponie na próbę.
- **Podsumowanie sezonu** w lidze na koniec sezonu (odznaki już są).
- **Automatyczne przypomnienia** mailem lub push. Odłożone (decyzja 01.11), wymaga domeny w Resend.
- **Analityka** (np. Umami), po Sentry.

## Porządki w kodzie

1. **Usunięcie starego modelu Mundialu** (migracja „contract”): `/ranking`, `/bonus/*`,
   `scoring_rules`, `matches.stage`. Źródło większości zamieszania, np. przy merge'u z `main`.
2. **Podział dużych plików:** `routers/leagues.py`, `routers/coupon.py`, `db/queries/coupon.py`,
   a na froncie `LeagueStandings.jsx` i `LeagueCoupon.jsx`.
3. **Jeden test e2e na prawdziwym backendzie** (docker compose): rejestracja, liga, typ, wynik,
   punkty. Dziś e2e działa tylko na podstawionym API.
4. **Paczka frontu ponad 500 kB:** podział na chunki (lazy routes).
5. **Opisy trafień w meczu Holandia–Maroko** (Mundial, 1/16): 3 typy mają opis niepasujący do
   punktów, bo wynik zmienił się po rozliczeniu. Punkty zostają, poprawić tylko `hit_type`.
6. ~~**Mecz nie może wrócić do typowania po tym, jak typy było widać.**~~ Zrobione 06.11 (migracja 014 `locked_at`). Okienko typów gracza
   (i kupon ligi) pokazuje typy od statusu `live`. Jeśli przerwany mecz dostanie od dostawcy nowy
   termin pod tym samym id, sync zmienia go z `live` na `scheduled` i typowanie znów się otwiera,
   a wszyscy widzieli już cudze typy. Poprawka: nowa kolumna `first_live_at` (migracja), ustawiana
   przez sync, i blokada w `prediction_block_reason`, gdy jest ustawiona. Albo sync nie cofa
   statusu z `live` na `scheduled`.
