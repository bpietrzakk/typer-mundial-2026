import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import PasswordInput from '../components/PasswordInput';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // redirect to where the user came from (or /matches by default)
  const from = location.state?.from?.pathname || '/matches';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Wypełnij wszystkie pola');
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      // 403 = correct password but email not confirmed yet
      if (err.response?.status === 403) {
        navigate('/verify-pending', { state: { email } });
        return;
      }
      let msg = 'Błąd logowania — spróbuj ponownie';
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
    <div className="auth-bg min-h-screen flex items-center justify-center px-4">
      <div className="relative w-full max-w-md animate-fade-in">
        {/* header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold gradient-text mb-2">
            Mundial Typer 2026
          </h1>
          <p className="text-gray-400">Zaloguj się i typuj wyniki!</p>
        </div>

        {/* login form */}
        <form onSubmit={handleSubmit} className="glass-card p-8 space-y-5">
          <div>
            <label htmlFor="login-email" className="block text-sm font-medium text-gray-400 mb-1.5">
              Email
            </label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="twoj@email.com"
              autoComplete="email"
              className="input-field"
            />
          </div>

          <div>
            <label htmlFor="login-password" className="block text-sm font-medium text-gray-400 mb-1.5">
              Hasło
            </label>
            <PasswordInput
              id="login-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
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
                Logowanie…
              </span>
            ) : (
              'Zaloguj się'
            )}
          </button>
        </form>

        {/* forgot password */}
        <p className="text-center mt-4 text-sm">
          <Link to="/forgot-password" className="text-gray-500 hover:text-mundial-teal transition-colors">
            Nie pamiętasz hasła?
          </Link>
        </p>

        {/* register link */}
        <p className="text-center mt-2 text-gray-500 text-sm">
          Nie masz konta?{' '}
          <Link to="/register" className="text-mundial-teal hover:text-mundial-teal/80 font-medium transition-colors">
            Zarejestruj się
          </Link>
        </p>
      </div>
    </div>
  );
}
