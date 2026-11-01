// Polish plurals: 1 gracz, 2-4 gracze, 5+ graczy (12-14 and 0 use the "many" form)
// index of the form to use: 0 = one, 1 = few, 2 = many
export function pluralIndex(n) {
  const last = n % 10;
  const lastTwo = n % 100;
  if (n === 1) return 0;
  if (last >= 2 && last <= 4 && !(lastTwo >= 12 && lastTwo <= 14)) return 1;
  return 2;
}

export const plural = (n, forms) => forms[pluralIndex(n)];

export const PLAYERS = ['gracz', 'gracze', 'graczy'];
export const TIPS = ['typ', 'typy', 'typów'];
export const MATCHES = ['mecz', 'mecze', 'meczów'];

// "3 gracze"
export const countOf = (n, forms) => `${n} ${plural(n, forms)}`;
