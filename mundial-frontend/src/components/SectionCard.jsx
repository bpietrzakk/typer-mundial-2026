import { Link } from 'react-router-dom';

// card with a title row and an optional "see all" link
export default function SectionCard({ title, link, linkLabel, children }) {
  return (
    <div className="glass-card overflow-hidden">
      <div className="px-5 py-4 border-b border-surface-500/20 flex items-center justify-between">
        <h2 className="font-semibold text-gray-200">{title}</h2>
        {link && (
          <Link to={link} className="text-xs text-mundial-teal hover:text-mundial-teal/80 transition-colors">
            {linkLabel}
          </Link>
        )}
      </div>
      {children}
    </div>
  );
}
