import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { verifyEmail } from '../api/auth';

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  // status: 'loading' | 'ok' | 'error'
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      return;
    }
    verifyEmail(token)
      .then(() => setStatus('ok'))
      .catch(() => setStatus('error'));
  }, [token]);

  return (
    <div className="auth-bg min-h-screen flex items-center justify-center px-4">
      <div className="relative w-full max-w-md animate-fade-in text-center">
        {status === 'loading' && (
          <div className="glass-card p-10">
            <div className="w-12 h-12 mx-auto border-4 border-mundial-teal/30 border-t-mundial-teal rounded-full animate-spin" />
            <p className="text-gray-400 mt-4">Weryfikuję konto…</p>
          </div>
        )}

        {status === 'ok' && (
          <div className="glass-card p-10 space-y-4">
            <h1 className="text-2xl font-extrabold gradient-text">Konto potwierdzone!</h1>
            <p className="text-gray-400">Możesz się teraz zalogować.</p>
            <Link to="/login" className="btn-primary inline-block">Zaloguj się</Link>
          </div>
        )}

        {status === 'error' && (
          <div className="glass-card p-10 space-y-4">
            <h1 className="text-2xl font-extrabold text-red-400">Link nieprawidłowy</h1>
            <p className="text-gray-400">
              Link weryfikacyjny jest nieprawidłowy lub wygasł.
            </p>
            <Link to="/login" className="btn-secondary inline-block text-sm">
              Wróć do logowania
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
