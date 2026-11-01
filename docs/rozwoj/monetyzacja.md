# czutka: jak na tym zarabiać

> **Aktualizacja 28.10 (wieczór):** zweryfikowane liczby, konkurencja w PL i za granicą, analiza
> z kilku perspektyw i plan z datami są w [`analiza-biznesowa.md`](analiza-biznesowa.md). Ten plik
> zostaje jako opis opcji. Werdykt: B2C prawie bez potencjału, B2B (typer firmowy) tak, w małej
> sprawdzonej niszy.

Notatki koncepcyjne, 28.10.2026. Liczby to **szacunki do weryfikacji**, nie dane rynkowe. Kwestie
prawne zaznaczone niżej trzeba sprawdzić z prawnikiem przed wdrożeniem. To nie jest porada prawna.

---

## Punkt wyjścia

- Dziś czutka to darmowa aplikacja dla znajomych. Koszty są bliskie zera (Vercel, Render, Neon,
  football-data, Resend: darmowe plany), skala to kilkadziesiąt osób.
- Rynek typerów jest zatłoczony: aplikacje bukmacherów z darmowymi typerami, typery portali
  sportowych, Excel w firmie, grupy na Messengerze. **Nie wygramy liczbą funkcji.** Wygrać można
  doświadczeniem „gramy w swoim gronie” (patrz `pomysly.md`) i obsługą grup, którym zależy na
  porządku: firm, klubów, społeczności.
- Ruch jest sezonowy. Największe piki to wielkie turnieje (Euro 2028, Mundial 2030), mniejsze to
  starty sezonów lig i faza pucharowa Ligi Mistrzów.
- **Warunek wstępny każdej opcji:** aplikacja musi zatrzymywać ludzi (retencja). Bez pomysłów z
  `pomysly.md` (liga jako dom, typy znajomych, podsumowania, przypomnienia) płatność będzie
  sprzedawać pustą skorupę.

---

## Opcje, od najbardziej sensownej

### 1. Ligi firmowe (B2B): najlepsze dopasowanie
**Co:** firma (dział HR, employer branding, team leader) kupuje typer na turniej albo sezon dla
pracowników. W pakiecie: własna przestrzeń z logo i kolorami firmy, wiele lig (działy, oddziały),
ranking między działami, nagrody od firmy, admin po stronie firmy, eksport wyników, logowanie
służbowym mailem (później SSO).

**Dlaczego to ma sens:**
- Firmy już robią typery przy wielkich turniejach, zwykle w Excelu albo przez maile, i jest to
  uciążliwe dla organizatora.
- Firma płaci za integrację zespołu, a nie za hazard. Nagrody funduje firma, gracze nie wpłacają.
  To prawnie najczystszy model.
- Kilka umów rocznie wystarczy, żeby pokryć koszty z dużym zapasem.

**Wycena (szacunek):** np. 5–10 zł za uczestnika na turniej albo pakiety: do 50 osób ok. 500 zł,
do 200 osób ok. 1500 zł, większe indywidualnie. Firma na 150 osób przy Euro 2028 to ok. 1000–1500 zł.

**Czego brakuje w produkcie:** wielodostępność (osobne przestrzenie organizacji), role (admin
firmy), branding, faktury i płatność (Stripe, a w Polsce także przelew na fakturę), panel
statystyk dla HR, onboarding masowy (import listy maili, zaproszenia). Do tego zgodność z RODO:
umowa powierzenia, polityka prywatności, eksport i usunięcie danych.

**Jak zacząć:** pilotaż za darmo lub tanio w 2–3 firmach znajomych przed jakimś turniejem albo
fazą pucharową LM. Zebrać opinie i studium przypadku, potem prosta strona sprzedażowa przed
Euro 2028, z kampanią od jesieni 2027.

### 2. Liga Premium (B2C): płaci założyciel ligi
**Co:** podstawowa gra zostaje darmowa. Właściciel ligi może jednorazowo dokupić na sezon
„Ligę Premium”:
- więcej pytań bonusowych (król strzelców, spadki, awanse), własna punktacja, joker;
- statystyki ligi (wykresy pozycji, rekordy, odznaki), podsumowania kolejki jako grafiki do udostępnienia;
- własne logo ligi, więcej członków (np. darmowa liga do 15 osób, premium bez limitu);
- rozgrywki spoza darmowego API, np. **Ekstraklasa** (patrz koszty niżej).

**Wycena (szacunek):** ok. 29–49 zł za ligę na sezon, czyli przy 10 osobach 3–5 zł na głowę.
Ludzie i tak składają się na nagrodę, więc taki koszt jest akceptowalny, jeśli premium daje widoczną
wartość. Konwersja w takich modelach bywa niska (kilka procent lig), więc to sensowny dodatek,
a nie główne źródło.

### 3. Ekstraklasa jako wyróżnik na polskim rynku
Polski użytkownik chce typować Ekstraklasę, a darmowe źródło jej nie ma (`data-source.md`).
Płatne API (np. API-Football ok. 19 USD/mies.) rozwiązuje to i daje powód do płatności: „Ekstraklasa
w Lidze Premium” albo w pakiecie firmowym. Zagraniczne typery rzadko robią polską ligę porządnie.
To realna przewaga lokalna.

### 4. Ligi sponsorowane i lokalne (B2B2C)
**Co:** pub, klub fitness, lokalny sklep sportowy, fanklub albo radio prowadzi typer dla swoich
klientów lub słuchaczy. Nagrody (piwo, karnet, gadżety) daje sponsor, a my bierzemy opłatę za
sezon albo turniej plus branding.

**Plus:** każdy taki partner przyprowadza dziesiątki nowych graczy, czyli marketing za darmo.
**Minus:** sprzedaż „od drzwi do drzwi”, małe kwoty, wymaga prostego panelu dla partnera.
Dobry kanał na start w jednym mieście, słaby do skalowania.

### 5. White-label dla twórców i społeczności
Streamerzy, kanały piłkarskie na YouTube, podcasty i serwery Discord chcą angażować widzów.
Typer z ich marką, rankingiem widzów i nagrodami od twórcy, rozliczany abonamentem albo za sezon.
Wymaga tego samego co B2B (wielodostępność, branding), więc to ten sam produkt sprzedawany innym
kanałem.

### 6. Drobne źródła, raczej nie warto
- **Reklamy displayowe:** przy setkach lub tysiącach użytkowników to grosze, a niszczą odbiór
  („random apka z reklamami”). Odradzam.
- **Wsparcie użytkowników** („postaw kawę”, Buy Me a Coffee): pokrywa hosting, nie więcej. Można
  dodać od razu, bo nic nie kosztuje.
- **Sprzedaż danych:** nie. RODO, zaufanie, i przy tej skali to i tak nic niewarte.

---

## Czego NIE robić (ryzyka prawne, do weryfikacji z prawnikiem)

- **Wpisowe i pula pieniężna obsługiwana przez aplikację.** Typowanie wyników za wpłaty z
  wygraną zależną od wyników sportowych w Polsce najpewniej podpada pod zakłady wzajemne z ustawy
  o grach hazardowych, a te wymagają zezwolenia. Obecna funkcja „pula nagród” w lidze powinna
  zostać czysto informacyjna („ile się składamy”), a aplikacja nie może przyjmować ani wypłacać pieniędzy.
- **Afiliacja z bukmacherami.** Reklama zakładów jest w Polsce mocno ograniczona: tylko legalni,
  licencjonowani operatorzy, szczegółowe wymogi, zakaz kierowania do nieletnich. Wysokie stawki
  afiliacyjne kuszą, ale to ryzyko prawne i wizerunkowe, a dla modelu B2B (firmy) wręcz
  dyskwalifikujące. Odradzam.
- **Nagrody od nas** (nie od firmy czy sponsora) przy dużej skali mogą wymagać regulaminu
  konkursu i rozliczeń podatkowych. Łatwiej, gdy nagrody funduje klient.

---

## Koszty przy płatnej wersji (szacunek miesięczny)

| Pozycja | Dziś | Przy płatnym produkcie |
|---|---|---|
| Hosting backendu (bez usypiania) | 0 (Render free, zasypia) | ok. 7–25 USD |
| Baza (Neon) | 0 | 0–19 USD |
| Dane piłkarskie | 0 (football-data free, bez Ekstraklasy) | ok. 19–40 USD (API z Ekstraklasą) |
| Maile (Resend + domena) | 0 | 0–20 USD + domena |
| Monitoring i analityka | 0 | 0 (darmowe plany Sentry / Umami) |
| **Razem** | **ok. 0** | **ok. 30–100 USD** |

Próg opłacalności przy tych kosztach to mniej więcej 1 firma na turniej albo kilkanaście lig
premium na sezon. Prawdziwym kosztem jest czas: sprzedaż, wsparcie, RODO, faktury.

---

## Proponowana ścieżka

1. **Teraz → wiosna 2027:** dopracować produkt dla własnych grup znajomych (pomysły P0 z
   `pomysly.md`). Mierzyć retencję: ile lig gra do końca sezonu, ile osób typuje co kolejkę.
2. **Faza pucharowa LM 2027:** pilotaż w 2–3 firmach znajomych, za darmo w zamian za opinie i
   referencje. Zbudować minimum B2B: przestrzeń firmy, branding, admin firmy.
3. **Lato 2027:** Ekstraklasa przez płatne API i Liga Premium (Stripe, prosta płatność za sezon).
   Zmierzyć konwersję.
4. **Jesień 2027 → czerwiec 2028:** sprzedaż pakietów firmowych na Euro 2028. Prosta strona
   ofertowa, LinkedIn, polecenia od firm z pilotażu.
5. **Po Euro:** decyzja na danych. Jeśli B2B działa, iść w white-label i społeczności przed
   Mundialem 2030. Jeśli nie, zostawić czutkę jako tani, dopracowany produkt dla znajomych z
   Ligą Premium.

**Najważniejsze:** nie budować płatności przed retencją. Najpierw sprawić, żeby ludzie sami
wracali w każdy weekend, dopiero potem kazać za to płacić.
