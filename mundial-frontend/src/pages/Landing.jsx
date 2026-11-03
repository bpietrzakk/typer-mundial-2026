import { Link } from 'react-router-dom';
import CompetitionBadge from '../components/CompetitionBadge';
import LandingPreview from '../components/LandingPreview';

const STEPS = [
  {
    title: 'Załóż ligę',
    text: 'Nadaj jej nazwę i wybierz, co typujecie — np. tylko Ligę Mistrzów albo Premier League.',
  },
  {
    title: 'Wyślij link znajomym',
    text: 'Wklejasz link na grupę. Kto kliknie, zakłada konto i od razu jest w Twojej lidze.',
  },
  {
    title: 'Typujcie co tydzień',
    text: 'Kupon ok. 10 meczów tygodnia. Wyniki pobieramy sami, punkty i tabela liczą się same.',
  },
];

const POINTS = [
  { pts: 5, label: 'dokładny wynik', cls: 'text-hit-exact border-hit-exact/40 bg-hit-exact/15' },
  { pts: 3, label: 'różnica bramek', cls: 'text-hit-diff border-hit-diff/30 bg-hit-diff/10' },
  { pts: 2, label: 'zwycięzca', cls: 'text-hit-winner border-hit-winner/25 bg-hit-winner/10' },
];

const COMPETITIONS = ['UCL', 'EPL', 'LIGA', 'SA', 'BL', 'L1'];

// public start page for guests: what czutka is and how to begin
export default function Landing() {
  // overflow-x-hidden: the glow behind the mock is wider than a phone screen
  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden">
      {/* top bar */}
      <header className="max-w-6xl w-full mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <img src="/favicon.svg" alt="" className="w-8 h-8 rounded-lg" />
          <span className="wordmark text-xl">czutka</span>
        </Link>
        <Link to="/login" className="text-sm font-medium text-gray-300 hover:text-white px-3 py-2 rounded-lg hover:bg-surface-700/40 transition-colors">
          Zaloguj
        </Link>
      </header>

      <main className="flex-1">
        {/* hero */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-6 pb-14 sm:pt-12 lg:pt-16 grid gap-12 lg:grid-cols-[1.1fr_1fr] lg:items-center">
          <div className="animate-fade-in">
            <p className="inline-flex items-center gap-2 text-xs font-semibold text-brand bg-brand/10 border border-brand/30 rounded-full px-3 py-1 mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-brand" />
              Typer piłkarski dla znajomych
            </p>
            <h1 className="font-sans font-extrabold tracking-tight text-5xl sm:text-6xl leading-[1.02] text-white">
              Masz czutkę?<br />
              <span className="text-brand">Udowodnij.</span>
            </h1>
            <p className="mt-5 text-lg text-gray-300 max-w-xl">
              Typujesz wyniki meczów ze znajomymi w prywatnej lidze i co tydzień sprawdzacie,
              kto naprawdę zna się na piłce. Liga Mistrzów i 5 najlepszych lig Europy.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <Link to="/register" className="btn-primary text-center">
                Załóż konto
              </Link>
              <Link to="/login" className="btn-secondary text-center">
                Mam konto — zaloguj
              </Link>
            </div>
            <p className="mt-4 text-sm text-gray-500">
              Za darmo. Bez hazardu, bez wpłat, bez reklam bukmacherów.
            </p>
          </div>

          <LandingPreview />
        </section>

        {/* how it works */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 pb-14">
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-6">Jak to działa</h2>
          <ol className="grid gap-4 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <li key={s.title} className="glass-card p-5 flex gap-4 md:flex-col md:gap-3">
                <span className="w-10 h-10 shrink-0 rounded-xl bg-brand flex items-center justify-center text-lg font-black text-surface-900">
                  {i + 1}
                </span>
                <div>
                  <h3 className="text-lg font-bold text-gray-100">{s.title}</h3>
                  <p className="text-sm text-gray-400 mt-1">{s.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* scoring */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 pb-14 grid gap-6 lg:grid-cols-2 lg:items-start">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-2">Punkty bez kombinowania</h2>
            <p className="text-gray-400 mb-5">
              Za każdy mecz dostajesz punkty za najlepsze trafienie. W Lidze Mistrzów stawka rośnie
              z każdą rundą — aż do 15 pkt za dokładny wynik finału.
            </p>
            <div className="grid grid-cols-3 gap-3">
              {POINTS.map((p) => (
                <div key={p.pts} className={`rounded-2xl border px-3 py-4 text-center ${p.cls}`}>
                  <p className="score-num text-4xl font-black leading-none">{p.pts}</p>
                  <p className="text-[11px] sm:text-xs font-semibold mt-2 text-gray-300">{p.label}</p>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-3">Przykład: typ 2:1, wynik 2:1 → 5 pkt, wynik 3:2 → 3 pkt, wynik 4:0 → 2 pkt.</p>
          </div>

          <div className="glass-card p-5">
            <h3 className="text-lg font-bold text-gray-100 mb-3">Co typujecie</h3>
            <div className="flex flex-wrap gap-2 mb-5">
              {COMPETITIONS.map((code) => (
                <CompetitionBadge key={code} code={code} className="!text-xs !px-2.5 !py-1" />
              ))}
            </div>
            <ul className="space-y-2 text-sm text-gray-300">
              <li className="flex gap-2"><span className="text-brand">✓</span> Gracie o honor (albo o pizzę) — bez wpłat i bukmacherów</li>
              <li className="flex gap-2"><span className="text-brand">✓</span> Tabela ligi po każdej kolejce i typy znajomych po meczu</li>
              <li className="flex gap-2"><span className="text-brand">✓</span> Działa w przeglądarce, można dodać do ekranu telefonu</li>
            </ul>
          </div>
        </section>

        {/* final call */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 pb-16">
          <div className="glass-card p-6 sm:p-8 text-center !border-brand/30">
            <h2 className="text-2xl sm:text-3xl font-bold text-white">Kto ma największą czutkę w Twojej ekipie?</h2>
            <p className="text-gray-400 mt-2">Załóż ligę w minutę i wyślij link na grupę.</p>
            <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-center">
              <Link to="/register" className="btn-primary text-center">Załóż konto</Link>
              <Link to="/login" className="btn-secondary text-center">Mam konto — zaloguj</Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-surface-500/20 py-6 text-center text-xs text-gray-600 px-4">
        czutka · typer dla znajomych · tylko dla zabawy, bez zakładów pieniężnych
      </footer>
    </div>
  );
}
