import { useCallback, useEffect, useRef, useState } from 'react';
import { getBonusQuestions } from '../api/leagueBonus';
import { apiErrorMessage } from '../utils/apiError';
import LeagueBonusQuestionCard from './LeagueBonusQuestionCard';
import LeagueBonusQuestionForm from './LeagueBonusQuestionForm';

// open questions first (soonest deadline), then closed ones (latest first)
function sortQuestions(list) {
  const time = (q) => new Date(q.deadline_at).getTime();
  return [...list].sort((a, b) => {
    if (a.is_open !== b.is_open) return a.is_open ? -1 : 1;
    return a.is_open ? time(a) - time(b) : time(b) - time(a);
  });
}

// league bonus questions section: list, my answers, owner create form
export default function LeagueBonusQuestions({ leagueId, isOwner, scope, competitions }) {
  const [questions, setQuestions] = useState(null); // null = loading
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const timersRef = useRef([]);

  const load = useCallback(async () => {
    try {
      const data = await getBonusQuestions(leagueId);
      setQuestions(sortQuestions(data));
      setError('');
      return data;
    } catch (err) {
      setError(apiErrorMessage(err, 'Nie udało się załadować pytań bonusowych'));
      return null;
    }
  }, [leagueId]);

  // first load; the .then keeps setState out of the effect body
  useEffect(() => {
    let cancelled = false;
    getBonusQuestions(leagueId)
      .then((data) => { if (!cancelled) setQuestions(sortQuestions(data)); })
      .catch((err) => { if (!cancelled) setError(apiErrorMessage(err, 'Nie udało się załadować pytań bonusowych')); });
    return () => { cancelled = true; };
  }, [leagueId]);

  // clear pending refreshes when leaving the page
  useEffect(() => {
    const timers = timersRef.current;
    return () => timers.forEach(clearTimeout);
  }, []);

  const retry = () => {
    setError('');
    setQuestions(null);
    load();
  };

  // a deadline just passed: reload to get the closed state + everybody's answers
  // (a few tries, in case the browser clock is slightly ahead of the server)
  const handleDeadlinePassed = useCallback(() => {
    [1500, 6000, 15000].forEach((delay) => {
      timersRef.current.push(setTimeout(load, delay));
    });
  }, [load]);

  const handleUpdated = (updated) => {
    setQuestions((list) => sortQuestions(list.map((q) => (q.id === updated.id ? updated : q))));
  };

  const handleDeleted = (id) => {
    setQuestions((list) => list.filter((q) => q.id !== id));
  };

  const handleCreated = (created) => {
    setQuestions((list) => sortQuestions([...(list || []), created]));
    setShowForm(false);
  };

  const canCreate = isOwner && scope && competitions;

  return (
    <section className="mt-8" aria-labelledby="league-bonus-title">
      <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <div>
          <h2 id="league-bonus-title" className="text-xl font-semibold text-gray-100">Pytania bonusowe</h2>
          <p className="text-sm text-gray-400 mt-0.5">Dodatkowe punkty w rankingu tej ligi, np. za mistrza sezonu.</p>
        </div>
        {canCreate && !showForm && (
          <button type="button" onClick={() => setShowForm(true)} className="btn-secondary text-sm !py-2">
            Dodaj pytanie
          </button>
        )}
      </div>

      {showForm && canCreate && (
        <LeagueBonusQuestionForm
          leagueId={leagueId}
          scope={scope}
          competitions={competitions}
          takenSeasonIds={(questions || []).map((q) => q.season.id)}
          onCreated={handleCreated}
          onCancel={() => setShowForm(false)}
        />
      )}

      {error && (
        <div className="glass-card p-6 text-center">
          <p className="text-red-400 mb-3">{error}</p>
          <button type="button" onClick={retry} className="btn-secondary text-sm !py-2">Spróbuj ponownie</button>
        </div>
      )}

      {!error && questions === null && (
        <div className="grid gap-4">
          <div className="skeleton h-40 rounded-2xl" />
        </div>
      )}

      {!error && questions !== null && questions.length === 0 && (
        <div className="glass-card p-8 text-center">
          <p className="text-gray-300 font-semibold mb-1">Brak pytań bonusowych</p>
          <p className="text-sm text-gray-400">
            {isOwner
              ? 'Dodaj pierwsze pytanie, np. kto wygra Premier League w tym sezonie.'
              : 'Właściciel ligi może dodać pytanie, np. kto wygra sezon.'}
          </p>
        </div>
      )}

      {!error && questions !== null && questions.length > 0 && (
        <div className="grid gap-4">
          {questions.map((question) => (
            <LeagueBonusQuestionCard
              key={question.id}
              leagueId={leagueId}
              question={question}
              isOwner={isOwner}
              onUpdated={handleUpdated}
              onDeleted={handleDeleted}
              onDeadlinePassed={handleDeadlinePassed}
            />
          ))}
        </div>
      )}
    </section>
  );
}
