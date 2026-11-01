const LABELS = {
  season: 'Sezon',
  window: 'Okno meczów',
  rescore: 'Korekty',
};

// Polish name of a sync run kind
export default function AdminRunKind({ kind }) {
  return <>{LABELS[kind] || kind}</>;
}
