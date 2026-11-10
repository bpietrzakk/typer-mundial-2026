# Analiza czutka.uk: stan projektu, diagnoza „dlaczego nikt nie używa”, rekomendacje

Stan na 4.11.2026, repo `main` @151c858. Analiza objęła cały kod (backend, frontend, migracje, CI, `docs/`), uruchomienie testów i aplikacji lokalnie, odtworzenie bugów na osobnych bazach, research rynku i usług w sieci. Szkic przeszedł niezależną, krytyczną recenzję i został na jej podstawie poprawiony (m.in. skrócone minimum przed startem, poprawiona rekomendacja dot. gałęzi, dodana „opcja zero”).

Ścieżki plików są względne do repo (`mundial-backend/…`, `mundial-frontend/…`). Oznaczenia: **[kod]** – potwierdzone w kodzie, **[env]** – zależy od zmiennych środowiskowych na produkcji, których nie widziałem, **[research]** – ze źródeł w sieci, **[wniosek]** – moja ocena. Produkcji nie dało się odpytać poza pobraniem HTML strony głównej.

Nakład: **S** = 1 wieczór (2–4 h), **M** = 2–5 wieczorów, **L** = ponad 5 wieczorów, dla jednej osoby po godzinach (~8–10 h tygodniowo). Przy pozycjach roadmapy zaznaczam, czy praca jest w **Pythonie** czy w **React**, bo to dla autora różnica w koszcie mniej więcej dwukrotna.

---

## 1. Podsumowanie dla zabieganego

### 10 najważniejszych wniosków

1. **Aplikacja nigdy sama nie woła gracza z powrotem.** Nie ma żadnego automatycznego przypomnienia ani podsumowania (maile tylko przy weryfikacji i resecie hasła, service worker bez push). Każdy liczący się konkurent ma przypomnienie „tylko do tych, którzy nie wytypowali”. **[kod]**
2. **Tych, którzy wracają sami, aplikacja wylogowuje po 7 dniach**, a hasła nie odzyskają, bo maile z domeny `resend.dev` docierają tylko do właściciela konta Resend. **[kod + env]**
3. **Baza może się wyłączyć w drugiej połowie miesiąca.** Jeśli synchronizacja jest włączona, a keep-alive działa, scheduler pyta Neona co 60 s, baza nie usypia i zużywa ok. 186 CU-h przy limicie 100 CU-h; po przekroczeniu Neon wstrzymuje bazę do końca okresu rozliczeniowego. Sprawdzenie zakładki Usage to 5 minut. **[kod + env + research]**
4. **Link zaproszenia słabo „sprzedaje”:** podgląd na Messengerze bez obrazka (względny `og:image`, potwierdzone na produkcji), przy zimnym serwerze pusty spinner, formularz z hasłem w przeglądarce wbudowanej Messengera. **[kod]**
5. **Problem jest też społeczny:** bez gospodarza ligi (kogoś innego niż autor), stawki i rytuału czutka przegrywa z czatem grupy, na którym wystarczy napisać „2:1”. Sezon ligowy nie ma naturalnego napięcia Mundialu. **[wniosek]**
6. **Za dużo funkcji i pojęć przy zera graczy:** obserwowane rozgrywki, zakres ligi, kupon ogólny i ligowy, dwa tryby rankingu, joker działający tylko w jednym. Nowy gracz nie wie, które mecze „się liczą”. **[kod]**
7. **Kod nie jest chaotyczny; backend to najmocniejsza część projektu.** 1223 testy zielone, poprawna punktacja w przypadkach brzegowych. Realne bugi są na brzegach: sesja, pula połączeń, usuwanie konta właściciela ligi (500), mecz wracający do typowania. **[kod]**
8. **Rewrite i natywna aplikacja nie mają teraz sensu.** Żadna zmiana stacku nie doda gracza, a każda kosztuje 120–500 h. Zostaje FastAPI + React + PWA, mail jako główny kanał. **[wniosek]**
9. **Funkcje gry czutka ma na poziomie najlepszych, ale odstaje w „rurach”** (przypomnienia, logowanie, Ekstraklasa). Najgroźniejszy rywal w Polsce, pominięty w dokumentach autora, to kicktipp.pl z darmowym typerem Ekstraklasy. Nisza: „polski typer dla ekipy, bez bukmachera”. **[research]**
10. **Autor nie wie, ile osób używa aplikacji.** Brak analityki, ale lejek i retencję da się odtworzyć z bazy zapytaniami z rozdz. 2.2. Bez tego nie wiadomo, czy problemem jest pozyskanie, czy powrót graczy z Mundialu. **[kod]**

### Rekomendacja strategiczna

**Ewolucja obecnego stacku, bez rewrite’u i bez dużego refactoru.** Cel na najbliższe 6 tygodni: **jedna prawdziwa liga znajomych, która typuje co tydzień.** Przyczyny braku użytkowników leżą w sesji, mailach, przypomnieniach, linku, hostingu i braku gospodarza, a każdą naprawia się w godzinach, nie w miesiącach. Rewrite to 6–12 miesięcy po godzinach bez żadnej zmiany dla graczy.

**Zamrożenie funkcji** do czasu, aż liga zagra 4 kolejki z rzędu: wolno naprawiać, mierzyć, upraszczać i dodać **dokładnie dwie** rzeczy: piątkowe przypomnienie mailem i poniedziałkowe podsumowanie mailem. Nic więcej.

**Warunek wstępny:** zanim autor napisze linijkę kodu pod plan adopcji, potrzebna jest grupa i gospodarz (rozdz. 2.0). Jeśli ich nie ma, uczciwą odpowiedzią jest „opcja zero”.

### Lista na najbliższe dni (ok. 6 h)

| # | Co | Czas | Gdzie |
|---|---|---|---|
| 1 | Konsola Neona → Usage; Render → Environment: sprawdzić `JWT_EXPIRE_DAYS`, `EMAIL_FROM`, `COOKIE_SECURE`, `SYNC_ENABLED`; w DevTools sprawdzić, że żądania idą na `www.czutka.uk/api/...` | 15 min | konsole |
| 2 | Zapytania B i E z rozdz. 2.2 (ilu typowało w czerwcu, ilu teraz) | 30 min | Neon SQL Editor |
| 3 | Rozmowa z kandydatem na gospodarza ligi | 30 min | telefon / piwo |
| 4 | `og:image` jako pełny URL + test w Facebook Sharing Debugger | 15 min | HTML |
| 5 | Domena `czutka.uk` w Resend (SPF/DKIM w Cloudflare), `EMAIL_FROM`, nazwa „czutka” w mailach | 45 min | DNS + Python |
| 6 | Sesja przesuwana: nowe cookie przy `/auth/me`, gdy token ma ponad 24 h; `JWT_EXPIRE_DAYS=90` | 2 h | Python (+1 linia React) |
| 7 | Scheduler: nie pytać bazy co minutę, gdy nic nie jest należne (stan w pamięci); `/health/live` bez bazy dla keep-alive | 2 h | Python |
| 8 | Fast-forward `feat/front-listopad` do `main` | 5 min | git |

---

## 2. Dlaczego nikt nie używa i plan adopcji wśród znajomych

### 2.0 Krok zero: czy jest dla kogo to robić

Plan adopcji zakłada grupę 8–15 osób, która ogląda razem piłkę, i gospodarza, który poprowadzi ligę. To trzeba sprawdzić **przed** kodowaniem, w pierwszym tygodniu:
- **Zapytanie E** (rozdz. 2.2): ilu graczy Mundialu nie wróciło. Jeśli było ich 30, jest kogo reaktywować. Jeśli 5, główny problem to brak zaproszonej grupy, nie aplikacja.
- **Rozmowa z gospodarzem:** „Robię typer, chcę go przetestować na naszej ekipie. Poprowadzisz ligę? Wystarczy, że raz w tygodniu wrzucisz obrazek na grupę.”

**Jeśli nie ma gospodarza albo grupa nie chce grać:** nie realizować planu z 2.4 na siłę. Dwie uczciwe opcje:
- **Opcja zero:** grupa gra tam, gdzie już jest wygodnie (kicktipp.pl ma dziś przypomnienia i Ekstraklasę), a czutka zostaje projektem do nauki i portfolio. Wtedy warto zrobić tylko poprawki z listy „na najbliższe dni” i bezpieczeństwo, bez funkcji.
- **Poczekać na moment:** wrócić z zaproszeniem na fazę pucharową LM (luty–marzec 2027) albo na Euro 2028, kiedy „kto wygra typera” brzmi naturalnie.

**Ryzyko wypalenia:** staż na 4/5 etatu, studia i sesja w styczniu–lutym. Plan zakłada 8–10 h tygodniowo i w sesji tylko utrzymanie. Jeśli tego czasu nie ma, lepiej przesunąć start, niż wystartować z aplikacją, która się psuje.

### 2.1 Diagnoza: przyczyny od najważniejszej

Najkrócej: **czutka nie ma pętli powrotu ani gospodarza.** Łatwiejsze wejście samo nic nie da, jeśli aplikacja nie przypomina o typowaniu, wylogowuje po tygodniu i nie daje powodu, żeby wrócić w poniedziałek.

| # | Przyczyna | Dowód | Pewność |
|---|---|---|---|
| 1 | **Brak automatycznych przypomnień i podsumowań.** W tygodniu z Ligą Mistrzów połowa kuponu zamyka się we wtorek i środę. Kto zagląda tylko w sobotę, widzi „4/10” i przegapione mecze. Autor sam nazywa przypomnienia „najważniejszą zmianą produktową” (`docs/rozwoj/pomysly.md`, „Druga runda”), a jednocześnie decyzją z 1.11 je odkłada. To najważniejsza sprzeczność w jego planie. | `services/email.py:40-62` (tylko weryfikacja i reset), `public/sw.js` (tylko install/activate/fetch), `LeagueCouponProgress.jsx:19-24` (ręczny tekst do schowka), `routers/coupon.py:158` (przycisk tylko dla organizatora) | wysoka |
| 2 | **Wylogowanie 7 dni po zalogowaniu, niezależnie od aktywności; brak odzyskania hasła; konto „zamknięte” w webview Messengera.** | `routers/auth.py:93,103` (ważność), `routers/auth.py:318-322` (`/me` nie odświeża), `AuthContext.jsx:19-30` (`setInterval` co 6 dni w otwartej karcie), `services/email.py:13` (domyślnie `onboarding@resend.dev`), [Resend: domena resend.dev tylko na adres właściciela](https://resend.com/docs/knowledge-base/403-error-resend-dev-domain) | wysoka w kodzie; wartości na produkcji [env] |
| 3 | **Brak gospodarza, rytuału i stawki.** Konkurencją jest czat grupy i Excel, nie inna aplikacja. Pole „Na co gramy?” istnieje (`LeaguePrizePool.jsx`), ale nic go nie ogłasza. | wniosek, zgodny z `pomysly.md` („zbiór ekranów, a nie doświadczenie”) | średnia–wysoka |
| 4 | **Tarcie przy wejściu z linku.** Podgląd bez obrazka i z ogólnym tytułem (SPA bez SSR). Przy zimnym serwerze pusty spinner podczas `/auth/me` (do 72 s zmierzone przez autora). Ekran rejestracji pokazuje już, kto zaprasza i do jakiej ligi (`InviteNotice.jsx`), ale formularz ma 4 pola z powtórzeniem hasła, a po dołączeniu jest sztuczne 1,5 s. | `index.html:17,24`, `App.jsx:155-160`, `AuthContext.jsx:84-91`, `Register.jsx:101-156`, `JoinByLink.jsx:30` | wysoka (kod), średnia (waga) |
| 5 | **Pusty powrót i zły moment.** Mundial się skończył. Od poniedziałku wyniki poprzedniego tygodnia są schowane za strzałką (`LeagueCoupon.jsx:26,164,226`). W przerwie reprezentacyjnej (12–17.11) kupon jest pusty, bo nie ma Ligi Narodów ani możliwości ręcznego dodania meczu. | kod, [terminarz UEFA](https://www.uefa.com/uefanationsleague/news/0298-1d6ef1acfaef-b54fcf1da859-1000--2026-27-uefa-nations-league-all-you-need-to-know) | średnia |
| 6 | **Za dużo do zrozumienia:** 5 zakładek, obserwowanie rozgrywek obok zakresu ligi, „Hity tygodnia” obok „Kuponu tygodnia”, tryby rankingu, joker tylko w trybie „kupon”. | `domain/joker.py:17`, `FollowButton.jsx`, `Welcome.jsx`, `pomysly.md` | średnia |
| 7 | **Autor niczego nie mierzy**, więc nie wie, która z przyczyn waży najwięcej. | `db/queries/admin.py:56-64` (6 liczb), `001_init.sql:15-22` (brak `last_seen_at`) | wysoka |

Zastrzeżenie: bez danych nie da się tych przyczyn zważyć. Jeśli zapytanie E pokaże, że w czerwcu typowało 20 osób, a dziś 2, głównym problemem jest powrót po turnieju (1, 2, 5). Jeśli nowych kont od 1.10 prawie nie ma, problem polega na tym, że nikt ich jeszcze nie zaprosił (3).

### 2.2 Pomiar: zapytania do produkcyjnego Neona

Uruchamiać w SQL Editorze Neona, najlepiej z rolą tylko do odczytu. **Zapytanie E zwraca adresy e-mail znajomych: nie wklejać wyników do czatu z AI ani nigdzie publicznie.**

```sql
-- A. Lejek: konto -> liga -> pierwszy typ, nowi od 1.10
SELECT u.id, u.nick, u.created_at AT TIME ZONE 'Europe/Warsaw' AS registered,
       MIN(plm.joined_at) AS first_league, MIN(p.created_at) AS first_pick,
       ROUND(EXTRACT(EPOCH FROM MIN(p.created_at) - u.created_at)/3600, 1) AS h_to_first_pick,
       COUNT(DISTINCT p.id) AS picks_total
FROM users u
LEFT JOIN private_league_members plm ON plm.user_id = u.id
LEFT JOIN predictions p ON p.user_id = u.id
WHERE u.created_at >= '2026-10-01'
GROUP BY u.id ORDER BY u.created_at;

-- B. Aktywni tygodniowo = typ na mecz z danego tygodnia
SELECT date_trunc('week', m.kickoff_at AT TIME ZONE 'Europe/Warsaw')::date AS week,
       COUNT(DISTINCT p.user_id) AS active_typers, COUNT(*) AS picks
FROM predictions p JOIN matches m ON m.id = p.match_id
WHERE m.kickoff_at >= '2026-05-01'
GROUP BY 1 ORDER BY 1;

-- C. Kohorty: tydzień rejestracji x tydzień życia
WITH act AS (
  SELECT DISTINCT p.user_id, date_trunc('week', m.kickoff_at AT TIME ZONE 'Europe/Warsaw')::date AS wk
  FROM predictions p JOIN matches m ON m.id = p.match_id),
coh AS (
  SELECT id AS user_id, date_trunc('week', created_at AT TIME ZONE 'Europe/Warsaw')::date AS cohort FROM users)
SELECT c.cohort, (a.wk - c.cohort)/7 AS week_n, COUNT(DISTINCT a.user_id) AS active,
       (SELECT COUNT(*) FROM coh c2 WHERE c2.cohort = c.cohort) AS cohort_size
FROM coh c JOIN act a ON a.user_id = c.user_id AND a.wk >= c.cohort
GROUP BY 1, 2 ORDER BY 1, 2;

-- D. Wypełnienie kuponu w ligach: % członków z >=1 typem i z kompletem
WITH cp AS (
  SELECT lc.id, lc.private_league_id, lc.week_start, COUNT(*) AS n
  FROM league_coupons lc JOIN league_coupon_matches lcm ON lcm.coupon_id = lc.id GROUP BY 1, 2, 3),
per_user AS (
  SELECT cp.private_league_id, cp.week_start, cp.n, plm.user_id, COUNT(p.id) AS typed
  FROM cp
  JOIN private_league_members plm ON plm.private_league_id = cp.private_league_id AND plm.joined_at < cp.week_start + 7
  JOIN league_coupon_matches lcm ON lcm.coupon_id = cp.id
  LEFT JOIN predictions p ON p.match_id = lcm.match_id AND p.user_id = plm.user_id
  GROUP BY 1, 2, 3, 4)
SELECT pl.name, week_start, COUNT(*) AS members,
       ROUND(100.0*AVG((typed > 0)::int)) AS pct_any, ROUND(100.0*AVG((typed >= n)::int)) AS pct_full
FROM per_user JOIN private_leagues pl ON pl.id = per_user.private_league_id
GROUP BY pl.name, week_start ORDER BY pl.name, week_start;

-- E. Gracze Mundialu, którzy nie wrócili (lista do reaktywacji)
SELECT u.nick, u.email, COUNT(*) AS wc_picks, MAX(m.kickoff_at) AS last_wc
FROM predictions p JOIN matches m ON m.id = p.match_id JOIN users u ON u.id = p.user_id
WHERE m.kickoff_at < '2026-08-01'
  AND NOT EXISTS (SELECT 1 FROM predictions p2 JOIN matches m2 ON m2.id = p2.match_id
                  WHERE p2.user_id = u.id AND m2.kickoff_at >= '2026-08-01')
GROUP BY u.id ORDER BY wc_picks DESC;

-- F. Kiedy ludzie typują (dobór godzin przypomnień)
SELECT EXTRACT(ISODOW FROM created_at AT TIME ZONE 'Europe/Warsaw') AS dow,
       EXTRACT(HOUR FROM created_at AT TIME ZONE 'Europe/Warsaw') AS hour, COUNT(*)
FROM predictions WHERE created_at >= '2026-06-01' GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 15;
```

Na później (po starcie ligi): kolumna `users.last_seen_at` (aktualizowana w `get_current_user` najwyżej raz na godzinę), tabela `events(user_id, kind, meta, created_at)` dla `register`, `join_league`, `open_from_reminder` (parametr `?r=mail_pt` w linkach z maili) i Umami albo GoatCounter na froncie (darmowe, bez cookies). Nakład S, głównie Python.

### 2.3 Pętla zaangażowania: tydzień gracza

Zasada: **jedno przypomnienie przed terminem, jedno podsumowanie po kolejce, najwyżej 3 wiadomości tygodniowo, przypomnienia tylko do tych, którym czegoś brakuje.** Kanał podstawowy to mail z własnej domeny, bo działa wszędzie i bez instalacji. Treść ma się zmieniać, bo ta sama wiadomość szybko traci skuteczność (Duolingo, [Yancey & Settles, KDD 2020](https://research.duolingo.com/papers/yancey.kdd20.pdf)). Maile generowane w Pythonie (Jinja), bez nowych ekranów w React.

| Kiedy | Kanał | Do kogo | Przykładowa treść | Kiedy wdrożyć |
|---|---|---|---|---|
| **Pt 17:00** | mail | kto ma braki w kuponie | „Weekend: masz 0/7. Pierwszy mecz w sobotę 13:30. 5 z 8 osób już wytypowało. [Wytypuj w minutę]” | **przed startem** |
| **Pon 9:00** | mail | wszyscy w lidze | „🏆 Tydzień w »Ekipa z AGH«: wygrał **Kuba** (+19). Ty: +11, 3. miejsce (▲1). Czutka tygodnia: Michał trafił 3:1 w Arsenal–Spurs. Nowy kupon: 10 meczów, pierwszy we wtorek 21:00 → [Typuj]” | tydzień +1 |
| **Wt 12:00** (tydzień z LM) | mail | kto nie wytypował meczów LM | „Dziś Liga Mistrzów: Real–Liverpool i 2 inne mecze z kuponu. Zamyka się o 21:00. Kuba już wytypował 😏” | tydzień +2 |
| Sob, 2 h przed pierwszym meczem | Web Push | wciąż z brakami | „Za 2 h Chelsea–United. Brakuje Ci 4 typów.” | później (Web Push to P2) |
| Ndz wieczór | gospodarz, ręcznie | grupa na Messengerze | obrazek tygodnia (już istnieje, `utils/weekImage.js`) | od startu |

Wymagania: link „wypisz się” w każdym mailu (podpisany token), wyłącznik w Ustawieniach (prosty przełącznik, później), informacja przy rejestracji. Resend Free: 100 maili dziennie, 3000 miesięcznie ([cennik](https://resend.com/pricing)), z dużym zapasem dla jednej czy dwóch lig. Web Push na iPhonie działa tylko po dodaniu aplikacji do ekranu głównego ([WebKit](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)), dlatego nie jest kanałem podstawowym.

Technicznie przypomnienia nie mogą zależeć tylko od schedulera w procesie API, który na darmowym Renderze śpi, gdy keep-alive zawiedzie. Na start wystarczy ten sam scheduler (Render nie śpi dzięki keep-alive) plus tabela `notification_log` dla idempotencji i healthchecks.io jako alarm, gdy mail nie wyjdzie. Zewnętrzny tick (`POST /internal/tick` z Cloudflare Worker Cron) to krok późniejszy (rozdz. 8.3).

### 2.4 Plan uruchomienia krok po kroku

**Kiedy:** start w weekend **21–22.11**, zaraz po przerwie reprezentacyjnej. Przerwa daje dwa tygodnie na poprawki, a po niej jest naturalny „nowy początek”. Do świąt mieści się 5 tygodni z dwiema kolejkami LM (24/25.11 i 8/9.12, [UEFA](https://www.uefa.com/uefachampionsleague/news/02a6-20d57cfcd03e-407c22a7f465-1000--2026-27-champions-league-teams-dates-draws-format-final/)) i maratonem świątecznym Premier League. Jeśli minimum przed startem (niżej) nie będzie gotowe, **przesunąć start na 28–29.11**, a nie startować z aplikacją, która wylogowuje i nie przypomina.

**Kogo:** jedna grupa 8–15 osób z wspólnym czatem, z gospodarzem innym niż autor. Zakres: **Premier League + Liga Mistrzów**, kupon ok. 8–10 meczów, bez innych lig i bez bonusów poza dwoma pytaniami sezonowymi (mistrz PL, zwycięzca LM).

**Minimum przed startem (ok. 20–25 h, czyli to, co realnie mieści się w 2,5 tygodnia):**

| Co | Czas | Python / React |
|---|---|---|
| Lista „na najbliższe dni” z rozdz. 1 | ok. 6 h | głównie Python |
| Piątkowe przypomnienie mailem: SQL braków per gracz, szablon Jinja, wysyłka w schedulerze, `notification_log`, link wypisania | 8–10 h | Python |
| Tekst „Budzę serwer…” po 3 s w spinnerze `ProtectedRoute`/`HomeRoute`, usunięcie 1,5 s w `JoinByLink.jsx`, jedno pole hasła zamiast dwóch | 1–2 h | React (małe zmiany) |
| `SameSite=Lax` (po sprawdzeniu, że front woła `/api` na tej samej domenie) | 15 min | Python |
| Backup: nocny `pg_dump` do Cloudflare R2 przez GitHub Actions | 2–3 h | YAML |
| Test na prawdziwych telefonach (iPhone + Android, link z Messengera) | 1 h | — |

Reszta (podsumowanie poniedziałkowe, wtorkowe przy LM, uproszczenia, publiczny `/join`, Werdykt) idzie **po** starcie, w tygodniach +1 do +4.

| Tydzień | Daty | Co robimy |
|---|---|---|
| −2 | 4–8.11 | Krok zero (2.0). Lista „na najbliższe dni”. |
| −1 | 9–20.11 | Reszta minimum przed startem. Gospodarz zakłada ligę, ustawia „Na co gramy?” i 2 pytania sezonowe z terminem 21.11 12:00 (rejestracja ma sens także w przerwie). Pon 16.11: test na telefonach z 2–3 osobami. |
| 0 | czw 19.11 | Gospodarz pisze na grupie (od kumpla, nie od autora aplikacji): „Od soboty gramy w typera. Co tydzień ~10 hitów z PL i LM, 5/3/2 pkt. Przegrany rundy (do świąt) stawia pizzę zwycięzcy. Rejestracja to minuta, a przed startem obstawcie mistrza PL: [link]”. |
| +1 | 21–29.11 | Pierwsza kolejka. Autor ręcznie pomaga każdemu, komu coś nie działa. Poniedziałkowe podsumowanie mailem (6–8 h, Python). **Środa 25.11: decyzja o aktywacji** (patrz progi). |
| +2 | 30.11–6.12 | Wtorkowe przypomnienie przy LM. Werdykt na Starcie do wtorku 12:00 (S, React). |
| +3 | 7–13.12 | **Punkt decyzji o retencji.** LM 8/9.12. |
| +4–5 | 14–27.12 | Maraton świąteczny. Koniec „rundy jesiennej”: zwycięzca ogłoszony obrazkiem, wręczenie pizzy. |
| +6–7 | 28.12–10.01 | Decyzja o drugiej grupie. |

**Progi** (przy 8–12 osobach w liczbach bezwzględnych, bo jedna osoba to ponad 10 p.p.):

| Metryka | Sukces | Porażka | Co zrobić przy porażce |
|---|---|---|---|
| Aktywacja: zaproszeni z kontem i ≥1 typem w 48 h (decyzja 25.11) | wszyscy poza najwyżej 2 osobami | połowa lub mniej | logowanie kodem z maila, rejestracja bez hasła (M) |
| Typujący kupon w tygodniu +3 | ≥ 3/4 grupy | ≤ połowa | krótszy kupon (5 meczów), przypomnienie wtorkowe także od gospodarza |
| Kompletne kupony | ≥ połowa grupy | ≤ 1/4 | kupon za długi lub terminy za wcześnie |
| Grający w tygodniu +4 vs +1 | ubyła najwyżej 1–2 osoby | odpadła połowa | format, nie funkcje: jeden mecz tygodnia, mecze Polski, albo powrót na fazę pucharową LM |
| Sygnały organiczne | ktoś sam wrzuca obrazek, pyta o drugą ligę | cisza | rozmowa z gospodarzem |

Przy porażce najpierw 15-minutowe rozmowy z 3 osobami, które odpadły, i z gospodarzem, potem **jedna** zmiana naraz.

**Plan awaryjny na awarię w trakcie kolejki:** gospodarz dostaje od autora gotowy tekst („czutka leży, typy wrzućcie tu na czat, wpiszę je ręcznie”), a admin może wpisać wynik ręcznie (`POST /matches/{id}/result` już istnieje). Healthchecks.io i UptimeRobot powiadamiają autora mailem.

**Stawka a prawo:** bez wpisowego i bez puli pieniężnej. Typer, w którym gracze wpłacają i wygrywają pieniądze zależne od wyników, może być zakładem wzajemnym w rozumieniu ustawy o grach hazardowych ([SMMLegal24](https://smmlegal24.pl/polska-gola-kilka-slow-o-legalnym-typowaniu-wynikow-meczow/)). Bezpieczne stawki: pizza, piwo, puchar przechodni za 30 zł. Pole „Na co gramy?” powinno mieć podpowiedź „bez wpłat pieniędzy”. To nie jest porada prawna.

### 2.5 Utrzymanie przez sezon

- **Stały rytm, nic więcej:** poniedziałek podsumowanie, wtorek/środa LM, piątek przypomnienie, niedziela obrazek.
- **Rundy zamiast jednego długiego sezonu:** ranking ligi resetowany co 6–8 tygodni („jesienna” do świąt, „zimowa” do lutego, „wiosenna” do maja, „finałowa” do finału LM 5.06.2027), z ogłoszeniem zwycięzcy. Kto odpadł w tabeli, ma powód wrócić na nową rundę. Odznaki są (`domain/league_badges.py`), brakuje ich ogłoszenia na koniec rundy. Nakład M.
- **Mini-wydarzenia:** tydzień derbów (lista derbów już jest w `domain/coupon.py`), tydzień LM, maraton świąteczny, faza pucharowa LM z wyższą punktacją (już jest w profilu `uefa_cup`).
- **Przerwy reprezentacyjne:** mecz Polski i kilka hitów LN dodane ręcznie przez admina (nowy endpoint i „ręczny dostawca”, rozdz. 8.4) albo pytanie sezonowe. Nie pusty kupon.
- **Reaktywacja:** kto nie typował 2 tygodnie z rzędu, dostaje jeden mail („Kuba prowadzi o 6 pkt, a Ty masz jokera. Wracasz?”). Po 4 tygodniach ostatnia, ręczna wiadomość od gospodarza, potem cisza. Gracze Mundialu z zapytania E dostają jednorazowy mail przed startem 21.11.
- **Nagrody sezonowe bez pieniędzy:** koronacja mistrza rundy z obrazkiem, 👑 przy nicku przez następną rundę, puchar przechodni.

---

## 3. Analiza konkurencji

Oznaczenia: liczby i funkcje ze źródłami (lista na końcu rozdziału), wnioski oznaczone jako wnioski. Część dokumentów autora (`docs/rozwoj/analiza-biznesowa.md`) wymaga korekty:

- **Pominięty najgroźniejszy rywal w Polsce: kicktipp.pl** z darmowym typerem PKO BP Ekstraklasy i 1. Ligi, a od sezonu 2026/27 z punktacją zależną od kursów [3].
- Liczby Kicktippa (6,5 mln graczy na MŚ 2026, ok. 1 mln € przychodu, ok. 500 tys. € zysku, dwie osoby) i cennik Profipaket się potwierdzają [1][2].
- „Goal.pl z nagrodą STS”: typer prowadził Better Collective (afiliant bukmacherski), nagrodą były bilety, punktacja „bukmacherska” (1X2, BTTS, over/under), bez lig prywatnych [4].
- Superbru „2,9 mln” się nie potwierdza: Wikipedia podaje 1,5 mln (2018), karta aplikacji „prawie 2 mln” [7][8].
- Office World Cup: 316 firm, 3470 graczy [5]. Progów cenowych 49/129/399 £ nie udało się potwierdzić, cennik zdjęto ze strony.

### 3.1 Krótkie profile

**Zagraniczne typery**
- **Kicktipp / kicktipp.pl** [1][2][3][11][12][13]: typer grupowy od lat 90. Punktacja do wyboru (2/3/4, reguła kursowa „Quotenregel”), joker ×2, pytania bonusowe, czat, tabela na żywo. **Push i mail tylko do tych, którzy nie wytypowali.** Reklamy + Premium 4,99 €/rok + Profipaket dla firm od 9,90 €/mies. Wniosek: wzorzec „nudny, ale niezawodny”. Wygrać z nim można designem, tonem i obsługą telefonu, nie listą funkcji.
- **Superbru** [8][15][16][17]: ponad 80 rozgrywek rocznie, do 10 pul prywatnych, logowanie Apple, **plakietka na ikonie z liczbą typów do oddania w 24 h**, push przy trafionym dokładnym wyniku. Reklamy, Premium 3,49 $/mies., „Megapools” dla marek. Ruch rośnie ok. 5× w minutę po końcu meczu.
- **Sky Super 6** [18][19][20]: 6 meczów w kolejce (dokładnie format kuponu tygodnia), 5 pkt za wynik, 2 za rezultat, remisy rozstrzyga minuta pierwszego gola, „Beat the Pundit”. Lejek Sky Bet, tylko UK/IE.
- **BBC Predictor** już nie działa [15][21]. **Premier League Matchweek/Table Predictor** [22][23]: oficjalne gry ligi; „tabela na koniec sezonu” to tanie pytanie bonusowe.
- **MonPetitProno** [32]: 1,1 mln graczy na Euro 2020, punkty zależne od kursów, „boost”. Gra tylko turnieje, bo „sezon ligowy nudzi”. Sygnał ostrzegawczy dla czutki.
- **Nowe małe aplikacje 2025–2026** [27–31]: Tippster (jeden twórca, PWA bez iOS, za darmo, **przeciwnik AI w każdej grupie**), Tippr (dołączenie bez obowiązkowego konta, typy znajomych od gwizdka, joker), BeTeam (link do WhatsAppa, czat i emoji pod typami, 3500+ lig na MŚ 2026), Flipseer (dołączenie „w mniej niż 2 minuty”). Wniosek: funkcje, z których czutka jest dumna, to dziś standard.

**Polskie**
- **League Mates** [9][10]: Ekstraklasa, 1.–3. liga, top ligi, puchary, ligi firmowe, „3000+ aktywnych” (deklaracja z 12.2025), skargi na logowanie w czasie MŚ.
- **Footrise** [33]: kod ligi, „Gorący Typ” ×2, ranking „Hot 9”, rankingi miesiąca i roku, ligi społeczności, utrzymuje się z darowizn.
- **liga-typera.pl** [34]: Ekstraklasa, mini-ligi, ligi firmowe. **LigaTyperska.pl**: blokuje pobieranie, nie zweryfikowano.
- **Typery bukmacherów** [36]: STS Wizjoner, Superbet SuperGame, ComeOn, forBET. Wymagają konta u bukmachera, są lejkiem do zakładów. O Fortunie, Betclicu i LV BET z lat 2025–26 brak potwierdzonych danych.
- **Portale:** WP Typer (logowanie przez Facebooka) [37]. Typery Meczyków, Sport.pl, Kanału Sportowego: brak danych.

**Fantasy**
- **FPL** [38][39][40]: 13,1 mln graczy w 2025/26, ligi klasyczne i H2H, dwa komplety chipów na sezon (po jednym na połowę), deadline jako oś tygodnia, przypomnienia push + mail + kalendarz.
- **UEFA Gaming / Predict Six** [41]: 6 wyników + „kto pierwszy strzeli”, booster ×2.
- **LOTTO Fantasy Ekstraklasa** [42]: „Duety” (pojedynki), Premium z większą liczbą lig i Jokerem.
- **Sorare** [43]: zwolnienie ok. 35% załogi (XI 2025), spadek przychodu. Przestroga przed mechanikami kolekcjonerskimi.

**B2B**
- **Scorecast Business** [44]: od 290 € (100 graczy) i 390 € (Enterprise) za turniej, 400+ firm, branding, ranking działów, newslettery, SSO jako dodatek.
- **Office World Cup / Office Rivals** [5][6]: bot w Slacku / Google Chat, poranne okna wysyłki, ranking firm według średniej na gracza, darmowo do 5 graczy, potem przepustki sezonowe.
- **Kicktipp Profipaket** [2]: 9,90 € (do 100 osób) do 149,90 €/mies. (do 3000).

### 3.2 Tabela porównawcza

T = tak, N = nie, ? = brak danych, (p) = płatne.

| Produkt | Ligi prywatne | Link/kod | Logowanie bez hasła / społ. | Aplikacja natywna | Push | Mail-przypomnienia | Dokładny wynik | Joker ×2 | Bonusy | H2H | Czat | Nagrody | Ekstraklasa | Model |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **czutka (dziś)** | T | T | **N** | N (PWA) | **N** | **N** | T | T (warunkowo) | T | N | emoji | N | **N** | darmowe |
| Kicktipp / .pl | T | T | ? | T | T | T | T | T | T | ? | T | N | **T** | reklamy, premium, B2B |
| Superbru | T | T | T (Apple) | T | T + plakietka | ? | T | ? | T | ? | T | T | N | reklamy, premium, sponsoring |
| Sky Super 6 | T | ? | N (KYC 18+) | T | ? | ? | T | N | tie-break | N | N | T | N | lejek bukmachera |
| UEFA Predict Six | T | ? | ? | T | ? | ? | T | T | T | N | N | ? | N | marketing UEFA |
| Tippster | T | T | ? | Android + PWA | T | ? | T | T | T | N | T | N | N | darmowe |
| Tippr | T | T (kod, QR) | bez obow. konta | T | T | ? | T | T | ? | N | ? | N | ? | freemium |
| BeTeam | T | T | ? | T | ? | ? | T | ? | T | N | **T + emoji** | N | ? | darmowe |
| League Mates | T | ? | ? | ? | ? | ? | T | ? | ? | ? | ? | ? | **T** | darmowe |
| Footrise | T | T | ? | T | ? | ? | T | T | T | N | N | N | ? | darowizny |
| STS / Superbet | N | N | N (konto buka) | T | T | ? | T | N | T | N | N | T | T | lejek bukmachera |
| FPL | T | T | ? | T | T | T | n/d | chipy | n/d | **T** | N | T | N | marketing ligi |
| Fantasy Ekstraklasa | T | ? | ? | T | ? | ? | n/d | (p) | n/d | **T** | ? | T | **T** | premium + sponsor |
| Scorecast Business | T (działy) | T | SSO (p) | T | ? | T | T | ? | T | drużyny | ? | od firmy | ? | 290–390 €/turniej |
| Office World Cup / Rivals | T | kanał | konto Slack/Google | Slack | DM | n/d | T | mnożnik | T | działy | Slack | N | N | free ≤5, przepustki |

**Wniosek z tabeli:** czutka ma „grę” na poziomie najlepszych (joker, kupon, typy po gwizdku, reakcje, tabela live, bonusy), a odstaje w „rurach”: logowanie, przypomnienia, push, Ekstraklasa. Właśnie tam konkurencja ma standard.

### 3.3 Mechaniki retencji, które działają (dla małej grupy znajomych)

1. **Przypomnienie tylko do tych, którzy nie wytypowali, tuż przed terminem** (Kicktipp, Superbru, OWC). Czutka: brak. Najważniejsze.
2. **Odsłonięcie typów przy gwizdku + powiadomienie o zmianie w tabeli** („Gol! Kuba wskoczył na 1. miejsce”). Czutka ma odsłonięcie, brakuje „wypchnięcia”.
3. **Rywalizacja z konkretnymi ludźmi, nie z tłumem** (MPP: gracze zostają, żeby być wyżej niż znajomi).
4. **Krótkie cykle w długim sezonie** (Footrise: ranking miesiąca, FPL: chipy na połowę sezonu). Odpowiedź na „jestem 40 pkt za liderem, odpuszczam”.
5. **Rzadki zasób decyzyjny** (joker, booster). Czutka ma, ale tylko w trybie „kupon”.
6. **Punktacja nagradzająca odwagę** (Kicktipp Quotenregel, OWC +2 za niespodziankę). W czutce można to liczyć z typów grupy, bez kursów bukmacherskich.
7. **Pojedynki H2H w kolejce** (FPL, Fantasy Ekstraklasa Duety).
8. **Podsumowanie i karta do udostępnienia** (OWC poranny skrót, karty Tippstera). Czutka ma obrazek, brakuje automatycznej dystrybucji.
9. **Bot lub ekspert jako punkt odniesienia** (Beat the Pundit, Tippy).
10. **Serie i odznaki**: słabszy efekt przy rytmie tygodniowym. Czutka już je ma, nie inwestować dalej.

### 3.4 Wnioski dla czutki

1. **Najpierw „rury”, potem funkcje.** Przypomnienia, długa sesja, działające maile. To jest różnica między czutką a każdym długowiecznym konkurentem.
2. **Dołączenie w 30 sekund.** Pełny obrazek w podglądzie linku, nazwa ligi w tytule, rejestracja bez hasła (kod z maila). Tippr i Flipseer pokazują, że da się to zrobić w małej aplikacji.
3. **Skopiować poranny skrót** z Office World Cup: jeden mail w poniedziałek rano z wynikami, obrazkiem i nowym kuponem.
4. **Pociąć sezon na rundy** (reset co 6–8 tygodni) i „mistrza miesiąca”. Bezpośrednia odpowiedź na problem, przez który MPP w ogóle nie gra sezonów.
5. **„Czutkobot” jako tani wyróżnik:** bot typujący według formy i tabeli (dane już są w `domain/match_context.py`), z polskimi docinkami w obrazku tygodnia („3 osoby przegrały z botem”). Kilka godzin w Pythonie, zero frontu poza etykietą. Do rozważenia po P0.
6. **Pozycjonowanie: „polski typer dla ekipy, bez bukmachera, z jajem”.** Wszystkie masowe darmowe typery w Polsce to lejki bukmacherów. Uwaga na spójność: panel kontekstu meczu pokazuje BTTS i over 2,5 (`MatchContextPanel.jsx:104-108`), czyli język bukmacherski. Usunąć.
7. **Ekstraklasa jest realną luką**, ale nie trzeba za nią płacić od razu: zacząć od meczów dodawanych ręcznie (rozdz. 8.4).
8. **Nie robić czatu** (grupa ma Messengera), **natywnej aplikacji** (przed retencją), **nagród od czutki**, **afiliacji bukmacherów**, mechanik kolekcjonerskich ani wyścigu na liczbę rozgrywek.
9. **B2B: wzorzec Office World Cup** (bot w Slacku/Teams, poranne DM, ranking według średniej) jest ciekawszy niż własny panel HR. Ale dopiero w etapie 2.

### 3.5 Źródła (konkurencja)

[1] [ZDF heute, Kicktipp-Boom, 21.06.2026](https://www.zdfheute.de/sport/fussball-wm/fussball-wm-2026-kicktipp-tippspiel-boom-100.html) · [2] [Kicktipp Profipaket – ceny](https://www.kicktipp.de/info/profipaket/preise) · [3] [kicktipp.pl – PKO BP Ekstraklasa](https://www.kicktipp.pl/pko-bp-ekstraklasa/) · [4] [Goal.pl – regulamin typera MŚ 2026](https://www.goal.pl/regulamin-konkursu-typer-na-mundial-2026/) · [5] [Office World Cup](https://officeworldcup.com/) · [6] [Office Rivals](https://workspace.google.com/marketplace/app/office_rivals/540577245291) · [7] [Wikipedia – Superbru](https://en.wikipedia.org/wiki/Superbru) · [8] [App Store – Superbru](https://apps.apple.com/app/id613066215) · [9] [League Mates](https://leaguemates.pl/) · [10] [Wykop – League Mates](https://wykop.pl/ludzie/league-mates) · [11] [App Store – Kicktipp](https://apps.apple.com/app/id570703120) · [12] [netzwelt – powiadomienia Kicktipp](https://www.netzwelt.de/anleitung/231779-kicktipp-so-aktiviert-benachrichtigungen.html) · [13] [buli-tipphilfe – reguły Kicktipp](https://buli-tipphilfe.de/kicktipp-strategie) · [15] [Superbru – BBC predictor alternative](https://www.superbru.com/premierleague_2019_20/bbc_predictor_alternative.php) · [16] [App Store – Superbru Football](https://apps.apple.com/us/app/-/id6450757084) · [17] [Superbru business](https://superbru-cdn.superbru.com/business) · [18] [Super 6 – zasady](https://footballpredictions.com/betting-tips/super-6/) · [19] [App Store UK – Super 6](https://apps.apple.com/gb/app/id662094510) · [20] [Football Critic – Super 6](https://www.footballcritic.com/news/super-6-how-the-sky-sports-game-swept-a-nation/3805) · [21] [Archiwum BBC Predictor](https://webarchive.archive.unhcr.org/20170829211926mp_/http://www.bbc.co.uk/sport/football/predictor) · [22] [PL Matchweek Predictor](https://www.premierleague.com/EN/games/premier-league-matchweek-predictor/rules-faqs) · [23] [PL Table Predictor](https://www.premierleague.com/en/games/pl-table-predictor-2025-26/rules-faqs) · [27] [Tippster](https://tippster.app/en/prediction-game-alternative) · [28] [Tippr](https://playtippr.de/en/football-pool-with-friends) · [29] [BeTeam](https://beteamapp.com/) · [30] [Flipseer](https://www.flipseer.com/leagues/friends) · [31] [Rivalix](https://apps.apple.com/app/rivalix/id6762013052) · [32] [90min – wywiad MonPetitProno](https://www.90min.com/fr/posts/interview-martin-jaglin-co-fondateur-de-monpetitprono-revient-sur-le-succes-de-l-appli-pendant-l-euro) · [33] [Footrise](https://footrise.app/pl) · [34] [liga-typera.pl](https://liga-typera.pl/typowanie/ekstraklasa/) · [36] [Meczyki – darmowe typowanie](https://www.meczyki.pl/bukmacherzy/darmowe-typowanie-ms-gdzie-odebrac-freebet-na-mundial/301) · [37] [Antyweb – WP Typer](https://antyweb.pl/wp-typer-typowanie-wynikow-mundial) · [38] [Wikipedia – FPL](https://en.wikipedia.org/wiki/Fantasy_Premier_League) · [39] [PL – zmiany FPL 2025/26](https://www.premierleague.com/en/news/4362211) · [40] [PL – rekord Bench Boost GW1 2026/27](https://www.premierleague.com/en/news/4690601/record-number-of-fpl-managers-bench-boost-in-gameweek-1) · [41] [App Store – UEFA Gaming](https://apps.apple.com/us/app/-/id1107602457) · [42] [Ekstraklasa – LOTTO Fantasy](https://ekstraklasa.org/en/news/lotto-fantasy-ekstraklasa-is-back/) · [43] [Maddyness – Sorare](https://www.maddyness.com/2025/11/21/sorare-envisage-de-se-separer-de-35-de-ses-effectifs-pour-viser-un-retour-a-la-profitabilite-en-2026/) · [44] [Scorecast Business](https://www.scorecastbusiness.com/en/competitions/world-cup)

---

## 4. Bugi i rzeczy do naprawy

Wszystkie pozycje potwierdzone w kodzie; tam, gdzie podano dowód, odtworzone lokalnie (osobne bazy na Postgresie 16 z migracjami 001–013, skrypty PoC). Waga uwzględnia cel „znajomi mają chcieć używać”.

| # | Plik:linia | Opis | Proponowane rozwiązanie | Waga |
|---|---|---|---|---|
| 1 | `services/sync.py:29,461-476,493-508`, `main.py:66,104-112` | Gdy synchronizacja jest włączona (`SYNC_ENABLED` + `FOOTBALL_API_KEY`, `main.py:66`), scheduler co 60 s robi 4 zapytania do bazy, a keep-alive co 10 min woła `/health` z `SELECT 1`. Jeśli keep-alive działa (Render nie śpi), Neon nie dostaje 5 minut ciszy i nie usypia: ok. 186 CU-h/mies. przy limicie 100 CU-h. Po wyczerpaniu baza jest wyłączona do końca okresu rozliczeniowego ([Neon](https://neon.com/faqs/free-plan-limits-and-quotas)). [env: zależy od zmiennych, działania keep-alive i daty okresu rozliczeniowego] | Dziś: Usage w Neonie. Najtańsza poprawka w samym `sync.py`: decyzja „czy coś jest należne” z pamięci (stan ostatnich przebiegów z TTL), baza tylko gdy przebieg jest należny. `/health/live` bez bazy dla keep-alive, `/health/ready` z bazą. Później zewnętrzny tick (rozdz. 8.3). | **krytyczna** (jeśli warunki spełnione) |
| 2 | `routers/auth.py:93,103`, `routers/auth.py:318-322`, `src/context/AuthContext.jsx:19-30` | Sesja wygasa 7 dni po zalogowaniu niezależnie od aktywności. `/auth/me` nie odświeża cookie, a `setInterval` co 6 dni praktycznie nie działa. | W `get_current_user` (albo w `/auth/me`): gdy `iat` starszy niż 24 h, ustawić nowe cookie. `JWT_EXPIRE_DAYS=90`. Usunąć `setInterval`. | **krytyczna** |
| 3 | `services/email.py:13,40-62`, `.env.example` | [env] Domyślny nadawca `onboarding@resend.dev` (notatki autora potwierdzają brak własnej domeny na produkcji): maile (reset hasła, weryfikacja) docierają tylko do właściciela konta Resend. Nazwa „Mundial Typer” w mailach. | Zweryfikować domenę `czutka.uk` w Resend (SPF/DKIM w Cloudflare), `EMAIL_FROM="czutka <hej@czutka.uk>"`, nowe teksty. | **krytyczna** |
| 4 | `mundial-frontend/index.html:17,24` | `og:image` i `twitter:image` względne (potwierdzone na produkcji). Podgląd linku zaproszenia na Messengerze/WhatsAppie bez obrazka. | `https://www.czutka.uk/og-image.png`, sprawdzenie w [Sharing Debuggerze](https://developers.facebook.com/tools/debug/). Docelowo tytuł z nazwą ligi dla `/join/KOD` (pkt 19). | **wysoka** |
| 5 | `db/migrations/001_init.sql:118`, `db/queries/users.py:221-234` | `private_leagues.owner_user_id` bez `ON DELETE`, a `delete_user` nie obsługuje lig właściciela. Usunięcie konta przez właściciela jakiejkolwiek ligi (także `DELETE /admin/users/{id}`) kończy się 500 (ForeignKeyViolation, odtworzone). Brak testu. Problem RODO. | Migracja 014: przekazanie własności najstarszemu członkowi, a gdy nikt nie zostaje, usunięcie ligi. Test integracyjny. | **wysoka** |
| 6 | `db/connection.py:44` | `ThreadedConnectionPool(minconn=1)`: psycopg2 zamyka przy zwrocie każde połączenie ponad `minconn` (`psycopg2/pool.py`, `_putconn`). Pomiar: 6 wątków × 10 zapytań = 41 nowych połączeń TLS na 60 zapytań. Każdy ekran ładuje kilka endpointów, a endpoint robi 3–10 osobnych `get_conn`. Brak `connect_timeout`, `statement_timeout`, sprawdzania martwych połączeń po uśpieniu Neona. | Od razu `minconn=maxconn` (np. 5) i `keepalives` w DSN. Docelowo `psycopg_pool` (psycopg 3) z `check` i `max_idle`. `connect_timeout=5`, `statement_timeout=10s`. | **wysoka** |
| 7 | `routers/auth.py:80-86` | Rate limit logowania bierze pierwszy wpis `X-Forwarded-For`. Render dopisuje do nagłówka, a backend jest publiczny pod `mundial-backend-h3al.onrender.com`, więc limit da się obejść ustawiając nagłówek (PoC: 20 prób bez blokady). Słowniki limitów rosną bez końca. | Limit także per e-mail (w bazie), IP z prawej strony łańcucha, zamknięcie bezpośredniego dostępu (sekret w nagłówku dodawany przez rewrite albo Cloudflare Tunnel), czyszczenie starych kluczy. | **wysoka** |
| 8 | `routers/auth.py:61-62` | [env] `SameSite=None` przy `COOKIE_SECURE=true`, choć produkcja jest same-origin (rewrite Vercela) i ADR #003 zakłada `Lax`. Endpointy JSON chroni FastAPI (odrzuca `text/plain`), ale 11 POST-ów bez body przyjmie formularz z obcej strony: m.in. `/leagues/{id}/leave`, `/leagues/{id}/reset-code`, `/coupon/regenerate` i 4 endpointy admina. | `SameSite=Lax`, **ale najpierw sprawdzić w DevTools, że front woła `www.czutka.uk/api/...`, a nie bezpośrednio `onrender.com`** (zmienna `VITE_API_URL` na Vercelu); przy cross-origin Lax zepsułby logowanie. Opcjonalnie middleware sprawdzający `Origin`/`Sec-Fetch-Site`. | **wysoka** (poprawka: 1 linia + sprawdzenie) |
| 9 | `domain/sync_plan.py:134-138`, `domain/prediction_lock.py:7-22` | Nierozliczony mecz, który był `live`/`suspended`/`postponed`, wraca od dostawcy jako `scheduled` z nową datą: typowanie otwiera się ponownie, choć wszyscy widzieli cudze typy (odtworzone). Szerzej niż pkt 6 w `do-zrobienia.md`. Brak testu tego przejścia. | Kolumna `matches.locked_at` ustawiana, gdy mecz pierwszy raz jest `live` lub minął `kickoff_at`. `prediction_block_reason` blokuje, gdy jest ustawiona. Backfill. Testy przejść. | średnia |
| 10 | `src/api/axios.js:25-27` | Przy 401 `window.location.href='/login'`: twardy reload, gubi ścieżkę docelową (np. kupon z linku przypomnienia). | `navigate('/login', { state: { from } })` przez kontekst albo parametr `?next=`. | średnia |
| 11 | `src/utils/pendingInvite.js:15` | Kod zaproszenia w `sessionStorage`, który nie przechodzi do nowej karty (link z maila). Komentarz w linii 2 obiecuje coś innego. Dziś bez skutków (weryfikacja wyłączona), ale wróci przy logowaniu kodem/linkiem z maila. | `localStorage` z czasem ważności albo `?next=/join/KOD` przekazywany przez backend w linku z maila. | średnia |
| 12 | `src/pages/JoinByLink.jsx:30`, `src/App.jsx:155-160`, `AuthContext.jsx:84-91` | Sztuczne 1,5 s po dołączeniu. Podczas `/auth/me` przy zimnym serwerze niezalogowany widzi pusty spinner. (Sam ekran rejestracji z zaproszeniem pokazuje już zapraszającego, ligę i liczbę graczy: `InviteNotice.jsx`.) | Usunąć timeout, tekst „Budzę serwer…” po 3 s w spinnerze, jedno pole hasła w `Register.jsx`. | średnia (S, ok. 1–2 h) |
| 13 | cały `src/` | Brak error boundary: wyjątek przy renderowaniu daje biały ekran bez komunikatu. | Jeden `ErrorBoundary` w `App.jsx` z przyciskiem „Odśwież” + Sentry. | średnia |
| 14 | `src/components/CouponRow.jsx:89-95` | Zapis przy wyjściu z ekranu po cichu połyka błąd: typ może zniknąć bez informacji. | Kolejka nieudanych zapisów i toast „Nie zapisano, spróbuj ponownie”. | średnia |
| 15 | `src/components/CouponRow.jsx:150` | Pola wyniku 32×36 px, poniżej zalecanych 44 px dla palca. | Min. 44×44 (docelowo 48×56 w redesignie). | średnia |
| 16 | 133× `text-gray-500`, 12× `text-gray-600` na ciemnym tle | Kontrast 3,67:1 i 2,35:1, poniżej 4,5:1 (WCAG AA). | Podnieść do `gray-400` / tokenu `ink-muted`. | niska–średnia |
| 17 | `routers/auth.py:360-371`, `251-260`, `routers/deps.py:41` | Zmiana i reset hasła nie unieważniają istniejących JWT (PoC: stary token działa). | `users.password_changed_at` (albo `token_version`) porównywane z `iat`. `get_current_user` i tak czyta użytkownika z bazy. | średnia |
| 18 | `db/queries/ranking.py:139-150`, `db/queries/coupon.py:270-293` | Ranking ligi agreguje typy wszystkich użytkowników, a potem łączy z członkami. Na syntetyce 1,4 mln typów: 248 ms → 2,9 ms (scope) i 619 ms → 7,2 ms (kupon) po dodaniu filtra członków. Dziś niewidoczne. | `AND p.user_id IN (SELECT user_id FROM private_league_members WHERE private_league_id=%s)` w obu CTE (wzorzec już jest w `badges.py`). | średnia (1 h) |
| 19 | `mundial-frontend/index.html`, `vercel.json` | Brak tytułu ligi w podglądzie `/join/KOD` (SPA). | Rewrite `/join/:code` w Vercelu do endpointu FastAPI, który zwraca `index.html` z podmienionymi `og:title`/`og:description` (i ewentualnie obrazkiem generowanym w Pillow). Bez Next.js. | średnia (M) |
| 20 | `routers/predictions.py:75-96`, `db/queries/predictions.py:114-129` | TOCTOU: sprawdzenie blokady i zapis typu w osobnych transakcjach. Typ może wejść w milisekundach po gwizdku. | Warunek w SQL (`INSERT … SELECT … WHERE m.status='scheduled' AND m.kickoff_at > now()`), brak wiersza = 409. | niska |
| 21 | `main.py:75-79` | Swagger, ReDoc i `openapi.json` publiczne na produkcji (pełna mapa API z adminem). | `docs_url=None, redoc_url=None, openapi_url=None` przy `ENV=prod`. | niska |
| 22 | `domain/crests.py:181-195`, `services/crest_cache.py:91-139` | `/img/crest`: SSRF zablokowany poprawnie, ale klucz cache zawiera query string i dysk nie ma limitu (`?x=N` = nowe pobranie i plik). Render Hobby ma 5 GB transferu wychodzącego miesięcznie, a po przekroczeniu bez karty usługi stają do końca miesiąca ([Render](https://render.com/docs/outbound-bandwidth)). | Odrzucać query i nietypowe ścieżki, limit plików. Docelowo herby jako statyczne pliki na Vercelu/R2. | niska–średnia |
| 23 | `schemas/models.py:11,41,183` | Nick i nazwa ligi: tylko długość. Przyjmuje znaki RTL-override i zero-width (PoC), unikalność nicku obchodzi się homoglifami. | `strip`, NFKC, dozwolony zestaw znaków, unikalność po `lower(nick)`. | niska |
| 24 | `routers/auth.py:138-152`, `279-287` | Enumeracja e-maili: rejestracja mówi, że e-mail istnieje; logowanie na nieistniejący e-mail odpowiada w 1,5 ms zamiast 106 ms (Argon2 tylko dla istniejących). | Hash-atrapa przy braku użytkownika. Przy przejściu na logowanie kodem: zawsze „sprawdź skrzynkę”. | niska |
| 25 | `domain/auth.py:5`, `pyproject.toml` | `python-jose` słabo utrzymywany (wersja 3.5.0 ma poprawki CVE-2024-33663/33664, aplikacja z HS256 i listą algorytmów nie jest podatna). | PyJWT (ok. 10 linii). | niska |
| 26 | `.github/workflows/deploy-backend.yml:38,42` | `curl` do deploy hooka bez `-f` (błąd deployu = zielony pipeline). Tag `latest` bez `concurrency` (starszy build może nadpisać nowszy). Vercel deployuje front bez czekania na CI i przed backendem. | `curl -fsS --retry 3`, deploy po digeście/SHA, `concurrency`, smoke test `/health/ready` po deployu. | niska–średnia |
| 27 | brak | Brak backupów: Neon Free ma 6 h historii i 1 ręczny snapshot. Błąd migracji wykryty po weekendzie = utrata danych. | Nocny `pg_dump` z GitHub Actions do Cloudflare R2 (10 GB za darmo), raz w miesiącu test odtworzenia. | **wysoka** |
| 28 | front (brak) | Regulamin football-data.org §7.1 wymaga tekstu „Football data provided by the Football-Data.org API”; nie ma go w aplikacji. | Stopka lub strona zasad. | niska (ryzyko utraty klucza) |
| 29 | brak polityki prywatności | Aplikacja zbiera maile znajomych, a nie ma polityki prywatności. Adresy e-mail trafiają do logów (`routers/auth.py:125,248`, `services/email.py:21,32`). | Krótka strona `/prywatnosc`. Logować `user_id` zamiast e-maila. | niska (etap 2: wysoka) |
| 30 | `services/email.py:35-37` | `FRONTEND_URL` służy i do CORS (lista po przecinku), i do linków w mailach. Przy kilku originach link w mailu jest zepsuty. | Osobna zmienna `PUBLIC_APP_URL`. | niska |
| 31 | `services/coupons.py:123-136,160-172` | W tygodniu bez meczów każdy `GET /me/coupon` przelicza od zera kandydatów i tabele (pusty kupon nie jest zapamiętywany). | Zapamiętać pusty wynik (wiersz z 0 meczów albo cache na godzinę). | niska |
| 32 | `services/providers/football_data.py` + `domain/live_points.py` | W dogrywce punkty „na żywo” liczone od wyniku z dogrywką, końcowe od wyniku po 90 min: tabela live „skacze” po gwizdku. | Dla `live` przy `duration != REGULAR` liczyć `regularTime`. | niska |
| 33 | `docs/ci-cd.md:11`, `docs/migrations.md`, ADR #008 | Dokumentacja nieaktualna: lint w CI blokuje, migracje 008–013 nieopisane w `migrations.md`, ADR #008 opisuje nginx, a produkcja to Vercel+Render. Kupon, joker i sync w procesie API bez ADR. | Aktualizacja przy okazji. | niska |
| 34 | gałęzie `origin/feat/front-listopad`, `origin/feat/feedback-listopad` | `feat/front-listopad` ma 1 commit (965fac4, 4.11, 93 pliki) na wierzchu `main`, możliwy fast-forward bez konfliktów. `feat/feedback-listopad` to 1 commit (b3bb55c, 3.11, 138 plików, w tym 31 backendowych) odgałęziony od 36126b7, sprzed merge’a backendu, i konfliktuje z `main`. Front na `main` nie woła `/coupon/global`, który backend na `main` już ma (obsługa jest tylko na `feedback-listopad`). Do tego kilkanaście martwych starych gałęzi. | Fast-forward `front-listopad` (5 min). Z `feedback-listopad` przenieść ręcznie tylko obsługę kuponu ogólnego na froncie (`api/coupon.js` i komponenty), **nie** mergować całej gałęzi, bo może nadpisać nowszą pracę. Martwe gałęzie usunąć. | średnia |

Co działa dobrze i nie wymaga zmian: punktacja w przypadkach brzegowych (dogrywka i karne liczone po 90 min, walkower i odwołanie unieważniają typy, korekta wyniku w oknie 24 h, joker z blokadą optymistyczną), obsługa czasu (ręczny DST dla Warszawy zgodny z `zoneinfo` w latach 2024–2030), autoryzacja w ligach (IDOR nie znaleziono), hasła w Argon2id, tokeny resetu jako SHA-256 z TTL 1 h, kod zaproszenia o przestrzeni 31^8, migracje w jednej transakcji z blokadą doradczą.

---

## 5. Kod i architektura

### 5.1 Ocena obecnego stanu

**Backend: dobry, lepszy niż autor sądzi.**
- Warstwy są przestrzegane: `domain/` to czyste funkcje z wstrzykiwanym czasem, SQL jako stałe z parametrami, `routers/` jako orkiestracja (ADR #001).
- Migracje: jedna transakcja na plik, `pg_advisory_xact_lock`, rollbacki, wzorzec expand→contract.
- Synchronizacja: blokada przez częściowy unikalny indeks, rate limiter z obsługą 429 i nagłówków, backoff, okno korekt 24 h, osobne kolumny na dogrywkę i karne (pułapka `fullTime` z football-data dobrze opisana w `docs/data-source.md`).
- Testy: 1223, wszystkie zielone. 964 jednostkowe (głównie czysta domena, wysoka wartość), 259 integracyjnych na prawdziwym Postgresie. Luka: testy API podmieniają `db.queries` (ok. 380 × `monkeypatch.setattr`), więc sprawdzają mapowanie HTTP, a nie SQL. Brakuje testów cyklu życia konta, regresji statusów meczu, auth na prawdziwej bazie i współbieżności. Stąd bugi #5 i #9 przeszły niezauważone.

**Co naprawdę jest „chaosem”:**
1. **Kombinatoryka produktu.** Ranking ma warianty: scope vs kupon, wszystkie sezony vs jeden, archiwum, `bonuses=true/false` tylko dla Mundialu, nakładka live, mnożnik jokera. Reguła „które mecze liczą się w lidze” jest skopiowana w 6+ zapytaniach (`SQL_LEAGUE_COUPON_RANKING`, `SQL_LIST_LEAGUE_LIVE_PREDICTIONS`, `SQL_LIST_LEAGUE_MEMBER_PREDICTIONS`, `SQL_LIST_LEAGUE_FINISHED_PICKS`, `SQL_LIST_LEAGUE_COUPON_UNIT_MATCHES`, `SQL_COUNT_TYPED_PER_MATCH`). Każda nowa funkcja dokłada kolejną kopię. To najważniejszy dług, i rośnie przez feature creep, nie przez styl kodu.
2. **Routery składają odpowiedzi z wielu zapytań** (`_coupon_response`, `routers/coupon.py:106-166`: ok. 9 zapytań, każde na osobnym połączeniu i w osobnej transakcji).
3. **Boilerplate DB:** 88 bloków `get_conn / try / finally release_conn`, 5 kopii `_fetch_all`, zapytania z 8–11 parametrami pozycyjnymi (kruche przy zmianach).
4. **Stary model Mundialu** (`/ranking`, `/bonus/*`, `/matches/bootstrap`, `leagues`, `scoring_rules`, `matches.stage`). Dług ograniczony i dobrze opisany. Tabela `scoring_rules` nie jest już nigdzie czytana. Migracja „contract” to 8–12 h.
5. **Historia:** gigantyczne commity („backend features added: coupon of the week, statistics…”: 31 plików, +1885 linii) i niezmergowane gałęzie. Kod jest dobry, ale historii nie da się czytać ani bezpiecznie cofać.
6. **Tożsamość drużyny per dostawca** (`teams (provider, external_id)` z migracji 005). Drugi dostawca dla Ekstraklasy zrobi z Legii w LM i Legii w Ekstraklasie dwa wiersze (zepsuje formę, H2H, rangi w kuponie, `team_pick`). Przed Ekstraklasą z API potrzebna tabela `team_provider_refs`.

**Frontend: porządny jak na kod z AI, ale autor go nie zna, a to ryzyko utrzymania.**
- Plusy: autozapis typów, polling zależny od widoczności karty, szkielety ładowania, tokeny kolorów w `tailwind.config.js`, czysty lint, testy e2e (na mockowanym API).
- Minusy: trzy różne sposoby pobierania danych bez cache (`useAsync`, ręczne efekty w `LeagueDetail.jsx:26-59`, `LeagueStandings.jsx:33-131`), brak lazy loadingu (576 kB JS w jednym chunku, razem z panelem admina), brak error boundary, ok. 110 komponentów, sporo dużych (`CouponRow` 308, `LeagueCoupon` 282, `LeagueStandings` 260, `Admin.jsx` 557 linii).

### 5.2 Opcje: ewolucja, refactor, rewrite

Szacunki dla jednej osoby przy 8–10 h tygodniowo.

| Opcja | Nakład | Kalendarz | Plusy | Minusy |
|---|---|---|---|---|
| **A. Ewolucja: FastAPI + React + PWA, celowane poprawki** | 30–50 h backend + 15–25 h porządków frontu | 6–8 tygodni, równolegle z funkcjami adopcji | Naprawia to, co realnie boli (sesja, pula, bugi, hosting). 1223 testy zostają. Od razu widać efekt dla graczy. | Front dalej w technologii, której autor nie zna (do nadrobienia: 10–15 h nauki Reacta i TanStack Query). |
| B. Refactor „frameworkowy”: SQLAlchemy/SQLModel, async, Alembic | 60–100 h | 2–3 miesiące | Ładniej wygląda w CV. | Przepisanie ok. 90 zapytań i testów integracyjnych dla estetyki. Async nic nie da przy kilkudziesięciu graczach, własny runner migracji działa. **Nie warto.** Wyjątki warte zrobienia: `psycopg_pool` (4–6 h), PyJWT (2 h). |
| C. Rewrite backendu w Go | 250–350 h | 7–10 miesięcy | Jedna binarka, mało RAM-u, język, który autor lubi. | Pół roku bez zmian dla graczy, ryzyko regresji w punktacji i syncu. Problem „nikt nie używa” zostaje. |
| D. Next.js full-stack (TS) | 350–500 h | 9–12+ miesięcy | SSR og-tagów dla `/join/KOD`. | Najgorsze dopasowanie: autor nie zna Reacta ani TS, a logikę domeny trzeba przepisać. SSR og-tagów da się zrobić endpointem FastAPI w 1 wieczór. |
| E. Supabase / PocketBase (BaaS) | tylko Auth: 20–30 h; pełny BaaS: 200–300 h | 3 tygodnie – 7 miesięcy | Gotowe logowanie Google, magic link, maile. | Dwa systemy auth do pogodzenia. Supabase Free pauzuje projekt po tygodniu bez aktywności. Sync i kupony nie pasują do RLS i edge functions. PocketBase to rewrite. |
| F. Front na HTMX + Jinja (FastAPI) | 120–180 h | 4–6 miesięcy | Autor rozumie każdą linijkę, SSR i og-tagi za darmo. | Interaktywny kupon, live i reakcje to dalej JS (Alpine). Przepisanie e2e. Miesiące bez nowych funkcji, gdy problemem jest brak użytkowników. |
| G. Front we Flutterze (Web lub natywnie) | 150–250 h (+99 USD/rok za Apple) | 5–8 miesięcy | Język, który autor zna. Natywny push. | Flutter Web: ok. 1,5 MB samego renderera CanvasKit ([flutter.dev](https://flutter.dev/blog/best-practices-for-optimizing-flutter-web-loading-speed)), najgorszy wybór dla strony otwieranej pierwszy raz z linku w webview Messengera. Natywnie: dwa klienty albo sklep jako dodatkowy krok dla każdego nowego gracza. |

**Rekomendacja: A, z wąskimi elementami B.** Backend zostaje w FastAPI z czystym SQL. Front zostaje w React, ale przy okazji zmian ujednolicony: TanStack Query jako jedyny sposób pobierania danych, `React.lazy` dla tras (szczególnie `/admin`), `ErrorBoundary`, mała biblioteka 10–12 komponentów pod przyszły wygląd. Do F wrócić najwcześniej za rok, jeśli front okaże się nieutrzymywalny.

### 5.3 Kroki refaktoru w kolejności

| # | Krok | Nakład |
|---|---|---|
| R1 | Sesja przesuwana, PyJWT, `SameSite=Lax`, `password_changed_at` (bugi #2, #8, #17, #25) | S (4–6 h) |
| R2 | Pula połączeń: `minconn=maxconn`, `keepalives`, timeouty (#6) | S (1–2 h) |
| R3 | Usuwanie konta właściciela ligi + test (#5) | S (2–3 h) |
| R4 | Filtr członków w rankingu (#18) | S (1–2 h) |
| R5 | `matches.locked_at` + warunkowy zapis typu (#9, #20) | M (4–6 h) |
| R6 | Zewnętrzny tick, `/health/live`, backup, Sentry (#1, #27; rozdz. 8) | M (6–10 h) |
| R7 | Decyzja o gałęziach, merge, usunięcie martwych (#34) | S–M |
| R8 | Migracja contract starego Mundialu | M (8–12 h) |
| R9 | Jedna definicja „meczów liczonych w lidze” (funkcja/widok SQL), `services/coupon_view.py`, jedna transakcja na request, nazwane parametry SQL, podział `schemas/models.py` | M (12–20 h, przyrostowo) |
| R10 | Front: TanStack Query, lazy routes, ErrorBoundary (przy okazji zmian ekranów) | M (15–25 h) |
| R11 | Jeden test e2e na prawdziwym backendzie (docker compose: rejestracja → liga → typ → wynik → punkty) | S–M |
| R12 | `team_provider_refs` i drugi dostawca (dopiero gdy Ekstraklasa z API będzie uzasadniona) | L (20–30 h) |

R1–R4 to ok. 10–13 h i dają największy zwrot. Mniejsze commity: jeden temat na commit, żeby historia znowu była czytelna.

---

## 6. Wygląd i UX

### 6.1 Ocena obecnego wyglądu

Obejrzałem aplikację lokalnie (na mockowanym API, 390 px i 1280 px) i zrzuty z `docs/screenshots/`. Szczerze: **to generyczny ciemny dashboard** w stylu Tailwind/shadcn z lat 2024–26. Granatowe tło #0B0E14, turkus, Inter, szklane karty z gradientem, `rounded-xl` wszędzie, wielkie liczby w kartach statystyk, uppercase’owe nagłówki. Jest spójny (tokeny w `tailwind.config.js:7-30`), ale **bezosobowy**: nic nie mówi „piłka”, „kumple” ani „nos do wyniku”. Ekrany to stosy kart o równej wadze, więc nic nie jest najważniejsze. Teksty tłumaczące model („Widok łączny sumuje punkty z meczów aktywnych sezonów w zakresie ligi oraz…”) to objaw tego, że model jest za skomplikowany. Logo z gradientem turkus→czerwień nie pasuje do reszty palety.

Problemy UX ważniejsze niż estetyka:
- Start pokazuje „Hity tygodnia”, liga pokazuje „Kupon tygodnia”: gracz nie wie, co się liczy.
- Wyniki poprzedniego tygodnia schowane za strzałką od poniedziałku.
- Na telefonie przycisk „Zarejestruj się” chowa się pod klawiaturą, link do logowania występuje dwa razy.
- Pola wyniku 32×36 px i systemowa klawiatura zasłaniająca pół kuponu.
- Kontrast szarego tekstu poniżej WCAG AA.

### 6.2 Kolejność: najpierw użyteczność, potem nowy wygląd

Autor 4.11 sam zaczął zmieniać wygląd (`feat/front-listopad`: nowe „hero” na Starcie, panel rozgrywek w Meczach, linie zamiast pudełek, mniejsze promienie, nowy font logo, turkus zostaje). To dobry kierunek „mniej dashboardu” i nie trzeba go wyrzucać. Kolejność:
1. **Teraz (S–M, React):** poprawki użyteczności, niezależne od stylu: pola wyniku min. 44×44 px, kontrast szarego tekstu, jeden kupon zamiast „Hitów” i „Kuponu tygodnia”, wyniki poprzedniego tygodnia widoczne w poniedziałek, przycisk rejestracji nad klawiaturą.
2. **Luty–marzec 2027, opcjonalnie:** nowa tożsamość wizualna opisana niżej. To propozycja do rozważenia, a nie obowiązek. Jasny motyw, nowe fonty i własna klawiatura dotykają większości komponentów (np. 133× `text-gray-500`), więc to M–L, a nie „tokeny i fonty”. Ma sens dopiero, gdy liga gra, i najlepiej razem z przejściem na TanStack Query.

### 6.3 Propozycja kierunku wizualnego: „czutka – nos do wyniku”

**Idea:** czutka to przeczucie, z brzucha, a nie z arkusza. Aplikacja ma przypominać **kartkę z typami przyklejoną na lodówce w mieszkaniu studenckim** i rozmowę przy piwie, a nie terminal bukmacherski ani panel analityczny. Ciepła, papierowa, z jednym „gorącym” kolorem. Wyraźnie inna niż ciemne aplikacje bukmacherów, co wzmacnia pozycjonowanie „bez bukmachera”.

**Paleta** (jasny motyw domyślny, ciemny jako „mecz wieczorem”):

| Token | Hex | Zastosowanie |
|---|---|---|
| `paper` | #F3EEE3 | tło |
| `card` | #FFFCF5 | karty, kupon |
| `ink` | #17150F | tekst, ramki 1,5 px, główne przyciski |
| `ink-muted` | #6B6457 | tekst pomocniczy (5,6:1 na `paper`) |
| `czutka` | #FF5A1F | **jedyny** kolor akcji i marki: „Typuj”, aktywne pole, live |
| `pitch` | #0F6E3D | dokładny wynik, „zapisane” |
| `pitch-soft` | #CFE6D3 | tło trafionej różnicy lub zwycięzcy |
| `miss` | #B9B2A4 | pudło (szarość, nie czerwień: pudło to nie błąd) |
| `gold` | #F2B705 | joker („Pewniak”), lider, odznaki |
| `night` / `night-card` | #14130F / #1F1D18 | ciemny motyw (tekst #F3EEE3) |

**Typografia** (Google Fonts z latin-ext): **Bricolage Grotesque** 700/800 (nagłówki, nazwy lig, werdykty), **Instrument Sans** 400/600 (UI), **Big Shoulders Display** 800 *wyłącznie do cyfr* wyników i punktów (tablica na stadionie). Opcjonalnie Caveat do 1–2 „odręcznych” dopisków.

**Komponenty i interakcje:**
- Kupon jako jedna kartka z perforowanym brzegiem i nagłówkiem „Kupon #45 · zamyka się pt 20:30”. Duże pola 48×56 z cyframi w Big Shoulders. **Własna klawiatura 0–9 przyklejona do dołu ekranu**, która po drugiej cyfrze przechodzi do następnego meczu (jak w Superbru). Systemowa klawiatura nie zasłania wtedy kuponu.
- Po zapisie mała pieczątka ✓ zamiast ptaszka. Pełny kupon: krótka animacja i seria „🔥 3 tygodnie z rzędu”.
- „Pewniak” zamiast „Joker ×2”: złota naklejka stukana na jeden mecz.
- **Twarze zamiast tabelek:** stos awatarów przy meczu („Ola, Kuba i 2 inne mają 2:1”).
- Tabela ligi jako tablica: pozycja, awatar, nick, punkty, strzałka. Szczegóły (dokładne, różnice) dopiero po tapnięciu.
- Ikony: jeden zestaw (Phosphor).
- Stempel „CZUTKA!” za trafiony dokładny wynik w podsumowaniu. Wszystko wyłączone przy `prefers-reduced-motion`.

**Ton:** krótki, kumpelski, z lekką ironią, bez regulaminu w interfejsie. „Kupon zamyka się za 3 h. Brakuje Ci 4 meczów.” · „Nos Cię dziś zawiódł: 2 pkt.” · „Ola ma lepszego nosa. Na razie.” · „Tylko Ty trafiłeś 3:1. Czutka tygodnia.”

### 6.4 Ekrany do przeprojektowania

**Nawigacja: 3 zakładki zamiast 5 – Kupon · Liga · Ja.** „Mecze” (wszystkie mecze świata) i ranking globalny schowane, statystyki w „Ja”.

1. **Zaproszenie `/join/KOD`.** Dziś ekran rejestracji już pokazuje zapraszającego, ligę, liczbę graczy i rozgrywki (`InviteNotice.jsx`). Do dodania: awatary członków, „ten tydzień: 10 meczów, zamyka się pt 20:30”, a po wdrożeniu logowania kodem z maila jedno pole e-mail + nick zamiast hasła. W webview Messengera dyskretny pasek „Otwórz w przeglądarce, żeby zostać zalogowanym”. Wariant ambitny (później): 3 mecze do wytypowania przed założeniem konta, trzymane lokalnie.
2. **Kupon jako ekran domowy.** Licznik do zamknięcia, pasek 7/10, seria. Mecze pogrupowane po dniach. Gracz w kilku ligach ma **jeden kupon** z etykietami lig przy meczach. Usunąć: rozróżnienie „Hity tygodnia” / „Kupon tygodnia”, karty „Twoje sezony” i „Ostatnie wyniki” (idą do Werdyktu), „Załóż ligę” u kogoś, kto ma ligę.
3. **Mecz (live / po gwizdku) jako arkusz od dołu:** wynik, „gdyby się teraz skończyło: +3”, typy znajomych jako awatary pogrupowane po wyniku, reakcje. Kontekst przed meczem zwinięty do jednej linii formy.
4. **Liga:** tablica, „kto jeszcze nie wytypował” z przyciskiem **„Szturchnij na grupę”** (dla każdego członka, nie tylko organizatora), ostatni Werdykt, pytania bonusowe tylko jeśli istnieją. Kod, zakres, ustawienia i wyjście z ligi w arkuszu „⋯”.
5. **Werdykt tygodnia (nowy, poniedziałek):** pełnoekranowa „okładka”: „Kolejka 11: Kuba wygrywa tydzień (+18)”, czutka tygodnia (jedyny trafiony dokładny wynik), pudło tygodnia, Twój awans lub spadek, przycisk „Wrzuć na grupę” (obrazek z `weekImage.js` w nowej szacie). To treść, którą ludzie przeklejają na Messengera, i zarazem główny powód powrotu.
6. **Landing:** jeden ekran, hasło („Masz czutkę? Pokaż.”), żywy przykład kuponu (już jest), „Załóż ligę w 30 s”.

**Jak to wdrażać po godzinach:** nie robić „wielkiego redesignu”. Werdykt najpierw jako treść maila poniedziałkowego (Python), a ekran dopiero później. Kupon i Werdykt to dwa ekrany, które gracz widzi co tydzień, więc od nich zaczynać. Pełna wersja z nowym kierunkiem to łącznie 60–90 h w React, rozłożone na luty–czerwiec, **po** sprawdzeniu, że liga gra.

### 6.5 Web, PWA czy natywna aplikacja

| Opcja | Koszt | Za | Przeciw |
|---|---|---|---|
| **Web + PWA (rekomendacja)** | 0 zł, Web Push 10–15 h | Link z Messengera otwiera się od razu. Jeden klient. Push na Androidzie bez instalacji, na iOS po dodaniu do ekranu głównego. PWA w UE działają normalnie (Apple wycofało się z ich wyłączenia w 2024, [TechCrunch](https://techcrunch.com/2024/03/01/apple-reverses-decision-about-blocking-web-apps-on-iphones-in-the-eu/)). | Push na iPhonie tylko po „Dodaj do ekranu” ([WebKit](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)); w webview Messengera tej opcji nie ma. |
| Flutter natywny (iOS + Android) | 150–250 h + 99 USD/rok (Apple) + 25 USD (Google) | Natywny push, „prawdziwa apka”. | Sklep jako dodatkowy krok dla każdego zaproszonego znajomego. Nowe osobiste konta Google Play muszą przejść test zamknięty z 12 testerami przez 14 dni. Budżet ≠ 0 zł. Dwa klienty do utrzymania, jeśli web zostaje dla zaproszeń. |
| Capacitor (opakowanie obecnego Reacta) | 20–40 h + te same opłaty | Push natywny bez przepisywania. | Te same sklepy i opłaty. Sens dopiero, gdy push na iOS okaże się realnym ograniczeniem. |
| Flutter Web | 150–250 h | Znany język. | ~1,5 MB renderera przed pierwszym pikselem, słaba dostępność, brak HTML pod podgląd linku. Odradzam. |

**Rekomendacja: web + PWA, bez natywnej aplikacji teraz.** Najkrócej: link z Messengera zawsze otworzy się w przeglądarce, a sklep z aplikacjami to dodatkowy krok i koszt. Mail jako główny kanał przypomnień, Web Push jako dodatek (prośba o zgodę dopiero po drugim pełnym kuponie, z instrukcją „Dodaj do ekranu” dla iPhone’a). Do natywnej aplikacji (Capacitor albo Flutter jako jedyny klient mobilny) wrócić, gdy będzie 50+ aktywnych graczy i dane pokażą, że brak pusha na iOS kosztuje retencję. Wtedy też koszt 99 USD/rok ma uzasadnienie.

---

## 7. Funkcje

### 7.1 Upraszczanie (najpierw zabrać, potem dodać)

| Co | Decyzja | Nakład |
|---|---|---|
| „Obserwuj rozgrywki” (`FollowButton`, krok w `/witaj`, `Competitions`) | Usunąć jako pojęcie. Gracz typuje to, co jest w jego ligach, a bez ligi kupon ogólny. Migracja 012 i tak synchronizuje obserwowanie z zakresem ligi. | S–M |
| Tryb rankingu `scope` | Ukryć dla nowych lig, zostaje tylko „kupon”. Wtedy joker działa zawsze. Rozmiar kuponu i automat do „zaawansowanych”. | S |
| Kupon ogólny vs ligowy | Domknąć po decyzji o gałęziach: dla gracza jeden kupon z etykietami lig. | S–M |
| Ranking globalny, stary `/bonus` | Ukryć, migracja contract. | M |
| Kontekst meczu | Zostawić tabelę i formę. Usunąć BTTS, over 2,5, czyste konta (język bukmacherski). H2H tylko, gdy są dane. „Karta-fiszka” z `do-zrobienia.md` odłożona. | S |
| „Na żywo” | Podpis „wynik z kilkuminutowym opóźnieniem” (darmowy football-data nie ma live). | S |
| Bonusy | `champion` zostaje, `team_pick` w zaawansowanych. | S |
| Odznaki, serie, reakcje, statystyki | Zamrozić, nie rozwijać. | — |

### 7.2 Lista funkcji z oceną

Wpływ na adopcję wśród znajomych: wysoki / średni / niski.

| Funkcja | Stan | Uzasadnienie | Wpływ | Nakład | Priorytet |
|---|---|---|---|---|---|
| Przypomnienie mailem w piątek (wtorkowe przy LM jako P1) | brak | jedyna rzecz, która sama przywołuje gracza; logika braków per gracz jest w `db/queries/coupon.py` | **wysoki** | M (Python) | **P0** |
| Poniedziałkowe podsumowanie mailem (Werdykt na Starcie później) | brak | moment, na który się czeka; ten sam mechanizm co przypomnienia | **wysoki** | S–M (Python) | P1, tydzień +1 |
| Długa sesja, działające maile, pełny og:image | brak | bez tego wszystko inne przecieka | **wysoki** | S | **P0** |
| Szybsza ścieżka z linku: „Budzę serwer…”, bez 1,5 s, bez „powtórz hasło” (P0); baner webview i awatary członków (P1) | częściowo | pierwsze 2 minuty | **wysoki** | S (P0) + S–M (React) | **P0**/P1 |
| „Szturchnij resztę” z imionami, dla każdego członka (zmiana warunku w `LeagueCouponProgress` i `routers/coupon.py:158`) | ręczne, tylko organizator | gospodarz nie zawsze pamięta | średni | S | P1 |
| Pomiar: zapytania A–F (P0), `last_seen_at`, `events`, Umami (P1) | brak | bez tego nie wiadomo, co działa | pośrednio krytyczny | S (Python) | **P0**/P1 |
| Logowanie kodem z maila / magic link (rejestracja: nick + e-mail, bez hasła) | brak | usuwa hasło i problem odzyskiwania; link z maila otwiera się w zwykłej przeglądarce, co przy okazji „wyciąga” gracza z webview | średni–wysoki | M (Python + React) | P1 (od razu, jeśli 25.11 aktywacja słaba) |
| Logowanie Google | brak | Google blokuje OAuth w przeglądarkach wbudowanych (błąd `disallowed_useragent`), czyli w głównym scenariuszu z Messengera | średni | M | P2 |
| Rundy ligi (reset rankingu co 6–8 tyg.) i ogłoszenie zwycięzcy | brak | lekarstwo na „odpuszczam, bo jestem daleko” | średni–wysoki | M | P1 |
| Ręczne mecze (Polska w LN, Ekstraklasa, hity) | brak | pusty kupon w przerwie reprezentacyjnej; lokalny koloryt za 0 zł | średni–wysoki | M | P1 |
| Kalendarz `.ics` z terminami kuponu | brak | na iPhonie działa bez PWA, FPL robi podobnie | średni | S–M | P1 |
| Web Push | brak | dla Androida i zainstalowanych PWA | średni | M–L | P2 |
| Czutkobot (bot w każdej lidze) | brak | punkt odniesienia i materiał na żarty, tani w Pythonie | średni | S–M | P2 |
| Pojedynki tygodnia H2H | brak | „mam rywala w tej kolejce” | średni | M | P2 |
| Bonus za niespodziankę (punkty za typ, który miało mniej osób w lidze) | brak | odwaga, szansa na odrobienie strat, bez kursów bukmacherskich | średni | M | P3 |
| Podsumowanie sezonu („Wrapped”) | odznaki są | viral raz w sezonie, PNG jak `weekImage.js` | średni | M | P2 (maj 2027) |
| Ekstraklasa z API | brak | najczęstsza prośba w PL; kicktipp.pl ją ma | średni–wysoki | L + 9–19 USD/mies. | P3 (najpierw ręcznie) |
| Liga Narodów / eliminacje z API | brak | wypełnia przerwy | średni | M po providerze | P3 |
| Tie-breaker „minuta pierwszego gola” | brak | emocje w kuponie | niski | M | P3 |
| Share do WhatsAppa/Messengera (`wa.me`, przyciski na desktopie) | `navigator.share` jest | drobne usprawnienie | średni | S | P1 |
| Czat / komentarze | brak | rozmowa i tak jest na Messengerze (słuszna decyzja autora) | niski | M–L | nie robić |
| Liga publiczna dla obcych | brak | przy zerze graczy pusta | niski | S–M | nie teraz |
| Bot Messengera / WhatsApp API | brak | review Meta, płatne API | niski | L | nie robić |
| Natywna aplikacja | brak | patrz 6.5 | niski teraz | L | nie teraz |
| Eksport CSV, panel organizacji, branding | brak | etap 2 | niski (B2C) | S–L | etap 2 |

---

## 8. Bezpieczeństwo, DevOps, infrastruktura i dane meczowe

### 8.1 Bezpieczeństwo

Najważniejsze pozycje są w tabeli w rozdziale 4 (#7, #8, #17, #21–#25, #29). Podsumowanie:
- **Do zrobienia od razu (1 wieczór):** `SameSite=Lax`, sesja przesuwana z `password_changed_at`, limit logowania per e-mail, ukrycie Swaggera na produkcji, nagłówki bezpieczeństwa w `vercel.json` (`X-Content-Type-Options`, `Referrer-Policy`, `frame-ancestors 'none'`, prosta CSP).
- **Dobrze zrobione:** autoryzacja w ligach (sprawdzone `_require_member`, `_require_manager`, przynależność pytań bonusowych do ligi, `users_share_league` w typach innego gracza), Argon2id, tokeny resetu jako hash, SSRF w proxy herbów zablokowany, emoji z listy dozwolonych.
- **Na etap 2:** polityka prywatności, maskowanie e-maili w logach, role w bazie zamiast `ADMIN_EMAILS`.

### 8.2 CI/CD i monitoring

1. `deploy-backend.yml`: `curl -fsS --retry 3`, deploy po SHA zamiast `latest`, `concurrency`, smoke test `/health/ready` i `/version` po deployu.
2. Vercel: front deployowany z workflowa **po** backendzie (wyłączyć auto-deploy z `main`), preview na PR zostają.
3. `dependabot.yml` (uv, npm, github-actions, docker), akcje przypięte do SHA, `pip-audit` / `npm audit` jako ostrzeżenie.
4. Dockerfile: przypięty `uv`, multi-stage, `USER` inny niż root, `HEALTHCHECK`.
5. Backup: workflow `backup.yml` (cron nocny) → `pg_dump -Fc` → szyfrowanie `age` → Cloudflare R2 (10 GB za darmo) → ping do healthchecks.io. Raz w miesiącu test odtworzenia.
6. Monitoring: Sentry Free (backend + front, `send_default_pii=False`), healthchecks.io jako „dead man’s switch” dla ticka synchronizacji i backupu, UptimeRobot na `/health/live`.
7. Uwaga: w publicznym repo GitHub wyłącza zaplanowane workflowy po 60 dniach bez commitów, więc backup przez Actions potrzebuje monitoringu (healthchecks.io) albo drugiego miejsca uruchamiania (homelab).

Nakład: ok. 1–2 wieczory na całość.

### 8.3 Infrastruktura: 0 zł vs homelab

Aktualne limity (sprawdzone w dokumentacji dostawców, listopad 2026):
- **Neon Free:** 100 CU-h na projekt miesięcznie, 1 GB, usypianie po 5 min bezczynności (nie da się wyłączyć), 6 h historii, 1 snapshot. Po przekroczeniu compute wstrzymany do końca okresu ([FAQ](https://neon.com/faqs/free-plan-limits-and-quotas)).
- **Render Free/Hobby:** usypia po 15 min, wybudzenie ok. 1 min, 750 h/mies. na workspace (jedna stale włączona usługa to 744 h w 31-dniowym miesiącu, więc druga usługa w tym samym workspace przekroczy limit), efemeryczny dysk, **5 GB transferu wychodzącego miesięcznie**, a po przekroczeniu bez karty usługi stają do końca miesiąca ([Render free](https://render.com/docs/free), [bandwidth](https://render.com/docs/outbound-bandwidth)).
- **Vercel Hobby:** tylko użytek niekomercyjny ([Vercel](https://vercel.com/docs/limits/fair-use-guidelines)). Na etap 2 trzeba zmienić hosting frontu (Cloudflare Pages pozwala na komercję).
- **Cloudflare:** Workers Free z Cron Triggers, Pages, Tunnel i R2 (10 GB) za darmo.
- **Resend Free:** 3000 maili/mies., 100/dzień, wymaga własnej domeny.
- **Oracle Always Free:** darmowy VM ARM bez usypiania, ale z ryzykiem odebrania „bezczynnej” instancji i zmian limitów bez zapowiedzi (według [InfoQ, 07.2026](https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/) limity ARM zostały w 2026 obcięte; do sprawdzenia przed decyzją). Fly.io i Railway nie mają już prawdziwego darmowego planu.

| Kryterium | A: obecny stack naprawiony (Vercel + Render + Neon + Cloudflare) | B: Oracle Free VM + Docker Compose + Tunnel | Homelab (Compose + Cloudflare Tunnel) |
|---|---|---|---|
| Koszt | 0 zł | 0 zł | prąd ok. 10–30 zł/mies. (sprzęt planowany i tak) |
| Zimny start | brak (keep-alive na `/health/live`), Neon budzi się w ok. 0,5–1 s | brak | brak |
| Główne ryzyko | limity CU-h i transferu, zmiany cenników | odebranie instancji/konta | prąd, łącze, dysk, wyjazd autora; CGNAT rozwiązuje Tunnel |
| Backup | Actions → R2 | cron → R2 | cron → R2/B2 **poza domem** (obowiązkowo) |
| Monitoring | healthchecks.io + UptimeRobot + Sentry | Uptime Kuma + zewnętrzny monitor | Uptime Kuma **plus** zewnętrzny monitor (Kuma w domu nie zgłosi awarii domu) |
| Czas autora | najmniej (1–2 wieczory) | średnio | najwięcej, ale to też nauka do pracy |
| Etap 2 (B2B) | Vercel Hobby zabrania komercji | brak SLA | brak SLA, IP domowe, trudne RODO |

**Rekomendacja:**
- **Teraz: wariant A.** Krok 1 (2 h, Python): scheduler decyduje z pamięci, czy coś jest należne, i dotyka bazy tylko wtedy; `/health/live` bez bazy dla keep-alive. Render nie śpi, a Neon może zasypiać poza okresami synchronizacji. Zgrubny szacunek: kilkadziesiąt CU-h miesięcznie zamiast ok. 186 (zależy od liczby meczów i ruchu; sprawdzić w Usage po tygodniu). Krok 2 (później, 4–6 h): synchronizacja i przypomnienia przez `POST /internal/tick` z sekretem, wołany co 5 min z Cloudflare Worker Cron, żeby nie zależeć od keep-alive. Do tego nocny backup do R2, Resend na `czutka.uk`, Sentry.
- **Homelab równolegle jako staging i odbiorca backupów:** codzienne `pg_restore` ostatniego dumpu do lokalnego Postgresa to przy okazji test odtwarzania. Produkcję przenieść na homelab dopiero po miesiącu z ponad 99% dostępności mierzonej z zewnątrz. Dla aplikacji znajomych kilka godzin przerwy po awarii prądu jest do przyjęcia, utrata danych nie jest. Bezpośredni port 8000 nie może być wystawiony na świat (`docker-compose.yml:40` dziś wystawia go na `0.0.0.0`).
- **Etap 2:** mały płatny VPS w UE (Hetzner/OVH, ok. 20–25 zł/mies.) albo Cloud Run, Postgres z PITR co najmniej 7 dni, front poza Vercel Hobby. Homelab nie nadaje się dla klientów firmowych.

### 8.4 Dane meczowe

| Źródło | Pokrycie | Limity darmowe | Ryzyko | Ocena |
|---|---|---|---|---|
| **football-data.org** (obecne) | LM, top 5, Mundial/Euro i inne; **bez Ekstraklasy i LN** | 10 zapytań/min, wyniki z opóźnieniem (bez live) | wymaga atrybucji (§7.1), brak gwarancji; o użyciu komercyjnym regulamin milczy, trzeba zapytać pisemnie | zostaje jako główne. Live score 12 €/mies., strzelcy 29 €/mies. ([cennik](https://www.football-data.org/pricing)) |
| API-Football | wszystko, w tym Ekstraklasa i LN | 100 zapytań/dzień; dostęp do bieżącego sezonu na darmowym planie niepotwierdzony (sprawdzić jednym zapytaniem z kluczem) | płatny od ok. 19 USD/mies. | plan B płatny |
| TheSportsDB | Ekstraklasa jest | darmowy klucz mocno obcięty | premium 9 USD/mies. | najtańsza płatna opcja dla Ekstraklasy |
| ESPN (nieoficjalne) | LN zwykle tak, Ekstraklasa zwraca błąd | nieudokumentowane | może zniknąć w każdej chwili | tylko do porównania wyników |
| FotMob / SofaScore (scraping) | wszystko | — | regulamin FotMob wprost zakazuje ([ToS](https://www.fotmob.com/tos.txt)) | **nie** |

**Wniosek:** legalnego, darmowego i kompletnego źródła dla Ekstraklasy i Ligi Narodów nie ma. Potwierdza to ustalenia autora z `docs/data-source.md`.

**Strategia:**
1. **`ManualProvider`** (interfejs w `services/providers/base.py` i rejestr już są): rozgrywka z `provider='manual'`, terminarz importowany z CSV raz na rundę, wynik wpisuje admin (endpoint `POST /matches/{id}/result` już jest), później zaufany organizator ligi. Okno korekt 24 h już działa. Koszt: M, 0 zł. To od razu rozwiązuje mecze Polski w przerwach i Ekstraklasę na hitowe kolejki.
2. **Wykrywanie anomalii** jako czyste funkcje w `domain/sync_plan.py`: ponad 10 goli, zmiana wyniku po rozliczeniu, mecz `live` dłużej niż 3,5 h, `scheduled` z godziną sprzed ponad 3 h, przesunięcie o ponad 48 h. Każda anomalia trafia do `sync_runs.error` i do maila dla admina.
3. **Alert przy padnięciu synchronizacji** (healthchecks.io) i przy korekcie wyniku po 24 h (dziś tylko log).
4. **Atrybucja football-data w stopce** i mail do football-data z pytaniem o użycie komercyjne przed etapem 2.
5. **Płatny dostawca dla Ekstraklasy** dopiero, gdy ręczne wpisy okażą się popularne. Wcześniej `team_provider_refs` (R12), żeby Legia z dwóch źródeł była jedną drużyną.

---

## 9. Etap 2: produkt komercyjny i monetyzacja

### 9.1 Ocena planu autora

Dokumenty `analiza-biznesowa.md`, `monetyzacja.md` i `walidacja-b2b.md` są dobre: oddzielają fakty od szacunków, mają z góry spisane kryteria porzucenia i scenariusz rozmów w duchu „Mom Test”, trafnie stwierdzają, że w B2C nie da się zarobić. Problemy:
1. **Walidacja B2B (20 rozmów, landing) zaplanowana równolegle z etapem 1.** Przy 4/5 etatu i studiach to zjada czas na retencję. Autor sam zapisał w `monetyzacja.md`, że nie buduje płatności przed retencją, a harmonogram w `analiza-biznesowa.md` tej zasady nie przestrzega.
2. **Pilotaż w lutym 2027** wymaga organizacji, brandingu, importu maili, działów i wersji angielskiej. To ok. 4×M + L, czyli 2–3 miesiące wieczorów kosztem przypomnień.
3. Dokumenty zakładają zespół dwuosobowy. W historii commitów drugi autor ma 1 commit z czerwca.
4. Szacunek 10–60 tys. zł na turniej jest optymistyczny. Realniej 0–15 tys. zł na Euro 2028 przy jednej osobie i bez wcześniejszych klientów.
5. Kryterium „≥ 40% typuje co tydzień” jest niemierzalne bez analityki.

**Werdykt:** B2B ma sens, ale jako etap 2, po udowodnieniu retencji wśród znajomych. Realne okno sprzedaży to Euro 2028 (luty–maj 2028). Teraz jedynie 5 nieformalnych rozmów ze znajomymi z korporacji (30 minut każda), bez budowania.

### 9.2 Co trzeba będzie zbudować

| Obszar | Zakres | Nakład |
|---|---|---|
| Organizacje (multi-tenancy) | `organizations`, `organization_members(role)`, `organization_id` w lidze, filtrowanie | M–L |
| Role w bazie | superadmin, admin organizacji, admin ligi, gracz (zamiast `ADMIN_EMAILS`, ADR #005) | M |
| Panel admina organizacji | członkowie, działy, eksport CSV, kupon turnieju | L (głównie front) |
| Branding | logo i kolor przez tokeny | M |
| Dołączanie z domeny firmowej, import maili | wymaga działających maili; limit Resend Free 100/dzień → Resend Pro albo wysyłka rozłożona | M |
| Ranking działów | średnia na aktywnego gracza (jak Office World Cup) | M |
| SSO | Google Workspace / Microsoft Entra przez authlib; na pilotaż wystarczy kod z maila z domeną firmy | M + M |
| Wersja angielska | ok. 110 komponentów i teksty backendu | **L** (największy koszt) |
| Niezawodność | VPS, osobny proces sync, backupy, Sentry, live score | M + 12 €/mies. |
| Płatności | najpierw faktura i przelew; Stripe/Przelewy24 dopiero przy samoobsłudze | M |
| Alternatywa | bot Slack/Teams na wzór Office World Cup zamiast pełnego panelu HR | M–L |

### 9.3 Minimum prawne (to nie porada prawna, do potwierdzenia u księgowego lub prawnika)

- **Działalność nierejestrowana 2026:** limit **10 813,50 zł przychodu na kwartał** (225% płacy minimalnej), po przekroczeniu 7 dni na wpis do CEIDG ([money.pl](https://direct.money.pl/artykuly/porady/dzialalnosc-nierejestrowana-2026-limit-10-813,50-zl,-po-przekroczeniu-7-dni-na-ceidg)). Kilka firm na pilotaż się mieści. Działy zakupów korporacji mogą wymagać NIP i faktury VAT, czyli JDG. Sprawdzić też zakaz konkurencji w umowie stażowej.
- **Hazard:** bez wpłat od graczy to nie zakład wzajemny. Nagrody od firmy jako konkurs z regulaminem (art. 919–921 KC), bez losowania ([SMMLegal24](https://smmlegal24.pl/polska-gola-kilka-slow-o-legalnym-typowaniu-wynikow-meczow/)). Nagroda od pracodawcy to przychód pracownika.
- **RODO:** polityka prywatności już teraz. W B2B czutka jest podmiotem przetwarzającym: umowa powierzenia (art. 28), rejestr kategorii czynności (art. 30 ust. 2), procedura naruszeń (72 h), usuwanie danych po turnieju, hosting w UE.
- **Regulamin usługi:** osobno B2C i B2B. Szablon regulaminu konkursu dla klienta.
- **Dane i znaki towarowe:** pisemna zgoda football-data na użycie komercyjne (regulamin milczy, wymaga atrybucji i zgód na logo, §9.2). Tryb bez herbów i logo UEFA w produkcie płatnym i w marketingu (słowne nazwy turniejów, nie „EURO 2028” jako znak).
- **Hosting:** Vercel Hobby zabrania użytku komercyjnego.

### 9.4 Model cenowy

Ceny konkurencji (zweryfikowane): Scorecast Business 290 € netto za 100 graczy + 2 € za kolejnego, Enterprise 390 € + 2,50 € ([cennik](https://www.scorecastbusiness.com/en/competitions/world-cup)); Kicktipp Profipaket 9,90 €/mies. do 100 osób, 19,90 € do 300, 59,90 € do 1000 ([cennik](https://www.kicktipp.de/info/profipaket/preise)); Office Rivals darmowy do 5 graczy, potem przepustki (cennik niepubliczny).

Propozycja za turniej lub fazę pucharową LM (netto):

| Pakiet | Cena | Zawartość |
|---|---|---|
| Zespół, do 25 osób | 0 zł | lejek |
| Firma, do 100 osób | 390 zł | logo, kolor, działy, CSV |
| Duża firma, do 300 osób | 790 zł | do tego import maili, przypomnienia, wsparcie |
| Powyżej 300 / SSO / angielski | od 1490 zł, wycena | dopiero gdy funkcje istnieją |
| Pilotaż LM 2027 | 0 zł | w zamian za referencję |

Próg 390 zł (niższy niż 690 zł w dokumentach autora), bo kwota do ok. 400 zł mieści się w budżecie team leadera bez działu zakupów, a Kicktipp jest niemal darmową alternatywą.

---

## 10. Roadmapa

Tempo: ok. 8–10 h tygodniowo (3 wieczory), w sesji egzaminacyjnej (koniec stycznia – luty) tylko utrzymanie. Do 2.12 nauka minimum Reacta (komponenty, hooki, TanStack Query; 10–15 h) **nie** jest wliczona, bo do tego czasu zmiany w React są drobne. Priorytety: **P0** = bez tego nie startować z ligą (najwyżej 5 pozycji), **P1** = pierwsze tygodnie po starcie, **P2** = gdy liga gra, **P3** = później lub warunkowo.

### 10.1 Tabela propozycji

| Propozycja | Wpływ | Nakład | Python / React | Priorytet | Etap |
|---|---|---|---|---|---|
| Krok zero: zapytania B i E, rozmowa z gospodarzem, sprawdzenie zmiennych na Renderze i Usage w Neonie | warunek wszystkiego | S | — | **P0** | 1 |
| Rury: sesja przesuwana 90 dni, domena w Resend, pełny `og:image`, scheduler bez minutowych zapytań do bazy, `/health/live` | krytyczny | S–M (ok. 6 h) | Python (+1 linia React, HTML) | **P0** | 1 |
| Piątkowe przypomnienie mailem (`notification_log`, link wypisania) | **najwyższy** | M (8–10 h) | Python | **P0** | 1 |
| Ścieżka z linku – minimum: „Budzę serwer…”, bez 1,5 s, jedno pole hasła | wysoki | S (1–2 h) | React (drobne) | **P0** | 1 |
| Bezpieczeństwo danych: nocny backup do R2, `SameSite=Lax` po sprawdzeniu, fast-forward `front-listopad` | wysoki (ryzyko) | S (3 h) | YAML, Python, git | **P0** | 1 |
| Poniedziałkowe podsumowanie mailem | wysoki | S–M (6–8 h) | Python | P1 | 1 |
| Wtorkowe przypomnienie przy LM | średni–wysoki | S (2 h, ten sam mechanizm) | Python | P1 | 1 |
| Logowanie kodem z maila, rejestracja bez hasła (od razu, jeśli 25.11 aktywacja słaba) | średni–wysoki | M | Python + React | P1 | 1 |
| Werdykt na Starcie do wtorku 12:00, „Szturchnij resztę” dla każdego z imionami | średni | S + S | React | P1 | 1 |
| Uproszczenia: bez „obserwuj”, jeden tryb ligi, jeden kupon dla gracza (z obsługą `/coupon/global` przeniesioną z `feedback-listopad`), bez BTTS | średni | M | React + Python | P1 | 1 |
| Bugi: usuwanie konta właściciela, pula połączeń, filtr rankingu, rate limit per e-mail, ukryty Swagger | średni | S–M | Python | P1 | 1 |
| Sentry, healthchecks.io, UptimeRobot, poprawki deployu | średni | S | Python, YAML | P1 | 1 |
| Pomiar ciągły: `last_seen_at`, `events`, Umami | średni | S | Python (+ skrypt) | P1 | 1 |
| Atrybucja football-data, krótka polityka prywatności | niski (ryzyko) | S | React | P1 | 1 |
| `matches.locked_at`, warunkowy zapis typu | średni | M | Python | P2 | 1 |
| Rundy ligi z resetem i ogłoszeniem zwycięzcy | średni–wysoki | M | Python + React | P2 | 1 |
| `ManualProvider`: ręczne mecze (Polska, Ekstraklasa) | średni–wysoki | M | Python (+ prosty formularz admina) | P2 | 1 |
| Kalendarz `.ics` | średni | S–M | Python | P2 | 1 |
| Zewnętrzny tick (Cloudflare Worker Cron → `/internal/tick`) | średni (niezawodność) | S–M | Python + JS (Worker, 20 linii) | P2 | 1 |
| Front: TanStack Query, lazy routes, ErrorBoundary | średni (utrzymanie) | M | React | P2 | 1 |
| Web Push | średni | M–L | React + Python | P2 | 1 |
| Czutkobot albo pojedynki H2H (jedno, według próśb graczy) | średni | S–M / M | Python (+ etykieta w React) | P2 | 1 |
| Migracja contract starego Mundialu, warstwa DB, jedna definicja „meczów liczonych w lidze” | niski (utrzymanie) | M + M | Python | P2 | 1 |
| Homelab jako staging i odbiorca backupów | niski | M | Docker | P2 | 1 |
| Nowy kierunek wizualny (Kupon, Werdykt, potem reszta) | średni | M–L | React | P3 | 1 |
| Podsumowanie sezonu („Wrapped”) | średni | M | Python + React | P3 | 1 |
| Ekstraklasa / LN z płatnego API + `team_provider_refs` | średni–wysoki | L + 9–19 USD/mies. | Python | P3 | 1/2 |
| Bonus za niespodziankę, tie-breaker | niski–średni | M | Python | P3 | 1 |
| 5 rozmów ze znajomymi z korporacji | walidacja | S | — | P3 | 2 |
| Organizacje, role, branding, panel admina ligi, działy | B2B | L | Python + React | — | 2 |
| Wersja angielska | B2B | L | React | — | 2 |
| Płatny hosting w UE, live score, regulaminy, JDG | B2B | M + koszty | — | — | 2 |

### 10.2 Plan w czasie

**4–8.11 (ok. 6 h):** lista „na najbliższe dni” z rozdz. 1: krok zero, Usage i zmienne, `og:image`, Resend, sesja, scheduler i `/health/live`, fast-forward gałęzi.

**9–15.11 (ok. 10 h):** piątkowe przypomnienie mailem (Python). Pierwszy test na własnym koncie w piątek 13.11 (przypomnienie bez meczów kuponu powinno się nie wysłać – dobry test).

**16–20.11 (ok. 8 h):** drobne poprawki ścieżki z linku, backup do R2, `SameSite=Lax` po sprawdzeniu, test na telefonach 16.11, ostrzeżenia do gospodarza 19.11. **Jeśli piątkowy mail nie działa do 19.11, start 28–29.11.**

**21.11–6.12 (ok. 8–10 h/tydz.):** start ligi. Autor przez pierwsze dwa weekendy „na dyżurze”. Poniedziałkowe podsumowanie (do 30.11), wtorkowe przy LM (do 1.12). 25.11 decyzja o aktywacji: jeśli słaba, logowanie kodem z maila w kolejnym tygodniu. Sentry i healthchecks (1 wieczór).

**7–20.12:** punkt decyzji o retencji (7.12). Werdykt na Starcie, „Szturchnij”, uproszczenia. Bugi z P1. Koniec „rundy jesiennej” ogłoszony ręcznie obrazkiem (bez nowego kodu).

**21.12–10.01:** święta – tylko dyżur. Po Nowym Roku: rundy ligi (jeśli liga gra), decyzja o drugiej grupie.

**Styczeń 2027 (do sesji):** `ManualProvider` przed marcową przerwą reprezentacyjną, nauka TanStack Query na jednym ekranie (Kupon).

**Koniec stycznia – luty:** sesja, tylko utrzymanie.

**Marzec–kwiecień 2027:** faza pucharowa LM jako „nowy start” i moment na kolejną grupę. Web Push. Czutkobot albo H2H. Homelab jako staging. Ewentualnie nowy kierunek wizualny dla Kuponu i Werdyktu.

**Maj–czerwiec 2027:** migracja contract, porządki w warstwie DB, „Wrapped” przed finałem LM (5.06). **Decyzja o etapie 2** według kryterium autora: co najmniej 3 ligi, w których ponad 40% członków typuje co tydzień przez 6 tygodni. Jeśli tak: 5 rozmów ze znajomymi z korporacji, potem `walidacja-b2b.md`.

**Lipiec 2027 – czerwiec 2028 (warunkowo, etap 2):** wakacje – organizacje, role, branding, działy. Jesień – pilotaż po polsku w 1–2 firmach znajomych. Zima – forma działalności, regulaminy, płatny hosting w UE, decyzja o wersji angielskiej. Luty–maj 2028 – sprzedaż na Euro 2028.

### 10.3 Czego świadomie nie robić w najbliższych miesiącach

Rewrite’u backendu lub frontu, natywnej aplikacji, czatu, nowych odznak i statystyk, kolejnych lig zagranicznych, płatnego API dla Ekstraklasy przed sprawdzeniem ręcznych meczów, budowy B2B i landingu dla firm przed retencją, pełnego merge’a `feat/feedback-listopad`.

---

## Załącznik: jak powstała ta analiza

- Przejrzany cały kod i dokumentacja repo, historia 116 commitów i gałęzie.
- Testy: backend 1223/1223 zielone (z integracyjnymi na Postgresie 16), ruff i eslint czyste, build frontu (576 kB JS w jednym chunku).
- Aplikacja uruchomiona lokalnie na mockowanym API, zrzuty ekranów 390 px i 1280 px.
- Bugi odtworzone skryptami na osobnych bazach: usuwanie konta właściciela ligi, pula połączeń, powrót meczu do typowania, rate limit z `X-Forwarded-For`, CSRF na endpointach bez body, brak unieważniania sesji, `EXPLAIN ANALYZE` rankingu na 1,4 mln typów.
- Research konkurencji i usług w sieci (źródła przy rozdziałach).
- Niezależna krytyczna recenzja szkicu; po niej: minimum przed startem zredukowane do ok. 20–25 h, poprawiona rekomendacja dot. gałęzi (fast-forward `front-listopad` zamiast merge’a `feedback-listopad`), dodany krok zero i „opcja zero”, oznaczenia zależności od zmiennych środowiskowych, ostrzeżenie przy `SameSite=Lax`, nowy wygląd przesunięty na „opcjonalnie, później”, kolumna Python/React w roadmapie.
- Czego nie sprawdzono: wartości zmiennych na Renderze (`JWT_EXPIRE_DAYS`, `COOKIE_SECURE`, `EMAIL_FROM`, `SYNC_ENABLED`), zużycia w Neonie, nagłówków odpowiedzi produkcji, prawdziwych danych użytkowników. Autor sprawdzi to w kilka minut i powinien zrobić to przed wdrożeniem rekomendacji.
