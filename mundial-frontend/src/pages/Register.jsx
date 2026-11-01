import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import PasswordInput from '../components/PasswordInput';
import InviteNotice from '../components/InviteNotice';
import { clearPendingInvite, inviteCodeFromPath, isInvitePath, readPendingInvite, savePendingInvite } from '../utils/pendingInvite';

export default function Register() {
  const [nick, setNick] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const location = useLocation();

  // came from an invite link? go back there after sign-up so the player joins the league
  const from = location.state?.from?.pathname || readPendingInvite() || null;
  const invited = isInvitePath(from);
  savePendingInvite(from);

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
      const res = await register(nick, email, password);
      if (res.verified) {
        clearPendingInvite();
        // invited -> straight to the league, everyone else gets the short onboarding
        navigate(invited ? from : '/witaj', { replace: true });
      } else {
        // email confirmation required — show the "check your inbox" screen
        navigate('/verify-pending', { state: { email } });
      }
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
          <img src="/favicon.svg" alt="czutka" className="w-16 h-16 mx-auto mb-4 rounded-xl" />
          <h1 className="text-3xl font-extrabold tracking-tight text-white mb-2">
            Dołącz do gry!
          </h1>
          <p className="text-gray-400">Stwórz konto i rywalizuj ze znajomymi</p>
        </div>

        {invited && (
          <>
            <InviteNotice code={inviteCodeFromPath(from)} mode="register" />
            {/* invited players usually have no account, but make the other way obvious */}
            <Link
              to="/login"
              state={{ from: { pathname: from } }}
              className="flex items-center justify-center w-full mb-4 px-4 py-2.5 rounded-xl border border-surface-500/50 bg-surface-800/50 text-sm font-semibold text-gray-300 hover:border-brand/50 hover:text-brand transition-colors"
            >
              Mam już konto — zaloguj się
            </Link>
          </>
        )}

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
            <PasswordInput
              id="reg-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 znaków"
              autoComplete="new-password"
            />
          </div>

          <div>
            <label htmlFor="reg-confirm" className="block text-sm font-medium text-gray-400 mb-1.5">
              Potwierdź hasło
            </label>
            <PasswordInput
              id="reg-confirm"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Powtórz hasło"
              autoComplete="new-password"
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
          <p className="text-xs text-gray-500 text-center">
            Po rejestracji możesz od razu typować.
          </p>
        </form>

        {/* login link */}
        <p className="text-center mt-6 text-gray-500 text-sm">
          Masz już konto?{' '}
          <Link to="/login" state={from ? { from: { pathname: from } } : undefined} className="text-brand hover:text-brand/80 font-medium transition-colors">
            Zaloguj się
          </Link>
        </p>
      </div>
    </div>
  );
}

