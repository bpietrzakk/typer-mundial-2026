import { Link } from 'react-router-dom';

const STEPS = [
  {
    title: 'Załóż ligę i wyślij link na grupę',
    text: 'Kto kliknie link, zakłada konto i od razu jest w Twojej lidze.',
  },
  {
    title: 'Co tydzień kupon z hitami',
    text: 'Najciekawsze mecze Ligi Mistrzów i pięciu topowych lig. Typujesz do pierwszego gwizdka.',
  },
  {
    title: 'Punkty i tabela liczą się same',
    text: 'Wyniki pobieramy sami: 5 pkt za dokładny wynik, 3 za różnicę bramek, 2 za zwycięzcę.',
  },
];

// public start page for guests: one line on what czutka is, a real screen of the app
// and three steps to start. the phone image is made from the app with the e2e mocks
export default function Landing() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* top bar */}
      <header className="max-w-6xl w-full mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <span className="wordmark text-2xl leading-none">czutka</span>
        </Link>
        <Link to="/login" className="text-sm font-medium text-gray-300 hover:text-white px-3 py-2 rounded-lg hover:bg-surface-700/40 transition-colors">
          Zaloguj
        </Link>
      </header>

      <main className="flex-1">
        {/* headline + phone */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-8 pb-12 sm:pt-12 lg:pt-16 lg:pb-16 grid gap-10 lg:gap-16 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
          <div className="animate-fade-in">
            <h1 className="font-sans font-extrabold tracking-tight text-[2.5rem] sm:text-6xl leading-[1.05] text-white">
              <span className="block">Typuj z ekipą.</span>
              <span className="block text-brand text-balance">Punkty liczą się same.</span>
            </h1>
            <p className="mt-5 text-lg text-gray-300 max-w-xl">
              Prywatna liga dla znajomych: co tydzień ten sam kupon z hitami, a wyniki,
              punkty i tabela aktualizują się bez Twojego udziału.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <Link to="/register" className="btn-primary text-center">
                Załóż ligę
              </Link>
              <Link to="/login" className="btn-secondary text-center">
                Mam konto
              </Link>
            </div>
            <p className="mt-4 text-sm text-gray-500">
              Za darmo. Bez zakładów i bez wpłat.
            </p>
          </div>

          {/* real start screen of the app in a phone frame */}
          <div className="mx-auto w-[260px] sm:w-[280px]">
            <div className="rounded-[2.5rem] bg-black/50 p-2.5 ring-1 ring-surface-500/60 shadow-card">
              <div className="relative overflow-hidden rounded-[2rem] bg-surface-900">
                <img
                  src="/landing/start-phone.png"
                  width="390"
                  height="844"
                  alt="Ekran startowy czutki: najbliższy mecz z odliczaniem do startu i polami na wynik, pod nim kupon tygodnia"
                  className="block w-full h-auto"
                />
              </div>
            </div>
          </div>
        </section>

        {/* how to start */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 pb-16" aria-labelledby="steps-title">
          <h2 id="steps-title" className="sr-only">Jak zacząć</h2>
          <ol className="grid gap-0 md:gap-8 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <li key={s.title} className="glass-card py-5 flex gap-4">
                <span className="score-num text-2xl font-black leading-none text-brand w-6 shrink-0">{i + 1}</span>
                <div>
                  <h3 className="text-base font-bold text-gray-100">{s.title}</h3>
                  <p className="text-sm text-gray-400 mt-1">{s.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>
      </main>

      <footer className="border-t border-surface-500/35 py-6 text-center text-xs text-gray-600 px-4">
        czutka · typer dla znajomych · tylko dla zabawy, bez zakładów pieniężnych
      </footer>
    </div>
  );
}
