import { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { resetPassword } from '../api/auth';

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) {
      setError('Hasło musi mieć co najmniej 8 znaków');
      return;
    }
    if (password !== confirm) {
      setError('Hasła nie są takie same');
      return;
    }
    setLoading(true);
    try {
      await resetPassword(token, password);
      setDone(true);
      setTimeout(() => navigate('/login', { replace: true }), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Nie udało się zmienić hasła');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-bg min-h-screen flex items-center justify-center px-4">
      <div className="relative w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <span className="text-5xl mb-4 block">🔐</span>
          <h1 className="text-3xl font-extrabold gradient-text mb-2">Nowe hasło</h1>
          <p className="text-gray-400">Ustaw nowe hasło do swojego konta</p>
        </div>

        {!token ? (
          <div className="glass-card p-8 text-center space-y-4">
            <p className="text-red-400">Brak tokenu w linku — otwórz link z emaila ponownie.</p>
            <Link to="/forgot-password" className="btn-secondary inline-block text-sm">
              Poproś o nowy link
            </Link>
          </div>
        ) : done ? (
          <div className="glass-card p-8 text-center">
            <p className="text-emerald-400">✅ Hasło zmienione! Przekierowuję do logowania…</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="glass-card p-8 space-y-5">
            <div>
              <label htmlFor="rp-pass" className="block text-sm font-medium text-gray-400 mb-1.5">
                Nowe hasło
              </label>
              <input
                id="rp-pass"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="new-password"
                className="input-field"
              />
            </div>
            <div>
              <label htmlFor="rp-confirm" className="block text-sm font-medium text-gray-400 mb-1.5">
                Powtórz hasło
              </label>
              <input
                id="rp-confirm"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="••••••••"
                autoComplete="new-password"
                className="input-field"
              />
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="w-full btn-primary">
              {loading ? 'Zapisuję…' : 'Zmień hasło'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
