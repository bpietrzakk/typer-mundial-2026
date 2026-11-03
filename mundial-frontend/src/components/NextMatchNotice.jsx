import { Link } from 'react-router-dom';

// top block of the start screen when there is no match to type:
// the coupon is closed or empty this week
export default function NextMatchNotice({ title, text }) {
  return (
    <section className="panel p-5 animate-fade-in" aria-labelledby="next-match-title">
      <h2 id="next-match-title" className="text-lg font-bold text-white">{title}</h2>
      {text && <p className="text-sm text-gray-400 mt-1 max-w-md">{text}</p>}
      <Link to="/matches" className="inline-block mt-4 text-sm font-semibold text-brand hover:text-brand-light transition-colors">
        Przejdź do meczów →
      </Link>
    </section>
  );
}
