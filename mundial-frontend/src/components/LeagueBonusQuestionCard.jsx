import { useState } from 'react';
import { deleteBonusQuestion } from '../api/leagueBonus';
import { useToast } from '../hooks/useToast';
import { apiErrorMessage } from '../utils/apiError';
import { formatDateTime } from '../utils/format';
import LeagueBonusAnswerForm from './LeagueBonusAnswerForm';
import LeagueBonusAnswersTable from './LeagueBonusAnswersTable';
import LeagueBonusResolveForm from './LeagueBonusResolveForm';
import LeagueBonusStatusBadge from './LeagueBonusStatusBadge';
import LeagueCountdown from './LeagueCountdown';
import LeagueTeamLabel from './LeagueTeamLabel';

// one bonus question ("who wins the season" or an own team question):
// my answer, deadline, others' answers, owner delete / resolve
export default function LeagueBonusQuestionCard({
  leagueId, question, isOwner, onUpdated, onDeleted, onDeadlinePassed,
}) {
  const { addToast } = useToast();
  const [editing, setEditing] = useState(!question.my_answer);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [resolving, setResolving] = useState(false);

  const { season, my_answer: myAnswer, resolved_team: resolvedTeam } = question;
  const isPick = question.kind === 'team_pick';
  const count = question.answers_count || 1;
  const title = isPick ? question.title : `Kto wygra ${season.competition.name} ${season.label}?`;
  const resolvedTeams = question.resolved_teams?.length ? question.resolved_teams : (resolvedTeam ? [resolvedTeam] : []);
  const myTeams = myAnswer ? (myAnswer.teams?.length ? myAnswer.teams : [myAnswer.team]) : [];
  const resolvedIds = new Set(resolvedTeams.map((t) => t.id));
  // owner marks the correct teams of an own question once answering closed
  const canResolve = isOwner && isPick && !question.is_open;

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteBonusQuestion(leagueId, question.id);
      addToast('Pytanie usunięte');
      onDeleted(question.id);
    } catch (err) {
      addToast(apiErrorMessage(err, 'Nie udało się usunąć pytania'), 'error');
      // 409 = deadline passed, the card has to switch to the closed state
      if (err.response?.status === 409) onDeadlinePassed?.();
      setConfirmingDelete(false);
      setDeleting(false);
    }
  };

  const handleSaved = (updated) => {
    onUpdated(updated);
    setEditing(false);
  };

  return (
    <article className="glass-card p-5" aria-label={title}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wider text-gray-400">
            {season.competition.name} · {season.label}
          </p>
          <h3 className="text-lg font-semibold text-gray-100 mt-0.5">{title}</h3>
          {count > 1 && (
            <p className="text-xs text-gray-400 mt-0.5">{count} poprawne odpowiedzi — typujesz {count} drużyny</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="badge bg-mundial-teal/15 text-mundial-teal normal-case tracking-normal">
            +{question.points} pkt{count > 1 ? ' za drużynę' : ''}
          </span>
          <LeagueBonusStatusBadge question={question} />
        </div>
      </div>

      <p className="text-sm text-gray-400 mt-2">
        Termin odpowiedzi: <span className="text-gray-200">{formatDateTime(question.deadline_at)}</span>
        {question.is_open ? (
          <> · <LeagueCountdown deadlineAt={question.deadline_at} onExpire={onDeadlinePassed} /></>
        ) : (
          <> · <span className="text-gray-400">zamknięte</span></>
        )}
      </p>

      {/* resolved answer + my result */}
      {resolvedTeams.length > 0 && !resolving && (
        <div className="mt-4 rounded-xl border border-mundial-gold/25 bg-mundial-gold/5 px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-wider text-gray-400 mb-1">
              {isPick ? (resolvedTeams.length > 1 ? 'Poprawne odpowiedzi' : 'Poprawna odpowiedź') : 'Mistrz sezonu'}
            </p>
            <div className="flex flex-col gap-1">
              {resolvedTeams.map((t) => (
                <LeagueTeamLabel key={t.id} team={t} className="text-mundial-gold font-semibold" />
              ))}
            </div>
            {canResolve && (
              <button type="button" onClick={() => setResolving(true)} className="mt-2 text-xs text-gray-400 hover:text-mundial-teal underline">
                Popraw rozstrzygnięcie
              </button>
            )}
          </div>
          {myAnswer ? (
            <div className="text-right">
              <p className="text-xs uppercase tracking-wider text-gray-400 mb-1">Twój wynik</p>
              {myAnswer.points_awarded > 0 ? (
                <span className="points-exact text-lg">+{myAnswer.points_awarded} pkt</span>
              ) : (
                <span className="text-gray-400 font-bold text-lg">0 pkt</span>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400">Nie oddałeś typu</p>
          )}
        </div>
      )}

      {/* owner: resolve an own question after the deadline */}
      {canResolve && (resolvedTeams.length === 0 || resolving) && (
        <div className="mt-4">
          <LeagueBonusResolveForm
            leagueId={leagueId}
            question={question}
            onResolved={(updated) => { onUpdated(updated); setResolving(false); }}
            onCancel={resolving ? () => setResolving(false) : undefined}
          />
        </div>
      )}

      {/* my answer */}
      <div className="mt-4">
        {question.is_open && editing ? (
          <LeagueBonusAnswerForm
            leagueId={leagueId}
            question={question}
            onSaved={handleSaved}
            onCancel={() => setEditing(false)}
            onDeadlinePassed={onDeadlinePassed}
          />
        ) : (
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-wider text-gray-400 mb-1">Twój typ</p>
              {myAnswer ? (
                <div className="flex flex-col gap-1">
                  {myTeams.map((t) => (
                    <span key={t.id} className="flex items-center gap-2">
                      <LeagueTeamLabel team={t} className="text-gray-100 font-medium" />
                      {resolvedTeams.length > 0 && (
                        <span className={resolvedIds.has(t.id) ? 'text-emerald-400 text-xs font-bold' : 'text-gray-500 text-xs'}>
                          {resolvedIds.has(t.id) ? '✓' : '✗'}
                        </span>
                      )}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">Nie oddałeś typu na to pytanie</p>
              )}
            </div>
            {question.is_open && (
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="text-sm px-3 py-1.5 rounded-lg bg-surface-600/30 text-gray-300 hover:text-mundial-teal transition-colors"
              >
                {myAnswer ? 'Zmień typ' : 'Oddaj typ'}
              </button>
            )}
          </div>
        )}
        {question.is_open && (
          <p className="text-xs text-gray-400 mt-2">
            Typy innych graczy zobaczysz po terminie. Swój typ możesz zmieniać do końca terminu.
          </p>
        )}
      </div>

      {/* everybody's answers after the deadline */}
      {!question.is_open && (
        <div className="mt-4">
          <p className="text-xs uppercase tracking-wider text-gray-400 mb-2">Typy graczy</p>
          <LeagueBonusAnswersTable answers={question.answers} resolved={resolvedTeams.length > 0} />
        </div>
      )}

      {/* owner: delete before the deadline, inline confirm */}
      {isOwner && question.is_open && (
        <div className="mt-4 pt-4 border-t border-surface-500/20">
          {confirmingDelete ? (
            <div className="flex items-center gap-3 flex-wrap" role="alert">
              <p className="text-sm text-red-300 flex-1 min-w-[12rem]">
                Usunąć to pytanie? Odpowiedzi graczy też znikną.
              </p>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="text-sm px-3 py-1.5 rounded-lg bg-red-500/20 border border-red-500/40 text-red-300 hover:bg-red-500/30 transition-colors disabled:opacity-50"
              >
                {deleting ? 'Usuwam…' : 'Tak, usuń'}
              </button>
              <button
                type="button"
                onClick={() => setConfirmingDelete(false)}
                disabled={deleting}
                className="text-sm text-gray-400 hover:text-gray-300 transition-colors"
              >
                Anuluj
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              className="text-sm text-gray-400 hover:text-red-400 transition-colors"
            >
              Usuń pytanie
            </button>
          )}
        </div>
      )}
    </article>
  );
}
