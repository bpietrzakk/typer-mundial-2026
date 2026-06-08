import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { resendVerification } from '../api/auth';

export default function VerifyPending() {
  const location = useLocation();
  const email = location.state?.email || '';

  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const handleResend = async () => {
    if (!email) return;
    setSending(true);
    try {
      await resendVerification(email);
      setSent(true);
    } catch {
      // resend always returns 204 — ignore
      setSent(true);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="auth-bg min-h-screen flex items-center justify-center px-4">
      <div className="relative w-full max-w-md animate-fade-in text-center">
        <div className="glass-card p-10 space-y-4">
          <span className="text-5xl block">📬</span>
          <h1 className="text-2xl font-extrabold gradient-text">Potwierdź swój email</h1>
          <p className="text-gray-400">
            Wysłaliśmy link aktywacyjny{email ? <> na <span className="text-gray-200">{email}</span></> : ''}.
            Kliknij go, żeby aktywować konto i móc się zalogować.
          </p>
          <p className="text-sm text-gray-500">
            Sprawdź też folder spam. Link jest ważny 24 godziny.
          </p>

          {email && (
            <button onClick={handleResend} disabled={sending || sent} className="btn-secondary text-sm">
              {sending ? 'Wysyłam…' : sent ? '✅ Wysłano ponownie' : 'Wyślij link ponownie'}
            </button>
          )}

          <div className="pt-2">
            <Link to="/login" className="text-mundial-teal hover:text-mundial-teal/80 text-sm font-medium transition-colors">
              Mam już potwierdzone konto — zaloguj się
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
