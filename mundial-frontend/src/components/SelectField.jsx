// styled native select (native = best picker on phones)
export default function SelectField({ label, value, onChange, children, className = '', disabled = false }) {
  return (
    <label className={`block min-w-0 ${className}`}>
      {label && (
        <span className="block text-[10px] font-semibold uppercase tracking-widest text-gray-500 mb-1">
          {label}
        </span>
      )}
      <span className="relative block">
        <select
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="input-field !py-2.5 !pr-9 appearance-none cursor-pointer text-sm font-medium truncate disabled:opacity-60 disabled:cursor-default"
        >
          {children}
        </select>
        <svg
          className="w-4 h-4 text-gray-500 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none"
          fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2} aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </span>
    </label>
  );
}
