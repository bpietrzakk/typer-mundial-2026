// last results as small coloured dots: W = win, R = draw, P = loss (newest first)
const DOT = {
  W: { cls: 'bg-emerald-500/90 text-emerald-950', label: 'wygrana' },
  R: { cls: 'bg-gray-400/80 text-gray-900', label: 'remis' },
  P: { cls: 'bg-red-500/90 text-red-950', label: 'porażka' },
};

export default function FormDots({ form }) {
  if (!form?.length) return <span className="text-[11px] text-gray-500">brak meczów</span>;
  const label = `Forma od najnowszego: ${form.map((f) => DOT[f]?.label ?? f).join(', ')}`;
  return (
    <span className="inline-flex items-center gap-[3px]" role="img" aria-label={label} title={label}>
      {form.map((f, i) => (
        <span
          key={i}
          aria-hidden="true"
          className={`w-4 h-4 rounded-full text-[9px] font-black leading-4 text-center ${DOT[f]?.cls ?? 'bg-surface-500'}`}
        >
          {f}
        </span>
      ))}
    </span>
  );
}
