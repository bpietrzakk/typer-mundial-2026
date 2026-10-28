import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { deleteLeague, leaveLeague } from '../api/leagues';
import { useToast } from '../context/ToastContext';
import { apiErrorMessage } from '../utils/apiError';

// delete (owner) or leave (member), both with an inline confirm
export default function LeagueDangerZone({ league, isOwner }) {
  const { addToast } = useToast();
  const navigate = useNavigate();
  const [confirming, setConfirming] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setLoading(true);
    try {
      if (isOwner) {
        await deleteLeague(league.id);
        addToast('Liga usunięta');
      } else {
        await leaveLeague(league.id);
        addToast('Opuściłeś ligę');
      }
      navigate('/leagues');
    } catch (err) {
      addToast(apiErrorMessage(err, isOwner ? 'Nie udało się usunąć ligi' : 'Nie udało się opuścić ligi'), 'error');
      setLoading(false);
      setConfirming(false);
    }
  };

  const title = isOwner ? 'Usuń ligę' : 'Opuść ligę';
  const description = isOwner
    ? 'Usunięcie jest nieodwracalne — wszyscy członkowie stracą dostęp.'
    : 'Stracisz dostęp do rankingu tej ligi.';
  const confirmText = isOwner
    ? `Usunąć ligę "${league.name}"? Tej operacji nie można cofnąć.`
    : `Opuścić ligę "${league.name}"?`;

  return (
    <div className="mt-8 pt-6 border-t border-surface-500/20">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className={`text-sm font-semibold ${isOwner ? 'text-red-400' : 'text-gray-400'}`}>{title}</p>
          <p className="text-xs text-gray-400 mt-0.5">{description}</p>
        </div>
        {!confirming && (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-colors
              ${isOwner
                ? 'bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20'
                : 'bg-surface-700/50 border border-surface-500/30 text-gray-400 hover:text-mundial-red hover:border-red-500/30'}`}
          >
            {title}
          </button>
        )}
      </div>

      {confirming && (
        <div className="mt-4 flex items-center gap-3 flex-wrap" role="alert">
          <p className="text-sm text-red-300 flex-1 min-w-[12rem]">{confirmText}</p>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={loading}
            className="text-sm px-4 py-2 rounded-xl bg-red-500/20 border border-red-500/40 text-red-300 hover:bg-red-500/30 transition-colors disabled:opacity-50"
          >
            {loading ? 'Chwileczkę…' : isOwner ? 'Tak, usuń ligę' : 'Tak, opuść'}
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            disabled={loading}
            className="text-sm text-gray-400 hover:text-gray-300 transition-colors"
          >
            Anuluj
          </button>
        </div>
      )}
    </div>
  );
}
