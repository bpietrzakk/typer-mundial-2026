# Do zrobienia

Krótka lista otwartych rzeczy. Historia testów i to, co już zrobione, jest w
[pomysly.md](pomysly.md). Stan na 01.11.2026, po wdrożeniu wersji multi-competition.

## Ręcznie (bartek)

- [ ] **Sentry:** darmowe konto, dwa projekty (FastAPI i React), oba DSN do zmiennych na
  Renderze i Vercelu. Potem podpięcie SDK w kodzie (wyłączone, gdy DSN pusty).

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
