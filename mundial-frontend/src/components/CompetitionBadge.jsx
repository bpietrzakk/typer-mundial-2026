import { competitionColor } from '../utils/matchUi';

// coloured code pill (EPL, UCL...) — stands in for a logo
export default function CompetitionBadge({ code, size = 'sm', className = '' }) {
  const sizes = {
    sm: 'px-2 py-0.5 text-[10px] rounded-md',
    lg: 'w-14 h-14 text-sm rounded-2xl',
  };
  return (
    <span
      className={`inline-flex items-center justify-center font-black tracking-wider border shrink-0
        ${sizes[size] || sizes.sm} ${competitionColor(code)} ${className}`}
    >
      {code}
    </span>
  );
}
