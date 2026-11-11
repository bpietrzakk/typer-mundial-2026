// "po dogrywce 2:1" / "karne 4:3" under (or next to) the 90 min score.
// inline = one span for the compact row's detail line
export default function MatchExtraResult({ match, inline = false }) {
  const { decided_by, home_goals_et, away_goals_et, home_pens, away_pens } = match;

  let text = null;
  if (decided_by === 'extra_time' && home_goals_et != null) {
    text = `po dogrywce ${home_goals_et}:${away_goals_et}`;
  } else if (decided_by === 'penalties' && home_pens != null) {
    text = `${home_goals_et != null ? `po dogrywce ${home_goals_et}:${away_goals_et} · ` : ''}karne ${home_pens}:${away_pens}`;
  }
  if (!text) return null;

  if (inline) return <span className="text-[11px] text-gray-400">{text}</span>;
  return <p className="text-[11px] text-gray-400 mt-0.5">{text}</p>;
}
