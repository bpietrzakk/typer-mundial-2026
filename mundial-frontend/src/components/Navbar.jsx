import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const NAV_LINKS = [
  { to: '/matches', label: 'Mecze', icon: '⚽' },
  { to: '/predictions', label: 'Moje Typy', icon: '🎯' },
  { to: '/ranking', label: 'Ranking', icon: '🏆' },
  { to: '/leagues', label: 'Ligi', icon: '👥' },
  { to: '/bonus', label: 'Bonusy', icon: '⭐' },
];

export default function Navbar() {
  const { user, logout, isLoggedIn } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  // admins get an extra link to the panel
  const links = user?.is_admin
    ? [...NAV_LINKS, { to: '/admin', label: 'Admin', icon: '🛠️' }]
    : NAV_LINKS;

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav className="sticky top-0 z-50 bg-surface-900/80 backdrop-blur-xl border-b border-surface-500/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* logo */}
          <Link to="/matches" className="flex items-center gap-2 group">
            <span className="text-2xl">🏟️</span>
            <span className="font-extrabold text-lg gradient-text group-hover:opacity-80 transition-opacity">
              Mundial Typer
            </span>
          </Link>

          {/* desktop nav links */}
          {isLoggedIn && (
            <div className="hidden md:flex items-center gap-1">
              {links.map(({ to, label, icon }) => {
                const active = location.pathname.startsWith(to);
                return (
                  <Link
                    key={to}
                    to={to}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200
                      ${active
                        ? 'bg-surface-700/60 text-white'
                        : 'text-gray-400 hover:text-gray-200 hover:bg-surface-700/30'
                      }`}
                  >
                    <span className="mr-1.5">{icon}</span>
                    {label}
                  </Link>
                );
              })}
            </div>
          )}

          {/* right side — user menu or login link */}
          <div className="flex items-center gap-3">
            {isLoggedIn ? (
              <div className="flex items-center gap-3">
                <span className="hidden sm:inline text-sm text-gray-400">
                  {user?.nick}
                </span>
                <button
                  onClick={handleLogout}
                  className="text-sm text-gray-400 hover:text-mundial-magenta transition-colors px-3 py-1.5 rounded-lg hover:bg-surface-700/30"
                >
                  Wyloguj
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="text-sm text-gray-400 hover:text-white transition-colors px-3 py-1.5"
                >
                  Zaloguj
                </Link>
                <Link to="/register" className="btn-primary text-sm !px-4 !py-2">
                  Rejestracja
                </Link>
              </div>
            )}

            {/* mobile hamburger */}
            {isLoggedIn && (
              <button
                onClick={() => setMobileOpen(!mobileOpen)}
                className="md:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-surface-700/30 transition-colors"
                aria-label="Menu"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {mobileOpen ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  )}
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* mobile menu dropdown */}
      {isLoggedIn && mobileOpen && (
        <div className="md:hidden border-t border-surface-500/20 bg-surface-900/95 backdrop-blur-xl animate-slide-up">
          <div className="px-4 py-3 space-y-1">
            {links.map(({ to, label, icon }) => {
              const active = location.pathname.startsWith(to);
              return (
                <Link
                  key={to}
                  to={to}
                  onClick={() => setMobileOpen(false)}
                  className={`block px-4 py-3 rounded-lg text-sm font-medium transition-all
                    ${active
                      ? 'bg-surface-700/60 text-white'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-surface-700/30'
                    }`}
                >
                  <span className="mr-2">{icon}</span>
                  {label}
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </nav>
  );
}
