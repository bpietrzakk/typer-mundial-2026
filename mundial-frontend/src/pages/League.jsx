import { useParams } from 'react-router-dom';
import LeagueDetail from '../components/LeagueDetail';
import LeagueList from '../components/LeagueList';

export default function League() {
  const { id } = useParams();

  // no :id in the URL = list of my leagues, with :id = league detail
  // key remounts the detail view when switching between leagues
  return id ? <LeagueDetail key={id} leagueId={id} /> : <LeagueList />;
}
