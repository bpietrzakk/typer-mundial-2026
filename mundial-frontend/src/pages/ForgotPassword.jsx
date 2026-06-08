import { useState } from 'react';
import { Link } from 'react-router-dom';
import { forgotPassword } from '../api/auth';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    try {
      await forgotPassword(email);
    } catch {
      // backend always returns 204 — ignore errors so we never reveal
      // whether the email exists
    } finally {
      setLoading(false);
      setSent(true);
    }
  };

  return (
    <div className="auth-bg min-h-screen flex items-center justify-center px-4">
      <div className="relative w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <span className="text-5xl mb-4 block">🔑</span>
          <h1 className="text-3xl font-extrabold gradient-text mb-2">Reset hasła</h1>
          <p className="text-gray-400">Wyślemy Ci link do zmiany hasła</p>
        </div>

        {sent ? (
          <div className="glass-card p-8 text-center space-y-4">
            <p className="text-gray-200">
              Jeśli konto z tym adresem istnieje, wysłaliśmy na nie link do
              resetu hasła. Sprawdź skrzynkę (i folder spam).
            </p>
            <Link to="/login" className="btn-secondary inline-block text-sm">
              Wróć do logowania
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="glass-card p-8 space-y-5">
            <div>
              <label htmlFor="fp-email" className="block text-sm font-medium text-gray-400 mb-1.5">
                Email
              </label>
              <input
                id="fp-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="twoj@email.com"
                autoComplete="email"
                className="input-field"
              />
            </div>

            <button type="submit" disabled={loading} className="w-full btn-primary">
              {loading ? 'Wysyłam…' : 'Wyślij link'}
            </button>
          </form>
        )}

        <p className="text-center mt-6 text-gray-500 text-sm">
          Pamiętasz hasło?{' '}
          <Link to="/login" className="text-mundial-green hover:text-mundial-green/80 font-medium transition-colors">
            Zaloguj się
          </Link>
        </p>
      </div>
    </div>
  );
}
