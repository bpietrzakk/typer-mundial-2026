import { getCompetitions } from '../api/competitions';
import useAsync from './useAsync';

// list of competitions with the in_my_leagues flag — shared by many pages
export default function useCompetitions() {
  return useAsync(getCompetitions);
}
