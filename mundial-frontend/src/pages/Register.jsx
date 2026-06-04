import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const [nick, setNick] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // client-side validation matching backend constraints
    if (!nick || !email || !password || !confirmPassword) {
      setError('Wypełnij wszystkie pola');
      return;
    }
    if (nick.length < 2 || nick.length > 32) {
      setError('Nick musi mieć od 2 do 32 znaków');
      return;
    }
    if (password.length < 8) {
      setError('Hasło musi mieć minimum 8 znaków');
      return;
    }
    if (password !== confirmPassword) {
      setError('Hasła nie są identyczne');
      return;
    }

    setLoading(true);
    try {
      await register(nick, email, password);
      navigate('/matches', { replace: true });
    } catch (err) {
      let msg = 'Błąd rejestracji — spróbuj ponownie';
      if (!err.response || err.response.status === 504 || err.response.status === 502) {
        msg = 'Brak połączenia z serwerem. Czy backend jest włączony?';
      } else if (Array.isArray(err.response?.data?.detail)) {
        msg = err.response.data.detail[0]?.msg || msg;
      } else if (typeof err.response?.data?.detail === 'string') {
        msg = err.response.data.detail;
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-bg min-h-screen flex items-center justify-center px-4 py-8">
      <div className="relative w-full max-w-md animate-fade-in">
        {/* header */}
        <div className="text-center mb-8">
          <span className="text-5xl mb-4 block">⚽</span>
          <h1 className="text-3xl font-extrabold gradient-text mb-2">
            Dołącz do gry!
          </h1>
          <p className="text-gray-400">Stwórz konto i rywalizuj ze znajomymi</p>
        </div>

        {/* register form */}
        <form onSubmit={handleSubmit} className="glass-card p-8 space-y-5">
          <div>
            <label htmlFor="reg-nick" className="block text-sm font-medium text-gray-400 mb-1.5">
              Nick
            </label>
            <input
              id="reg-nick"
              type="text"
              value={nick}
              onChange={(e) => setNick(e.target.value)}
              placeholder="TwojNick"
              autoComplete="username"
              maxLength={32}
              className="input-field"
            />
          </div>

          <div>
            <label htmlFor="reg-email" className="block text-sm font-medium text-gray-400 mb-1.5">
              Email
            </label>
            <input
              id="reg-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="twoj@email.com"
              autoComplete="email"
              className="input-field"
            />
          </div>

          <div>
            <label htmlFor="reg-password" className="block text-sm font-medium text-gray-400 mb-1.5">
              Hasło
            </label>
            <input
              id="reg-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 znaków"
              autoComplete="new-password"
              className="input-field"
            />
          </div>

          <div>
            <label htmlFor="reg-confirm" className="block text-sm font-medium text-gray-400 mb-1.5">
              Potwierdź hasło
            </label>
            <input
              id="reg-confirm"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Powtórz hasło"
              autoComplete="new-password"
              className="input-field"
            />
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full btn-primary"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Rejestracja…
              </span>
            ) : (
              'Zarejestruj się'
            )}
          </button>
        </form>

        {/* login link */}
        <p className="text-center mt-6 text-gray-500 text-sm">
          Masz już konto?{' '}
          <Link to="/login" className="text-mundial-teal hover:text-mundial-teal/80 font-medium transition-colors">
            Zaloguj się
          </Link>
        </p>
      </div>
    </div>
  );
}
