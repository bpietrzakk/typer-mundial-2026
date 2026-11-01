import { plural } from './plural';

// unit of a streak: league rounds or weekly coupons
export const ROUNDS = ['kolejka', 'kolejki', 'kolejek'];
export const WEEKS = ['tydzień', 'tygodnie', 'tygodni'];
export const streakForms = (unit) => (unit === 'coupon' ? WEEKS : ROUNDS);

const VALUE_FORMS = {
  exact_king: ['dokładny', 'dokładne', 'dokładnych'],
  contrarian: ['trafienie', 'trafienia', 'trafień'],
  grumbler: ['pudło', 'pudła', 'pudeł'],
};

// "5 dokładnych", "64%", "4 kolejki"
export function badgeValueLabel(badge, unit) {
  if (badge.code === 'prophet') return `${badge.value}%`;
  const forms = badge.code === 'streak' ? streakForms(unit) : VALUE_FORMS[badge.code];
  return forms ? `${badge.value} ${plural(badge.value, forms)}` : String(badge.value);
}
