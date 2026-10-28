import { useAuth } from '../context/AuthContext';
import LeagueTeamLabel from './LeagueTeamLabel';

// everybody's answers to a bonus question — shown only after the deadline
export default function LeagueBonusAnswersTable({ answers, resolved }) {
  const { user } = useAuth();

  if (answers.length === 0) {
    return <p className="text-sm text-gray-400">Nikt nie oddał typu na to pytanie.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-surface-500/20">
      <table className="w-full text-sm">
        <caption className="sr-only">Odpowiedzi graczy na pytanie bonusowe</caption>
        <thead>
          <tr className="text-left text-xs uppercase tracking-wider text-gray-400 border-b border-surface-500/20">
            <th scope="col" className="px-3 py-2">Gracz</th>
            <th scope="col" className="px-3 py-2">Typ</th>
            <th scope="col" className="px-3 py-2 text-right">Punkty</th>
          </tr>
        </thead>
        <tbody>
          {answers.map((answer) => {
            const isMe = user && answer.user_id === user.id;
            const points = answer.points_awarded;
            return (
              <tr
                key={answer.user_id}
                className={`border-b border-surface-500/10 last:border-0 ${isMe ? 'bg-mundial-teal/10' : ''}`}
              >
                <td className={`px-3 py-2 font-medium ${isMe ? 'text-mundial-teal' : 'text-gray-200'}`}>
                  {answer.nick}
                  {isMe && <span className="ml-2 text-xs text-mundial-teal/70">(Ty)</span>}
                </td>
                <td className="px-3 py-2 text-gray-300 max-w-[12rem]">
                  <LeagueTeamLabel team={answer.team} />
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {points == null ? (
                    <span className="text-gray-400" title={resolved ? '' : 'Czeka na rozstrzygnięcie'}>—</span>
                  ) : points > 0 ? (
                    <span className="points-exact">+{points}</span>
                  ) : (
                    <span className="text-gray-400 font-semibold">0</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
