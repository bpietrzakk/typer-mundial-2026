import { Link, useNavigate } from 'react-router-dom';

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="text-center animate-fade-in">
        <p className="text-8xl font-black font-display gradient-text tracking-tight mb-2">404</p>
        <p className="text-xl font-semibold text-gray-200 mb-2">Tej strony nie ma</p>
        <p className="text-gray-500 text-sm mb-8 max-w-xs mx-auto">
          Wygląda na to, że trafiłeś w słupek. Wróć na boisko.
        </p>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="btn-secondary text-sm"
          >
            Wróć
          </button>
          <Link to="/" className="btn-primary text-sm">
            Strona główna
          </Link>
        </div>
      </div>
    </div>
  );
}
