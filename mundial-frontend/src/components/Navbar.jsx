import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const NAV_LINKS = [
  {
    to: '/',
    label: 'Dom',
    exact: true,
    d: 'M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25',
  },
  {
    to: '/matches',
    label: 'Mecze',
    d: 'M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 9v7.5',
  },
  {
    to: '/predictions',
    label: 'Typy',
    d: 'M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z',
  },
  {
    to: '/ranking',
    label: 'Ranking',
    d: 'M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M7.73 9.728a6.726 6.726 0 002.748 1.35m8.272-6.842V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 012.916.52 6.003 6.003 0 01-5.395 4.972m0 0a6.726 6.726 0 01-2.749 1.35m0 0a6.772 6.772 0 01-3.044 0',
  },
  {
    to: '/leagues',
    label: 'Ligi',
    d: 'M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z',
  },
  {
    to: '/bonus',
    label: 'Bonusy',
    d: 'M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z',
  },
];

const ADMIN_LINK = {
  to: '/admin',
  label: 'Admin',
  d: 'M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75',
};

function NavIcon({ d }) {
  return (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d={d} />
    </svg>
  );
}

export default function Navbar() {
  const { user, logout, isLoggedIn } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const desktopLinks = user?.is_admin ? [...NAV_LINKS, ADMIN_LINK] : NAV_LINKS;
  const bottomNavLinks = NAV_LINKS;

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <>
      {/* top bar */}
      <nav className="sticky top-0 z-50 bg-surface-900/80 backdrop-blur-xl border-b border-surface-500/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">

            <Link to="/" className="flex items-center gap-2 group">
              <img src="/favicon.svg" alt="" className="w-8 h-8 rounded-lg shrink-0" />
              <span className="font-display font-bold text-xl tracking-wide gradient-text group-hover:opacity-80 transition-opacity">
                Mundial Typer
              </span>
            </Link>

            {/* desktop nav */}
            {isLoggedIn && (
              <div className="hidden md:flex items-center gap-1">
                {desktopLinks.map(({ to, label, exact }) => {
                  const active = exact ? location.pathname === to : location.pathname.startsWith(to);
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
                      {label}
                    </Link>
                  );
                })}
              </div>
            )}

            <div className="flex items-center gap-3">
              {isLoggedIn ? (
                <>
                  {/* admin shortcut visible only on mobile */}
                  {user?.is_admin && (
                    <Link
                      to="/admin"
                      className="md:hidden text-xs font-semibold px-2 py-1 rounded-lg text-mundial-red bg-mundial-red/10 hover:bg-mundial-red/20 transition-colors"
                    >
                      Admin
                    </Link>
                  )}
                  <span className="hidden sm:inline text-sm text-gray-400">{user?.nick}</span>
                  <Link
                    to="/settings"
                    aria-label="Ustawienia"
                    className="p-1.5 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-surface-700/30 transition-colors"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" />
                    </svg>
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="text-sm text-gray-400 hover:text-mundial-red transition-colors px-3 py-1.5 rounded-lg hover:bg-surface-700/30"
                  >
                    Wyloguj
                  </button>
                </>
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
            </div>

          </div>
        </div>
      </nav>

      {/* mobile bottom nav */}
      {isLoggedIn && (
        <nav
          className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-surface-900/95 backdrop-blur-xl border-t border-surface-500/20"
          style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
        >
          <div className="flex items-stretch">
            {bottomNavLinks.map(({ to, label, d, exact }) => {
              const active = exact ? location.pathname === to : location.pathname.startsWith(to);
              return (
                <Link
                  key={to}
                  to={to}
                  className={`relative flex-1 flex flex-col items-center justify-center gap-1 py-2.5 transition-colors min-h-[56px]
                    ${active ? 'text-mundial-teal' : 'text-gray-500 active:text-gray-300'}`}
                >
                  {active && (
                    <span className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-mundial-teal rounded-full" />
                  )}
                  <NavIcon d={d} />
                  <span className="text-[10px] font-medium leading-none">{label}</span>
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </>
  );
}
