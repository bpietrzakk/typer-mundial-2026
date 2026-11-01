// "po dogrywce 2:1" / "karne 4:3" under the 90 min score
export default function MatchExtraResult({ match }) {
  const { decided_by, home_goals_et, away_goals_et, home_pens, away_pens } = match;
  if (decided_by === 'extra_time' && home_goals_et != null) {
    return <p className="text-[11px] text-gray-400 mt-0.5">po dogrywce {home_goals_et}:{away_goals_et}</p>;
  }
  if (decided_by === 'penalties' && home_pens != null) {
    return (
      <p className="text-[11px] text-gray-400 mt-0.5">
        {home_goals_et != null && <>po dogrywce {home_goals_et}:{away_goals_et} · </>}
        karne {home_pens}:{away_pens}
      </p>
    );
  }
  return null;
}
