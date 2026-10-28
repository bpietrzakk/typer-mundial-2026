// centered card for "nothing here" states, icon is a calendar by default
export default function EmptyState({ title, text, children }) {
  return (
    <div className="glass-card p-10 text-center">
      <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-surface-700/50 flex items-center justify-center">
        <svg className="w-7 h-7 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 9v7.5" />
        </svg>
      </div>
      <p className="text-gray-200 font-semibold mb-1">{title}</p>
      {text && <p className="text-gray-400 text-sm">{text}</p>}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
