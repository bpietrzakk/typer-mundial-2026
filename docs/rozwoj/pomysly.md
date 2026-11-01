# czutka: pomysły na rozbudowę i przebudowę

Notatki z testu aplikacji (branch `feat/multi-competition`, 28.10.2026), w trzech rundach
(trzecia, „zwykły gość”, jest w sekcji [„Trzecia runda”](#trzecia-runda-zwykły-gość-który-niczego-nie-zna-2810-wieczór)). W
pierwszej testowałem jak nowy użytkownik na desktopie (1280 px) i telefonie (390 px). W drugiej
przeszedłem te same kroki jako różne osoby i sprawdziłem założenia z pierwszej rundy, w tym na
produkcji. Wyniki drugiej rundy są w sekcji
[„Druga runda: weryfikacja”](#druga-runda-weryfikacja-i-poprawki-wniosków). Część wniosków się
potwierdziła, dwa były nieprecyzyjne, trzy nowe problemy są ważniejsze niż cokolwiek z pierwszej rundy.

---

## Diagnoza w skrócie: skąd poczucie „randomowej, vibecodowanej apki”

Technicznie aplikacja działa dobrze: sama pobiera mecze, poprawnie liczy punkty, jest szybka i
porządnie przetestowana. Problem leży gdzie indziej. **Aplikacja jest zbiorem ekranów, a nie
doświadczeniem.** Ma sześć zakładek (Start, Mecze, Typy, Ranking, Ligi, Rozgrywki) i każda pokazuje
trochę tych samych danych z innej strony. Brakuje jednej osi, wokół której wszystko się kręci.

Typer wśród znajomych żyje z trzech rzeczy. Dziś żadnej z nich nie ma:

1. **Rywalizacja z konkretnymi ludźmi.** Przy meczu nie widzę, co wytypowali moi znajomi, kto mnie
   wyprzedził w tej kolejce, kto zgadł wynik, którego nikt się nie spodziewał. Typy innych da się
   zobaczyć tylko po kliknięciu gracza w rankingu i tylko dla meczów zakończonych. Ta funkcja jest
   ukryta, a ranking to suche tabelki.
2. **Rytm tygodnia.** Piątek: „masz 6 meczów do wytypowania, zamyka się o 20:30”. Poniedziałek:
   „kolejka 9 dla Bartka, +14 pkt, awans na 2. miejsce”. Aplikacja nie ma przypomnień, podsumowań
   ani momentów, na które się czeka.
3. **Emocje na żywo.** W trakcie meczu nic się nie dzieje: brak wyniku na żywo z „gdyby się teraz
   skończyło, masz +3” i brak reakcji.

Bez tego aplikacja jest formularzem do wpisywania wyników. Wygląda ładnie, ale nie ma powodu,
żeby do niej wracać inaczej niż z obowiązku.

**Rekomendacja nr 1:** przebudować aplikację wokół **ligi znajomych i bieżącej kolejki**, a nie
wokół listy rozgrywek. Większość punktów niżej z tego wynika.

---

## ✅ Zrobione 01.11.2026: P0

Wdrożone na branchu `feat/multi-competition` (backend + front, testy: 952 z bazą). Szczegóły
kuponu w [`spec-kupon-tygodnia.md`](spec-kupon-tygodnia.md), kontrakt w `docs/api-contract.md`.

- **Kupon tygodnia** (migracja 008): każda liga ma co tydzień ok. 10 wspólnych meczów, które
  automat układa z hitów albo układa organizator. Licznik „X z 10” zastąpił „68 meczów czeka”.
  Gracz bez ligi dostaje „Hity tygodnia”.
- **Typowanie w kompaktowych wierszach z autozapisem**: jeden mecz w jednym wierszu, bez przycisku „Zapisz”,
  szara podpowiedź „0” zapisuje się dopiero po wyjściu z wiersza.
- **Start = kupon moich lig** (z etykietami lig przy meczu), zamiast długiej listy wszystkich meczów.
- **Liga skupiona na kuponie**: kto już wytypował, przycisk „Przypomnij resztę” (tekst + link
  na grupę), typy ligi przy meczu po pierwszym gwizdku z rozkładem, wyniki tygodnia ze
  zwycięzcą i „Udostępnij podsumowanie”, edytor kuponu i ustawienia (tryb rankingu
  „tylko kupon” albo „wszystkie mecze”, rozmiar, automat).
- **Kreator ligi „Co typujecie?”** i karta „Wyślij link znajomym” po utworzeniu ligi.
- **Zaproszenie**: publiczny podgląd (`GET /leagues/preview/{code}`). Ekran mówi, kto zaprasza,
  do jakiej ligi, ilu graczy i co typują. Dla linku domyślnie otwiera się rejestracja, po
  dołączeniu jest przycisk „Wytypuj kupon (0/10)”, a członek z linku trafia prosto do kuponu ligi.
- **Strona startowa dla niezalogowanych** („Masz czutkę? Udowodnij.”) i tagi Open Graph z
  obrazkiem `og-image.png`.
- **Ranking ligi dla obecnych graczy**: gdy bieżące sezony mają same zera, ranking sam pokazuje
  archiwum Mundialu z banerem.
- **Prywatność**: typy innego gracza widzą tylko członkowie wspólnej ligi (403 w innym przypadku).
- **`/health` dotyka bazy**, więc keep-alive budzi też Neona.
- **Drobne**: czytelne nazwy rozgrywek zamiast skrótów (SA, L1, „LIGA”), zakładka Mecze
  otwiera rozgrywkę z najbliższym meczem, awatar zamiast ikony suwaków, „Wyloguj się” i
  „Zasady punktacji” w Ustawieniach, „Pula nagród” przemianowana na „Na co gramy?”, „Usuń
  ligę” schowane w ustawieniach zaawansowanych, rejestracja nie obiecuje już maila, na stronie
  Ranking najpierw „Rankingi Twoich lig”.

**Znane ograniczenia tego wdrożenia:**
- Kupon ułożony w niedzielę zawiera tylko niedzielne mecze (reszta tygodnia minęła). Pełny
  kupon pojawia się w poniedziałek rano.
- Podgląd linku na Messengerze ma ogólny obrazek. Wersja z nazwą ligi dla `/join/KOD` wymaga
  renderowania tagów po stronie serwera. Na produkcji `og:image` musi mieć pełny adres URL.
- Zwykłe karty w zakładce Mecze nadal od razu wpisują 0 po drugiej stronie (szara podpowiedź jest
  tylko w kuponie).
- Rozpoczęte mecze z typami ligi i wyniki tygodnia przetestowane na podstawionych danych. Na
  prawdziwych sprawdzimy po pierwszej kolejce.
- Do zrobienia przy okazji: `GET /leagues` nie zwraca `join_code` ani `ranking_mode`, a edytor
  kuponu składa kandydatów z kilku zapytań (przydałby się `GET /leagues/{id}/coupon/candidates`).

---

## P0: co zostało

### 1. Przypomnienia, które wysyłają się same
Jest przypomnienie „na grupę” od organizatora. Brakuje automatu: mail lub push „za 3 h
pierwszy mecz kuponu, nie wytypowałeś 4”. Mail wymaga domeny w Resend, a push działa na iPhonie
tylko po dodaniu aplikacji do ekranu głównego. Podsumowanie tygodnia jako **obrazek** do
wrzucenia na grupę (dziś jest tekst).

### ✅ 2. Onboarding nowego gracza bez ligi (zrobione 01.11, etap 1)
Ekran `/witaj` po rejestracji bez zaproszenia: „Co typujesz?” (obserwowanie rozgrywek), potem „Z kim
grasz?” (załóż ligę / mam kod / na razie sam). Ograniczenie: przy włączonej weryfikacji maila
pierwsze logowanie po weryfikacji idzie na Start.

### ◐ 3. Mniej zakładek, jasny podział (częściowo, etap 1)
✅ Nawigacja ma 5 pozycji (Start, Mecze, Typy, Ligi, Ranking). „Rozgrywki” są w Ustawieniach i
pod przyciskiem „Wybierz rozgrywki” w Meczach. Zostało: połączenie „obserwuj” z zakresem ligi
w jedno pojęcie i ewentualne dalsze łączenie (Typy + Ranking).

### 4. Zimny start na produkcji
`/health` budzi już bazę, ale darmowy Render nadal usypia (72 s). Decyzja: płatny plan (ok. 7 $/mies.)
albo działający keep-alive na cron-job.org.

---

## P1: wyraźnie lepsza aplikacja

### Wygląd i charakter
- ✅ *(etap 2, 01.11)* **Logo rozgrywek** zapisywane z `emblem` football-data przy synchronizacji
  (migracja 009 uzupełnia istniejące) i pokazywane w badge'ach.
- ✅ *(etap 2, 01.11)* **Herby przez nasz cache:** endpoint `GET /img/crest` (tylko
  `crests.football-data.org`, cache w pamięci i na dysku, tydzień w przeglądarce). Na Renderze
  cache dyskowy znika przy restarcie (pierwsze ładowanie wolniejsze).
- ✅ *(etap 2)* Puste stany z prostą ilustracją SVG (boisko, podium).
- **Mniej „dashboardu”, więcej piłki:** wszystko to te same ciemne karty z gradientem. Brakuje
  akcentów boiska: kolorów klubów na karcie meczu, zdjęć lub tła stadionu w nagłówku kolejki,
  ilustracji w pustych stanach. Tytuły robione fontem z czasów „Mundial Typer” (szeroki,
  plakatowy) gryzą się z nową, minimalistyczną marką.
- **Jedna paleta:** turkus, czerwień, złoto i fiolet badge'y rozgrywek konkurują ze sobą. Warto
  wybrać 1 kolor marki + 1 akcent i używać kolorów tylko do znaczenia (wygrana, pudło, na żywo).
- **Gęstość:** karty są wysokie i mają dużo pustego miejsca. Na desktopie prawa kolumna Startu jest
  w większości pusta. Kompaktowe wiersze (pkt 3) i dwie kolumny na desktopie by to rozwiązały.

### Kontekst do typowania
Typujący lubią mieć powód: forma (ostatnie 5 meczów W/R/P), miejsce w tabeli, ostatnie mecze
bezpośrednie. Wystarczy mała ikonka „i” na karcie meczu. Dane są w football-data (tabela
`standings`, mecze drużyny). Bonus: „średni typ ligi” po rozpoczęciu meczu.

### Na żywo
- wynik na żywo na karcie (synchronizacja i tak odświeża co 5 min w czasie meczów);
- „gdyby się teraz skończyło: +3” na karcie i w tabeli ligi („tabela na żywo”);
- odświeżanie bez przeładowania. Dziś Start odpytuje feed co minutę, a reszta stron wcale.

### Grywalizacja (z umiarem)
- **Joker:** raz na kolejkę podwójne punkty za wybrany mecz. Prosta zasada, która mocno zwiększa emocje.
- **Seria:** „5 kolejek z rzędu bez pudła”.
- **Odznaki sezonowe:** król dokładnych wyników, prorok (najwięcej typów pod prąd, które weszły),
  maruda (najwięcej pudeł). Na koniec sezonu podsumowanie, które chce się wrzucić do grupy.
- **Więcej pytań bonusowych:** król strzelców, kto spadnie, kto awansuje do LM. Mechanizm pytań
  w lidze już jest, a dziś ma tylko „mistrza”.

### Komunikacja w lidze
Komentarze lub reakcje pod meczem albo pod podsumowaniem kolejki. Nie pełny czat, bo ludzie mają
już grupę na Messengerze. Ale emoji pod typem kolegi („🤡” przy 0:5) to tani i skuteczny element
społecznościowy. Alternatywa: przycisk „udostępnij podsumowanie” generujący obrazek do wklejenia na
grupę. To bardziej realistyczne, bo rozmowa i tak dzieje się na Messengerze.

### Zasady w miejscu, nie na osobnej stronie
Zamiast czytać „Zasady”: podgląd punktów na karcie („dokładny 5 · różnica 3 · zwycięzca 2”)
i po meczu wyjaśnienie, czemu „+3”. Mecze pucharowe z większą punktacją oznaczone na karcie
(„1/8 finału · punkty x1.4”).

---

## P2: porządki, wydajność, technika

### Wydajność i pierwsze wrażenie
- **Zimny start Rendera:** darmowy Render usypia po 15 minutach. **Zmierzone na produkcji
  28.10: pierwsza odpowiedź `/api/health` przyszła po 72 s**, kolejne po 0,2 s. Dla nowego użytkownika z linku to najgorsze możliwe wrażenie. Keep-alive przez
  cron-job.org najwyraźniej nie działa (inaczej nie byłoby 72 s), a nawet działający pinguje
  `/health`, który nie dotyka bazy, więc darmowy Neon i tak usypia po kilku minutach i pierwsze
  zapytanie do bazy po przerwie też trwa dłużej. Płatny plan (ok. 7 USD/mies.) albo hosting bez usypiania
  usuwa problem.
- **Lokalnie (Docker, ciepła baza) strony ładują się ok. 0,5 s.** To nie mówi nic o produkcji,
  gdzie dochodzi Render, Neon i sieć. Na produkcji tego nie mierzyłem poza `/health`.
- Lokalnie, Start ok. 0,6 s przy 5–8 zapytaniach do API. Jest
  dobrze. Można jeszcze połączyć dane Startu w jeden endpoint (`/me/home`).
- **Szkielety ładowania** zamiast spinnerów: strona wygląda wtedy na szybszą, nawet gdy nie jest.

### Dług techniczny
- Stare endpointy i strony Mundialu (`/matches`, `/ranking`, `/bonus/*`, `leagues`, `scoring_rules`,
  `matches.stage`): zaplanować migrację „contract” i usunąć, gdy front z nich nie korzysta.
- 3 stare błędy lintu (`AuthContext`, `ToastContext`, `VerifyEmail`) i brak jakichkolwiek testów
  frontu. Choćby kilka testów Playwright na główne ścieżki (rejestracja, typowanie, liga) w CI.
- Brak monitoringu błędów (Sentry ma darmowy plan) i podstawowej analityki (np. Plausible lub
  Umami): dziś nie wiadomo, ile osób wraca w weekend, gdzie odpadają i czy ktoś używa bonusów.
- `ADMIN_EMAILS` w env zamiast roli w bazie. Do 2 adminów jest OK, przy B2B (patrz monetyzacja) nie.
- Weryfikacja emaila wyłączona (`REQUIRE_VERIFIED_EMAIL=false`), a domena Resend nieskonfigurowana.
  Maile (reset hasła!) mogą nie docierać.

### Drobne rzeczy z testu
- Ranking per rozgrywka liczy wszystkich użytkowników aplikacji. Przy grupie znajomych to OK,
  przy większej skali to ranking obcych ludzi: warto rozważyć, czy w ogóle ma być.
- Strona „Ligi” bez ligi ma podwójne przyciski („Dołącz do ligi / Utwórz ligę” u góry i to samo
  w pustym stanie).
- Pusty ranking mówi „Pojawi się, gdy ktoś wytypuje mecze”, ale pojawia się dopiero, gdy mecze się
  skończą.
- Na telefonie „Wyloguj” jest stale widoczne w górnym pasku i zabiera miejsce.
- „Pula nagród” w lidze: patrz uwaga prawna w `monetyzacja.md`.
- **Naprawione przy okazji testu:** „#1” przy 0 punktach na Starcie i w karcie „Moje ligi” (każdy
  był pierwszy, zanim cokolwiek się rozliczyło). Teraz miejsce pokazuje się dopiero po pierwszych
  punktach.

---

## Druga runda: weryfikacja i poprawki wniosków

Te same kroki jeszcze raz, ale jako konkretne osoby. Szukałem miejsc, gdzie pierwsza runda się myli.

### Osoby

| Kto | Co robi | Co znalazłem |
|---|---|---|
| **Znajomy z linkiem** (nie ma konta, telefon) | klika `/join/KOD` z Messengera | **Błąd krytyczny (naprawiony):** link przenosił na zwykłe logowanie bez słowa o zaproszeniu. Po rejestracji gracz lądował na „Meczach” i **nie był w lidze**, bo kod przepadał. To główna droga, którą ludzie trafiają do typera. |
| **Gracz z Mundialu** (obecny użytkownik po wdrożeniu) | otwiera swoją ligę | **Problem przed wdrożeniem:** ranking ligi domyślnie pokazuje „łącznie aktywne sezony”, czyli **wszyscy mają 0**. Punkty z Mundialu są tylko po ręcznym wybraniu sezonu archiwalnego. Dla obecnych graczy wygląda to jak wyzerowana liga. |
| **Gracz ligi tylko z Premier League** | wchodzi na Start, typuje | **Nowy problem:** Start pokazuje mecze z „obserwowanych rozgrywek” (albo ze wszystkich, gdy nic nie obserwuje), a nie z zakresu jego lig. Zachęca do typowania Serie A, które w jego lidze nic nie daje. „Obserwuj” i „zakres ligi” to dwa osobne pojęcia, choć użytkownik myśli o tym jak o jednym. |
| **Ktoś z zewnątrz / kupujący (HR, właściciel pubu)** | wchodzi na czutka.uk | Strona główna od razu przekierowuje na logowanie z hasłem „Zaloguj się i typuj wyniki!”. Brak informacji, co to jest, dla kogo, jak wygląda, ile kosztuje. **Bez strony startowej nie da się niczego sprzedać ani nikogo przekonać.** |
| **Pierwszy użytkownik po przerwie** | wchodzi na produkcję rano | 72 s czekania na pierwszą odpowiedź (zmierzone). Większość ludzi zamknie kartę po kilkunastu sekundach. |
| **Organizator ligi** | tworzy ligę, ustawia zakres, bonusy | Działa (przetestowane przez recenzentów i przeze mnie). Brakuje podglądu, kto jeszcze nie wytypował kolejki, i przypomnienia dla takich osób. To narzędzie, którego organizator najbardziej potrzebuje. |
| **Gracz „statystyk”** | Typy, Ranking | Jest sporo (rozkład trafień, skuteczność, forma). Ta część jest akurat dobra, a może nawet za bogata jak na resztę. |

### Co się potwierdziło
- Brak warstwy społecznej i rytmu (przypomnienia, podsumowania). To nadal najważniejsza zmiana produktowa.
- Typowanie kolejki: 10 osobnych kart z 10 przyciskami „Zapisz”.
- Brak logo rozgrywek, choć API je zwraca (sprawdzone: pole `emblem`, np. `https://crests.football-data.org/PL.png`).

### Co było nieprecyzyjne
- „Nie da się zobaczyć typów znajomych”: da się, ale tylko w ukrytym oknie po kliknięciu w ranking
  i tylko po meczu. Wniosek się nie zmienia (brakuje porównania przy meczu), ale problem jest inny,
  niż napisałem.
- „Zimny start 30–60 s”: było to założenie. Pomiar na produkcji dał 72 s.
- „Strony ładują się 0,5 s”: to pomiar lokalny i nie przenosi się na produkcję.

### Czego nie doceniłem w pierwszej rundzie
- **Pierwsze 2 minuty decydują**, a tam były trzy dziury naraz: 72 s ładowania, zgubione zaproszenie,
  brak strony „co to jest”. Żadna funkcja społeczna nie pomoże, jeśli znajomy z linkiem nie dotrze
  do ligi. Dlatego te rzeczy idą przed wszystko inne.
- **Pomieszanie pojęć „obserwuj” i „zakres ligi”.** To nie jest drobiazg UI, tylko powód, dla
  którego aplikacja wydaje się chaotyczna: gracz nie wie, które mecze „się liczą”.
- **Wdrożenie dla obecnych graczy.** Ich pierwsze spotkanie z nową wersją to liga z samymi zerami.

### Podważenie własnych rekomendacji
- **„4 zakładki zamiast 6”**: przesadziłem z wagą. Ludzie nie odchodzą przez liczbę zakładek, tylko
  dlatego, że nie wiedzą, co mają zrobić i po co. Zostawiam jako P1, nie P0.
- **„Push w PWA”**: na iPhonie push działa tylko po dodaniu aplikacji do ekranu głównego (iOS 16.4+),
  co robi mała część ludzi. Pewniejsze są maile (Resend jest już podpięty, ale wymaga własnej domeny)
  albo przypomnienie wysyłane przez organizatora jednym kliknięciem jako link na grupę.
- **„Komentarze i reakcje”**: rozmowa i tak dzieje się na Messengerze lub WhatsAppie. Zamiast budować
  czat, lepiej dawać ludziom rzeczy do wrzucenia tam: obrazek z podsumowaniem kolejki, link „zobacz
  typy na ten mecz”.
- **„Liga jako dom”**: prawdziwe dla grup znajomych, ale aplikacja musi działać też dla kogoś bez
  ligi. Wtedy dom to kupon kolejki, a nie pusta liga.

### Nowa kolejność (zastępuje tę z pierwszej rundy)

**P0: zanim pokażecie nową wersję komukolwiek**
1. ✅ Zaproszenie linkiem prosto do ligi (z podglądem ligi i rejestracją jako domyślną).
2. ✅ Ranking ligi dla obecnych graczy (archiwum Mundialu, gdy bieżące sezony mają zera).
3. ◐ Zimny start: `/health` budzi bazę, a decyzja o płatnym Renderze nadal czeka.
4. ✅ Strona startowa dla niezalogowanych.

**P0 produktowe**
5. ◐ Jedno pojęcie: Start pokazuje kupon moich lig z etykietami lig. „Obserwuj” w Rozgrywkach nadal istnieje.
6. ✅ Kupon z autozapisem (kupon tygodnia).
7. ✅ Organizator widzi, kto nie wytypował, i wysyła przypomnienie (link na grupę). Mail jeszcze nie.
8. ✅ Typy znajomych przy meczu po pierwszym gwizdku i podsumowanie tygodnia do udostępnienia (tekst).

**P1 i dalej:** jak w pierwszej rundzie (logo i herby, kontekst do typowania, na żywo, joker,
nawigacja, porządki techniczne).

---

## Trzecia runda: „zwykły gość, który niczego nie zna” (28.10, wieczór)

Lokalny Docker z tego brancha (z niescommitowaną poprawką zaproszeń). Pięć podejść, za każdym
razem inna osoba i świeże konto: przypadkowy gość z telefonu, organizator ligi, znajomy z linkiem
z Messengera, kibic „na poważnie” na komputerze i ktoś, kto wkleja link na grupę. Celowo
marudziłem i podważałem wszystko. Poniżej tylko to, co **nowe** albo co **wciąż nie jest
zrobione** z poprzednich rund.

### Najważniejszy wniosek tej rundy: za dużo meczów, za mało powodu

„68 meczów czeka na Twój typ” i ściana „Nie typowałeś tego meczu” zniechęcały od pierwszego
ekranu. Propozycja „Mecze tygodnia zamiast wszystkich meczów świata” jest **✅ zrobiona jako
kupon tygodnia** (patrz „Zrobione 01.11.2026” na górze).

### Problemy z tej rundy: status

✅ Zrobione 01.11: podgląd linku (tagi `og:*`, ogólny obrazek), ekran zaproszenia z nazwą ligi i
zapraszającym, rejestracja jako domyślna dla `/join`, przycisk po dołączeniu, kreator „Co
typujecie?”, „Na co gramy?” zamiast „Pula nagród”, „Usuń ligę” w ustawieniach
zaawansowanych, domyślna rozgrywka w Meczach, pełne nazwy rozgrywek, szara podpowiedź „0” (w
kuponie), prywatność typów, awatar zamiast suwaków, „Wyloguj się” w Ustawieniach, rejestracja bez
obietnicy maila, rankingi lig na górze strony Ranking.

**Co zostało z tej rundy:**
- **Nazwa „czutka” bez wyjaśnienia w aplikacji.** Hasło jest już na stronie startowej („Masz czutkę?
  Udowodnij.”). Można je powtórzyć przy pustych stanach i w podsumowaniach.
- ✅ *(etap 1)* Podpowiedź punktów przy meczu i w kuponie („5 · 3 · 2”, w fazie pucharowej LM więcej).
  Na telefonie wyjaśnienie liczb jest tylko w atrybucie `title`.
- ✅ *(etap 1)* Globalny ranking domyślnie zwinięty, na górze rankingi lig.
- ✅ *(etap 1)* 5 pozycji w nawigacji zamiast 6.
- ✅ *(etap 1)* Lista rund w Meczach pokazuje ±3 kolejki od bieżącej plus „Wszystkie rundy…”.
- ✅ *(etap 1)* Szara podpowiedź „0” także w zwykłych kartach meczów.
- **Podgląd linku z nazwą konkretnej ligi** (renderowanie tagów po stronie serwera dla `/join/KOD`).

---

## Proponowana kolejność (pierwsza runda, zastąpiona wyżej)

1. **Sprint „społeczny”:** typy znajomych po rozpoczęciu meczu (pkt 2), podsumowanie kolejki w lidze
   (pkt 4), logo rozgrywek i hostowane herby.
2. **Sprint „kupon”:** kompaktowe typowanie z autozapisem (pkt 3) i nowy podział nawigacji (pkt 6).
3. **Sprint „rytm”:** przypomnienia (push lub email), onboarding (pkt 5), joker.
4. **Sprint „na żywo”:** wynik na żywo, tabela na żywo, odświeżanie.
5. **Porządki:** contract migration, testy frontu, Sentry i analityka, płatny hosting.

Po kroku 1–2 aplikacja przestaje być „zbiorem ekranów”, a staje się typerem, w który gra się ze znajomymi.
