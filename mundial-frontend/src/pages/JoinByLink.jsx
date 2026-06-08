import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { joinLeague } from '../api/leagues';

export default function JoinByLink() {
  const { code } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('joining'); // 'joining' | 'success' | 'error' | 'already'
  const [error, setError] = useState('');

  useEffect(() => {
    joinLeague(code)
      .then((league) => {
        setStatus('success');
        setTimeout(() => navigate(`/leagues/${league.id}`, { replace: true }), 1500);
      })
      .catch((err) => {
        const detail = err.response?.data?.detail || '';
        if (err.response?.status === 409) {
          setStatus('already');
          setTimeout(() => navigate('/leagues', { replace: true }), 1500);
        } else {
          setStatus('error');
          setError(detail || 'Nieprawidłowy lub wygasły kod zaproszenia');
        }
      });
  }, [code]);

  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="glass-card p-10 text-center max-w-sm w-full animate-fade-in">
        {status === 'joining' && (
          <>
            <div className="w-12 h-12 border-2 border-mundial-teal/30 border-t-mundial-teal rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-200 font-semibold">Dołączam do ligi…</p>
            <p className="text-gray-500 text-sm mt-1">Kod: <span className="font-mono text-mundial-teal">{code}</span></p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </div>
            <p className="text-gray-200 font-semibold">Dołączono!</p>
            <p className="text-gray-500 text-sm mt-1">Przekierowuję do ligi…</p>
          </>
        )}
        {status === 'already' && (
          <>
            <div className="w-12 h-12 rounded-full bg-mundial-teal/15 flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-mundial-teal" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-gray-200 font-semibold">Już jesteś w tej lidze</p>
            <p className="text-gray-500 text-sm mt-1">Przekierowuję do lig…</p>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="w-12 h-12 rounded-full bg-red-500/15 flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
            </div>
            <p className="text-gray-200 font-semibold">Nie udało się dołączyć</p>
            <p className="text-red-400 text-sm mt-1">{error}</p>
            <button onClick={() => navigate('/leagues')} className="btn-secondary text-sm mt-4">
              Wróć do lig
            </button>
          </>
        )}
      </div>
    </div>
  );
}
