# czutka: czy da się na tym zarabiać? Analiza biznesowa

28.10.2026. Uzupełnia i częściowo zastępuje `monetyzacja.md` (tamte opcje zostają, tu są
zweryfikowane liczby, konkurencja i werdykt). Oznaczenia: **[F]** fakt ze źródła (link),
**[S]** szacunek lub wniosek. To nie jest porada prawna ani inwestycyjna. Kwestie prawne trzeba
potwierdzić u prawnika.

---

## Werdykt w 5 zdaniach

1. **Jako darmowy typer dla znajomych w Polsce czutka praktycznie nie ma potencjału zarobkowego.**
   Rynek jest zatłoczony darmowymi aplikacjami (z Ekstraklasą, której nie mamy) i typerami
   bukmacherów z pulami po 100 tys. zł. Reklamy przy naszej skali to dziesiątki euro rocznie.
2. **Potencjał jest w innym kierunku: typer firmowy (B2B).** To sprawdzony model. Scorecast
   Business ma ponad 400 klientów firmowych, Office World Cup (bot na Slacku) 311 firm na sam
   Mundial 2026, Kicktipp sprzedaje „Profipaket” firmom i klubom.
3. **Skala realistyczna dla dwóch osób po godzinach to ok. 10–60 tys. zł na jeden duży turniej**
   (Euro 2028, Mundial 2030) [S]. To dobry projekt poboczny i świetne portfolio, ale nie
   startup na inwestora.
4. **Najciekawszy kierunek na większą skalę:** typer firmowy po angielsku, wpięty w Slacka i
   Teams, sprzedawany samoobsługowo na cały świat przed Mundialem 2030. Polska jest wtedy
   rynkiem testowym, a nie docelowym.
5. **Najpierw trzeba sprawdzić popyt, a dopiero potem budować.** 20 rozmów z HR i landing page
   z zapisami na pilotaż kosztują tydzień. Budowa wersji firmowej kosztuje kilka miesięcy.

---

## Fakty, na których stoi ta analiza

### Konkurencja bezpośrednia w Polsce (wszystkie darmowe, wszystkie z prywatnymi ligami)
| Produkt | Co ma | Skala |
|---|---|---|
| League Mates ([wykop](https://wykop.pl/ludzie/league-mates)) | Ekstraklasa, 1. i 2. liga, LM, PL, MŚ, siatkówka, rugby | [F] „3000+ aktywnych” (12.2025), awarie przy MŚ 2026 |
| LigaTyperska.pl ([link](https://ligatyperska.pl/)) | Ekstraklasa, LM, top ligi | [F] ok. 1020 użytkowników |
| Footrise ([link](https://footrise.app/pl)) | ligi z kodem, „Hot Type”, ligi społeczności | [F] utrzymuje się z darowizn |
| Protyper, Typerek, liga-typera.pl | ligi, częściowo plany płatne | [?] brak liczb |

**[S] Wniosek:** w B2C czutka nie ma żadnej przewagi funkcjonalnej. Konkurenci mają Ekstraklasę, a my
nie. Jedyne, czym możemy wygrać, to wygoda i „klimat” (patrz `pomysly.md`), ale za to nikt nie
płaci.

### Typery bukmacherów i afiliantów (konkurencja o uwagę, nie o pieniądze)
- [F] LV BET na MŚ 2026: pula ponad 100 tys. zł w bonusach ([źródło](https://najlepsibukmacherzy.pl/blog/typer-ms-2026-lvbet/)).
  Goal.pl z nagrodą STS ([regulamin](https://www.goal.pl/regulamin-konkursu-typer-na-mundial-2026/)),
  Betside, legalnibukmacherzy.pl, typer.nazielono.pl (Superbet).
- **[S]** Dla nich typer jest lejkiem do zakładów: płacą nagrodami, bo zarabiają na graczach. Nie
  wygramy z nimi nagrodami, możemy tylko z nimi nie konkurować („gramy w swoim gronie, bez
  bukmacherów”).

### Wzorce zagraniczne
- **Kicktipp (Niemcy)** [F] ([ZDF, 21.06.2026](https://www.zdfheute.de/sport/fussball-wm/fussball-wm-2026-kicktipp-tippspiel-boom-100.html)):
  ponad 6,5 mln zarejestrowanych na MŚ 2026, **ok. 1 mln € przychodu rocznie i ok. 500 tys. €
  zysku, firma dwuosobowa**. 2/3 przychodu to reklamy, reszta to premium i pakiet dla firm, klubów
  i mediów ([cennik Profipaket](https://www.kicktipp.de/info/profipaket/preise): 9,90 €/mies.
  do 100 typerów, 19,90 € do 300, 59,90 € do 1000).
  - **[S] Ile daje jeden użytkownik:** ok. 0,10 € z reklam na zarejestrowanego rocznie. Przy 5 tys.
    użytkowników czutki to **ok. 500 € rocznie**. Model Kicktippa działa tylko przy milionach
    graczy i 20 latach przewagi pierwszego gracza na rynku.
- **Scorecast Business (Francja)** [F] ([cennik](https://www.scorecastbusiness.com/en/competitions/world-cup)):
  Starter 290 € netto za 100 graczy plus 2 € za każdego kolejnego, Enterprise 390 € plus 2,50 €.
  Ponad 400 klientów firmowych w 26 krajach (Adidas FR, Burger King, TotalEnergies), ponad 400 tys.
  graczy w 2024. **To najlepszy dowód, że firmy płacą za typer.**
- **Office World Cup (bot na Slacku i Google Chat)** [F] ([link](https://officeworldcup.com/)):
  3464 graczy z 311 firm na MŚ 2026. Cennik według wyszukiwarki (niezweryfikowany): darmowo do
  10 osób, 49 £ do 50, 129 £ do 100, 399 £ bez limitu.
- **Superbru** [F]: ok. 2,9 mln użytkowników od startu, reklamy, sponsoring, white-label, B2B na wycenę.
- **Splash Sports (USA)** [F]: zarabia na prowizji od wpisowego. **W Polsce to hazard**, więc nie
  da się tego przenieść.

### Koszty danych [F]
- football-data.org: darmowo 12 rozgrywek, płatnie 49 € (30 rozgrywek) do 199 € (100).
  **Ekstraklasy nie ma w żadnym planie** ([pricing](https://www.football-data.org/pricing)).
- API-Football: Pro ok. 19 $/mies. ze wszystkimi ligami, w tym Ekstraklasą (cena z poradnika
  dostawcy, niezweryfikowana na cenniku). Sportmonks: 29 €/mies. za 5 lig ([pricing](https://www.sportmonks.com/football-api/plans-pricing/)).
- **Do sprawdzenia przed jakąkolwiek sprzedażą:** czy darmowy plan football-data pozwala na
  użycie komercyjne. Nie udało mi się otworzyć oficjalnego regulaminu, a źródła pośrednie mówią
  o „personal/non-commercial”. Jeśli tak jest, to płatny produkt wymaga płatnego planu (od 49 €/mies.)
  albo innego dostawcy. Osobna sprawa to **herby klubów i logo rozgrywek**, czyli znaki towarowe. Przy
  produkcie płatnym, zwłaszcza w materiałach reklamowych, trzeba ostrożnie.

### Prawo (do potwierdzenia u prawnika) [F]
- Typer **bez wpłat od graczy** nie jest zakładem wzajemnym w rozumieniu ustawy o grach
  hazardowych. Typer z wpisowym i wygraną jest, i wymaga zezwolenia ([SMMLegal24](https://smmlegal24.pl/polska-gola-kilka-slow-o-legalnym-typowaniu-wynikow-meczow/)).
- Nagrody od organizatora lub sponsora najlepiej przyznawać jako konkurs (przyrzeczenie
  publiczne, art. 919–921 KC) z regulaminem. **Żadnego losowania** wśród najlepszych, bo wtedy
  może to być gra losowa ([Rzeczpospolita](https://pro.rp.pl/prawo-w-firmie/art4269451-konkurs-w-internecie-nie-moze-miec-cech-gry-hazardowej)).
- Dla czutki: funkcja „pula nagród” musi pozostać informacyjna, a model B2B (nagrody funduje
  firma, udział darmowy) jest prawnie najczystszy.

---

## Runda 1: inwestor VC („pokaż mi miliard”)

**Pytania, które zada:** jak duży jest rynek, co was chroni przed konkurencją, ile kosztuje
pozyskanie użytkownika, czy to rośnie samo.

- **Rynek B2C:** darmowy z definicji. Gracze nie płacą za typer, płacą najwyżej za brak reklam
  (Kicktipp: 4,99 €/rok). Duzi gracze (bukmacherzy, ESPN, UEFA) dają typer za darmo z nagrodami,
  bo zarabiają gdzie indziej.
- **Efekt sieciowy jest lokalny.** Liga 10 znajomych nie potrzebuje, żeby w aplikacji był ktoś
  jeszcze. Kicktippa nie da się „pobić” lepszą funkcją, a nas da się skopiować w weekend. Przeniesienie
  ligi to jeden link na Messengerze.
- **Sezonowość:** piki co 2 lata (Euro, Mundial), między nimi spadek. Kicktipp ma zasięg 4,85 mln
  w maju i 13,14 mln w czerwcu ([turi2](https://www.turi2.de/aktuell/kicktipp-springt-auf-platz-vier-im-dna-ranking/), rok niepotwierdzony).
- **Przychód na użytkownika z reklam:** ok. 0,10 €/rok (wyliczone z danych Kicktippa).

**Werdykt inwestora:** „Nie zainwestuję. To produkt typu lifestyle business: najlepszy na rynku
(Kicktipp) zarabia 1 mln € rocznie po 20 latach i jest przy tym świetnym biznesem dla dwóch
osób, ale nie dla funduszu. Wróćcie, jeśli macie 100 płacących firm i retencję między turniejami.”

**Podważenie:** inwestor ocenia czutkę jako startup, a nie musi nim być. Kicktipp to dowód, że
dwuosobowa firma może mieć 500 tys. € zysku rocznie. Pytanie nie brzmi „czy to jednorożec”, tylko
„czy da się zbudować mały, rentowny biznes”. Odpowiedź w kolejnych rundach.

---

## Runda 2: handlowiec B2B („komu to sprzedam w poniedziałek?”)

### Kto kupuje
- **Klient idealny [S]:** firma 100–2000 osób z kulturą integracji. Software house'y, centra
  usług wspólnych i BPO (Kraków, Wrocław, Łódź, Katowice, Trójmiasto), firmy doradcze, banki,
  sieci handlowe (centrala).
- **Centra usług dla biznesu (SSC/BPO) to najlepszy segment [S].** Mają międzynarodowe zespoły,
  angielski jako język pracy, duże budżety na zaangażowanie i dużo osób z krajów, w których
  piłka jest religią. **Wymaga to wersji angielskiej**, której dziś nie ma.
- **Kto decyduje:** HR Business Partner, employer branding, office manager, „engagement /
  culture”, czasem team leader z budżetem na integrację.
- [F] Polskie firmy już to robią. Lorenz P.S.A. ([zasady](https://ligatyperowlorenz.pl/assets/files/zasady-liga-typerow-2026.pdf))
  i Primost Południe ([link](https://www.primost-poludnie.pl/typer/)) miały firmowe typery na MŚ
  2026 z logowaniem mailem służbowym. Inne firmy używają Excela, Google Forms albo darmowego Kicktippa.

### Co dokładnie boli organizatora w firmie
1. Excel i ręczne liczenie punktów, kłótnie o wyniki, „kto wpisał po czasie”.
2. Darmowe narzędzia mają reklamy, a czasem **reklamy bukmacherów**. W firmie to dyskwalifikuje.
3. Brak logo firmy i rankingu działów („IT kontra Finanse” to cała zabawa).
4. RODO: dane pracowników w losowej aplikacji bez umowy powierzenia.
5. Trzeba ludziom przypominać, a organizator nie ma na to czasu.

### Co sprzedajemy (jedno zdanie)
„Typer na Euro dla Twojej firmy w 10 minut: logo i kolory firmy, ranking działów, punkty liczą
się same, przypomnienia, zero hazardu i zero reklam bukmacherów, faktura VAT.”

### Cennik [S] (porównanie: Scorecast 290 € ≈ 1250 zł za 100 osób)
| Pakiet | Dla kogo | Cena za turniej (netto) |
|---|---|---|
| Zespół | do 30 osób | 0 zł (marketing, jak Office World Cup) |
| Firma | do 150 osób | 690 zł |
| Duża firma | do 500 osób | 1490 zł |
| Korporacja | powyżej 500, SSO, kilka krajów | od 2990 zł, wycena |

Sezon ligowy (LM, Premier League): abonament ok. 30–40% ceny turnieju za kwartał.

### Kalendarz sprzedaży (to najważniejsze)
- **Euro 2028: czerwiec–lipiec 2028.** Firmy decydują 1–3 miesiące przed startem, budżety
  ustalają wcześniej. **Okno sprzedaży: luty–maj 2028.**
- Przed tym jest jedna okazja na pilotaż: **faza pucharowa Ligi Mistrzów (luty–maj 2027)**.
- Między turniejami sprzedaż jest bliska zera. To trzeba przyjąć, a nie z tym walczyć.

### Skala [S]
- Realistycznie dla dwóch osób bez doświadczenia w sprzedaży: **10–40 firm na Euro 2028** ×
  ok. 800–1200 zł = **ok. 10–50 tys. zł**.
- Przy dobrym kanale partnerskim (agencja eventowa, platforma benefitowa, firma HR-tech) więcej.
  Jedna platforma benefitowa z tysiącami klientów zmienia rachunek, ale taka współpraca to
  osobny projekt sprzedażowy.

### Obiekcje i odpowiedzi
| Obiekcja | Odpowiedź |
|---|---|
| „Mamy darmowego Kicktippa” | Bez reklam, z logo, z rankingiem działów, po polsku i angielsku, z fakturą i umową RODO |
| „Zrobimy w Excelu” | Pokaż, ile godzin to zajmie organizatorowi przez 51 meczów Euro |
| „Dział bezpieczeństwa” | Ankieta bezpieczeństwa, umowa powierzenia, dane w UE, logowanie mailem służbowym |
| „A jak padnie w trakcie turnieju?” | Płatny hosting bez usypiania, monitoring. **Dziś darmowy Render usypia, a zimny start trwa 72 s, co dyskwalifikuje** |

**Werdykt handlowca:** „Da się sprzedać. To konkretny problem i konkretny budżet, a konkurencja
w Polsce jest słaba (liga-typera.pl na wycenę, Trefa darmowa). Ale to praca handlowa, nie
programistyczna: telefony, LinkedIn, demo, faktury. Jeśli nikt z was nie lubi rozmawiać z
klientami, ten model nie ruszy.”

**Podważenie:** 400 klientów Scorecasta to wynik wielu lat i 26 krajów. Office World Cup, czyli
prawdopodobnie lider Slacka, miał 311 firm na Mundialu, z czego wiele zapewne na darmowym
pakiecie. Nawet lider niszy przy największym turnieju świata zarabia kwoty rzędu dziesiątek tysięcy
funtów [S]. Nisza istnieje, ale jest mała i sezonowa.

---

## Runda 3: marketingowiec i agencja („kampania, nie aplikacja”)

**Pomysł:** marki (piwo, bank, telekom, sieć handlowa), media (radio, portal regionalny) i
kluby (Ekstraklasa, żużel) robią typer dla swoich klientów lub kibiców z nagrodami od marki.
Kupują to jako **kampanię**: landing w barwach marki, regulamin, nagrody, zgody marketingowe,
raport po kampanii.

- **Plus:** najwyższa jednorazowa kwota [S], ok. 10–50 tys. zł za kampanię, bo to budżet
  marketingowy, a nie HR.
- **Minus:** każda kampania jest „szyta na miarę”, a marka chce agencji z portfolio, nie dwóch
  programistów. Konkurencja to Superbru white-label, Scorecast i agencje, które zrobią to same.
  Trzeba ogarnąć regulaminy konkursów, podatek od nagród i zgody RODO.
- **Realny wariant:** sprzedawać **silnik** agencjom interaktywnym (licencja na kampanię), a
  nie markom bezpośrednio. Agencja ma klienta i robi kreację, my dajemy działający typer.

**Werdykt:** dobre jako dodatkowe źródło, gdy produkt B2B już istnieje (to ten sam silnik z
brandingiem). Na start za drogie w sprzedaży.

---

## Runda 4: twórca i społeczność („moi widzowie chcą grać ze mną”)

- [F] Typery na Discorda istnieją (Football Nation, Tossup, UnifyFootball). Footrise ma ligi
  partnerskie społeczności („Piłka Bez Cenzury”, „Zgrywus Ekstraklasowy”).
- [?] Nie znalazłem polskiego typera dla youtuberów i streamerów (Kanał Sportowy, streamy
  piłkarskie). To luka, ale nie wiadomo, czy jest na nią popyt.
- **Problem:** twórcy rzadko płacą za narzędzia. Zarabiają na sponsorach, a sponsorem typera
  najczęściej chce być… bukmacher.
- **Lepszy sposób na ten segment:** nie źródło przychodu, tylko **kanał pozyskania**. Darmowa
  liga dla społeczności twórcy (z jego nazwą) przyprowadza setki graczy, z których część założy
  własne ligi znajomych albo wniesie typer do swojej firmy.

**Werdykt:** marketing, nie przychód.

---

## Runda 5: adwokat diabła i księgowy („dlaczego to się nie uda”)

1. **Czas to prawdziwy koszt.** Sprzedaż B2B, wsparcie w trakcie turnieju (wieczory i weekendy),
   faktury, RODO, regulaminy. Przy 30 klientach to kilkadziesiąt godzin w miesiącu turnieju.
2. **Dane i licencje.** Status komercyjny darmowego football-data jest niejasny. Płatny plan to
   49 €/mies. Herby klubów to znaki towarowe, a Ekstraklasa wymaga innego dostawcy.
3. **Niezawodność.** Turniej trwa miesiąc, a awaria w dniu finału przekreśla klienta na zawsze.
   League Mates miał awarie przy MŚ 2026 i zostało to publicznie opisane na Wykopie.
4. **Działalność gospodarcza.** Faktura VAT wymaga firmy (JDG albo spółki), księgowości i
   regulaminu usługi. Na start można testować przez firmę któregoś z was albo w ramach
   działalności nierejestrowanej, ale trzeba to sprawdzić z księgowym.
5. **Jeden turniej na dwa lata** oznacza dwa lata czekania na weryfikację każdej hipotezy.
6. **Produkt nie jest gotowy na B2B:** brak wielodostępności (przestrzeń firmy), ról, brandingu,
   angielskiego, rankingu działów, importu listy osób, płatności i faktur. Hosting usypia.

**Kryteria porzucenia [S]** (zapisać teraz, żeby potem nie oszukiwać się sentymentem):
- po 20 rozmowach z HR mniej niż 3 firmy deklarują, że zapłacą → porzucić B2B;
- po pilotażu na LM 2027 mniej niż połowa graczy typuje po 3. tygodniu → najpierw retencja, potem sprzedaż;
- na Euro 2028 mniej niż 10 płacących firm → czutka zostaje hobby i portfolio.

---

## Runda 6: synteza („czy jest potencjał, a jeśli tak, to gdzie?”)

| Kierunek | Potencjał | Koszt wejścia | Ocena |
|---|---|---|---|
| Darmowy typer dla znajomych (B2C, PL) | znikomy (reklamy ok. 500 €/rok przy 5 tys. graczy) | niski | **tylko jako marketing i portfolio** |
| Liga Premium (płaci założyciel ligi) | mały (konwersja kilka %, a konkurenci są darmowi) | średni | dodatek, nie biznes |
| **Typer firmowy PL (B2B)** | **10–60 tys. zł na turniej** [S] | średni (wersja firmowa) + praca handlowa | **najlepszy pierwszy krok** |
| **Typer firmowy po angielsku na Slack/Teams (globalnie)** | większy, samoobsługowy, Mundial 2030 to rekordowy turniej | wysoki (integracje, angielski, płatności globalne) | **kierunek na skalę po Euro 2028** |
| Silnik white-label dla agencji, mediów i klubów | wysokie kwoty, mało klientów | wysoki (sprzedaż, umowy) | później, ten sam silnik co B2B |
| Społeczności i twórcy | marketing | niski | kanał pozyskania |
| Typer „na wszystko” (Eurowizja, F1, skoki, żużel, Oscary; wyniki wpisuje organizator) | rozwiązuje sezonowość, ale trudny do wyjaśnienia | średni | ciekawy eksperyment w B2C, nie priorytet |
| Sprzedaż aplikacji lub kodu | ok. zero bez przychodów (wycena idzie od zysku) | — | nie |

### Czy aplikacja ma szansę się sprzedać?
- **W obecnej formie (darmowy typer dla znajomych): nie.** Nie ma przewagi nad darmowymi
  konkurentami i nie ma kto za nią zapłacić.
- **Po przestawieniu na typer firmowy: tak, w małej, sprawdzonej niszy.** Firmy już płacą
  (Scorecast, Office World Cup, Kicktipp Profipaket), a w Polsce nie ma mocnego lokalnego gracza.
- **Na większą skalę: tylko globalnie** (angielski, Slack i Teams, samoobsługa, Mundial 2030).
  Wtedy konkurencja jest silniejsza, ale rynek sto razy większy.

### Co z tego wynika dla produktu
Dobra wiadomość: **to, co trzeba zrobić dla znajomych (`pomysly.md`), jest też fundamentem
wersji firmowej.** Kupon tygodnia lub turnieju, przypomnienia, podsumowania i ranking grupy to
dokładnie to, za co płaci HR. Wersja firmowa dokłada na wierzch tylko „przestrzeń organizacji”.
Nie trzeba wybierać między „fajną apką dla kumpli” a „biznesem”, wystarczy dobra kolejność.

---

## Plan działania z datami

| Kiedy | Co | Miara sukcesu |
|---|---|---|
| **XI 2026 – I 2027** | Rdzeń dla znajomych: kupon tygodnia, podgląd linku, onboarding, płatny hosting bez usypiania (ok. 7 $/mies.) | ≥ 40% członków lig typuje co tydzień przez 6 tygodni |
| **XII 2026 – I 2027** (równolegle, tydzień pracy) | **Test popytu bez kodu:** landing „Typer firmowy na Euro 2028” z zapisem na pilotaż + **20 rozmów** z HR i office managerami (znajomi w korpo, LinkedIn, SSC w Krakowie i Wrocławiu) | ≥ 3 firmy deklarujące zapłatę i ≥ 5 chętnych na pilotaż |
| **II – V 2027** | **Pilotaż w 3–5 firmach** na fazie pucharowej LM, za darmo w zamian za opinie i zgodę na referencje. Minimum B2B: przestrzeń firmy (logo, kolor), import maili, ranking działów, wersja angielska | NPS organizatora, % graczy aktywnych do finału |
| **VI – XII 2027** | Płatności (faktura VAT przelewem + Stripe), cennik, regulamin, umowa powierzenia, studium przypadku z pilotażu, wyjaśnienie licencji danych | gotowa oferta i 2–3 referencje |
| **II – V 2028** | **Sprzedaż na Euro 2028** (LinkedIn, polecenia z pilotażu, agencje eventowe) | ≥ 10 płacących firm (minimum), cel 30 |
| **VII 2028** | Decyzja na danych | jeśli ≥ 30 firm i ≥ 50% chce dalej: Slack/Teams i rynek globalny przed Mundialem 2030; jeśli nie: hobby i portfolio |

### Co zrobić w tym tygodniu (koszt prawie zero)
1. Zapytać 5 znajomych z korporacji: „czy u was był typer na Mundial, kto go robił, w czym, czy
   firma by za to zapłaciła?”. To w 30 minut weryfikuje połowę tego dokumentu.
2. Napisać do football-data.org (info@football-data.org) z pytaniem o użycie komercyjne.
3. Zanotować w kalendarzu: start okna sprzedaży Euro 2028, czyli luty 2028.

---

## Najważniejsza myśl

Czutka nie przegrywa tym, co ma, tylko tym, dla kogo jest. Dla grupy kumpli jest jedną z wielu
darmowych aplikacji. Dla działu HR, który co dwa lata walczy z Excelem i z reklamami bukmacherów, może
być jedyną sensowną opcją po polsku. Ten sam kod, inny klient.
