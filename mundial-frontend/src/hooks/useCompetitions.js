import { getCompetitions } from '../api/competitions';
import useAsync from './useAsync';

// list of competitions with follow flags — shared by many pages
export default function useCompetitions() {
  return useAsync(getCompetitions);
}
