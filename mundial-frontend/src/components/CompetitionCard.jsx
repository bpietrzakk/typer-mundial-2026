import { Link } from 'react-router-dom';
import CompetitionBadge from './CompetitionBadge';
import FollowButton from './FollowButton';
import { SEASON_STATUS_LABELS, isArchiveCompetition } from '../utils/matchUi';

const KIND_LABELS = {
  league: 'Liga',
  cup: 'Puchar',
  national_cup: 'Turniej reprezentacji',
};

const STATUS_CLS = {
  active: 'bg-brand/10 text-brand border-brand/30',
  upcoming: 'bg-surface-600/40 text-gray-300 border-surface-500/30',
  archived: 'bg-surface-600/40 text-gray-400 border-surface-500/30',
};

// competition card: logo tile, season, follow toggle, links
export default function CompetitionCard({ competition, busy, onToggleFollow }) {
  const { id, code, name, country, kind, logo_url: logoUrl, is_followed: followed, current_season: season } = competition;
  const archive = isArchiveCompetition(competition);
  const seasonQuery = season ? `&season=${season.id}` : '';

  return (
    <div className={`glass-card p-5 flex flex-col gap-4 ${followed && !archive ? '!border-brand/40' : ''}`}>
      <div className="flex items-start gap-4">
        <CompetitionBadge code={code} name={name} logoUrl={logoUrl} size="lg" />
        <div className="min-w-0 flex-1">
          <h3 className="text-lg font-bold text-gray-100 leading-tight">{name}</h3>
          <p className="text-sm text-gray-500 mt-0.5">
            {[country, KIND_LABELS[kind]].filter(Boolean).join(' · ')}
          </p>
          {season && (
            <p className="flex items-center gap-2 mt-2 text-sm text-gray-400">
              Sezon {season.label}
              <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wider ${STATUS_CLS[season.status] || STATUS_CLS.archived}`}>
                {SEASON_STATUS_LABELS[season.status] || season.status}
              </span>
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center flex-wrap gap-x-4 gap-y-2 pt-3 border-t border-surface-500/20 text-sm">
        <Link
          to={`/matches?competition=${id}${seasonQuery}`}
          className="font-semibold text-brand hover:text-brand/80 transition-colors whitespace-nowrap"
        >
          Mecze →
        </Link>
        {season && (
          <Link
            to={`/ranking?competition=${id}${seasonQuery}`}
            className="font-semibold text-gray-400 hover:text-gray-200 transition-colors whitespace-nowrap"
          >
            Ranking
          </Link>
        )}
        {code === 'WC' && (
          <Link to="/bonus" className="font-semibold text-gray-400 hover:text-gray-200 transition-colors whitespace-nowrap">
            Bonusy
          </Link>
        )}
        {!archive && (
          <div className="ml-auto">
            <FollowButton followed={followed} busy={busy} onClick={() => onToggleFollow(competition)} name={name} />
          </div>
        )}
      </div>
    </div>
  );
}
