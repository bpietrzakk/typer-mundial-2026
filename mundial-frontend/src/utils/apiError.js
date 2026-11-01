// readable Polish messages for failed API calls

const FIELD_LABELS = {
  deadline_at: 'Termin',
  points: 'Punkty',
  season_id: 'Sezon',
  team_id: 'Drużyna',
  kind: 'Rodzaj pytania',
  competition_ids: 'Rozgrywki',
  competition_code: 'Rozgrywka',
  is_active: 'Aktywność',
  prize_pool_per_person: 'Pula nagród',
  name: 'Nazwa',
  join_code: 'Kod zaproszenia',
};

// pydantic error type -> short Polish text, ctx holds the limit (le / ge / lt / gt / min_length ...)
const TYPE_MESSAGES = {
  missing: () => 'to pole jest wymagane',
  int_type: () => 'musi być liczbą całkowitą',
  int_parsing: () => 'musi być liczbą całkowitą',
  int_from_float: () => 'musi być liczbą całkowitą',
  float_type: () => 'musi być liczbą',
  float_parsing: () => 'musi być liczbą',
  bool_type: () => 'nieprawidłowa wartość',
  datetime_type: () => 'nieprawidłowa data',
  datetime_parsing: () => 'nieprawidłowa data',
  datetime_from_date_parsing: () => 'nieprawidłowa data',
  less_than_equal: (ctx) => `musi być nie większe niż ${ctx?.le}`,
  less_than: (ctx) => `musi być mniejsze niż ${ctx?.lt}`,
  greater_than_equal: (ctx) => `musi być nie mniejsze niż ${ctx?.ge}`,
  greater_than: (ctx) => `musi być większe niż ${ctx?.gt}`,
  string_too_short: (ctx) => `jest za krótkie (min. ${ctx?.min_length} znaków)`,
  string_too_long: (ctx) => `jest za długie (max ${ctx?.max_length} znaków)`,
};

function formatValidationItem(item) {
  const loc = Array.isArray(item?.loc) ? item.loc : [];
  // loc looks like ['body', 'competition_ids', 0] — take the last field name
  const field = [...loc].reverse().find((part) => typeof part === 'string' && part !== 'body');
  const label = FIELD_LABELS[field] || field || '';
  const makeText = TYPE_MESSAGES[item?.type];
  const text = makeText ? makeText(item?.ctx) : 'nieprawidłowa wartość';
  return label ? `${label}: ${text}` : text;
}

// readable text for an axios error: detail string, pydantic 422 list or fallback
export function apiErrorMessage(err, fallback = 'Coś poszło nie tak') {
  if (err?.code === 'ECONNABORTED') return 'Przekroczono czas oczekiwania na serwer';
  if (!err?.response) return 'Brak połączenia z serwerem';
  const detail = err.response.data?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map(formatValidationItem).join('; ');
  }
  return fallback;
}
