import { Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import ErrorBoundary from './components/ErrorBoundary';
import Navbar from './components/Navbar';
import InstallPrompt from './components/InstallPrompt';
import PageFallback from './components/PageFallback';
import Matches from './pages/Matches';
import MyPredictions from './pages/MyPredictions';
import Ranking from './pages/Ranking';
import League from './pages/League';
import Settings from './pages/Settings';
import Dashboard from './pages/Dashboard';
import Competitions from './pages/Competitions';
import JoinByLink from './pages/JoinByLink';
import NotFound from './pages/NotFound';
import HomeRoute from './components/HomeRoute';
import ProtectedPage from './components/ProtectedPage';
import { lazyPage } from './utils/lazyPage';

// pages a logged in player rarely opens (or only once) load on demand,
// the everyday ones stay in the main bundle
const Login = lazyPage(() => import('./pages/Login'));
const Register = lazyPage(() => import('./pages/Register'));
const ForgotPassword = lazyPage(() => import('./pages/ForgotPassword'));
const ResetPassword = lazyPage(() => import('./pages/ResetPassword'));
const VerifyEmail = lazyPage(() => import('./pages/VerifyEmail'));
const VerifyPending = lazyPage(() => import('./pages/VerifyPending'));
const Landing = lazyPage(() => import('./pages/Landing'));
const Welcome = lazyPage(() => import('./pages/Welcome'));
const Rules = lazyPage(() => import('./pages/Rules'));
const BonusPicks = lazyPage(() => import('./pages/BonusPicks'));
const Admin = lazyPage(() => import('./pages/Admin'));

// layout wrapper — navbar + page content for authenticated routes.
// the navbar stays while a lazy page loads
function AppLayout({ children }) {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Suspense fallback={<PageFallback />}>{children}</Suspense>
      </main>
      <InstallPrompt />
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
    <BrowserRouter>
      <AuthProvider>
      <ToastProvider>
        {/* pages without the layout (auth, landing, welcome) */}
        <Suspense fallback={<PageFallback />}>
        <Routes>
          {/* public routes — no navbar */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/verify-pending" element={<VerifyPending />} />

          {/* start: landing page for guests, dashboard when logged in */}
          <Route
            path="/"
            element={
              <HomeRoute guest={<Landing />}>
                <AppLayout><Dashboard /></AppLayout>
              </HomeRoute>
            }
          />

          {/* protected routes — with navbar */}
          <Route
            path="/matches"
            element={
              <ProtectedPage>
                <AppLayout><Matches /></AppLayout>
              </ProtectedPage>
            }
          />
          <Route
            path="/predictions"
            element={
              <ProtectedPage>
                <AppLayout><MyPredictions /></AppLayout>
              </ProtectedPage>
            }
          />
          <Route
            path="/ranking"
            element={
              <ProtectedPage>
                <AppLayout><Ranking /></AppLayout>
              </ProtectedPage>
            }
          />
          <Route
            path="/competitions"
            element={
              <ProtectedPage>
                <AppLayout><Competitions /></AppLayout>
              </ProtectedPage>
            }
          />
          <Route
            path="/leagues"
            element={
              <ProtectedPage>
                <AppLayout><League /></AppLayout>
              </ProtectedPage>
            }
          />
          <Route
            path="/leagues/:id"
            element={
              <ProtectedPage>
                <AppLayout><League /></AppLayout>
              </ProtectedPage>
            }
          />
          {/* old Mundial bonus picks — read-only archive page */}
          <Route
            path="/bonus"
            element={
              <ProtectedPage>
                <AppLayout><BonusPicks /></AppLayout>
              </ProtectedPage>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedPage>
                <AppLayout><Admin /></AppLayout>
              </ProtectedPage>
            }
          />

          <Route
            path="/settings"
            element={
              <ProtectedPage>
                <AppLayout><Settings /></AppLayout>
              </ProtectedPage>
            }
          />
          <Route
            path="/rules"
            element={
              <ProtectedPage>
                <AppLayout><Rules /></AppLayout>
              </ProtectedPage>
            }
          />
          {/* onboarding after sign-up without an invite — no navbar, full focus */}
          <Route
            path="/witaj"
            element={
              <ProtectedPage>
                <Welcome />
              </ProtectedPage>
            }
          />
          <Route
            path="/join/:code"
            element={
              <ProtectedPage>
                <AppLayout><JoinByLink /></AppLayout>
              </ProtectedPage>
            }
          />
          {/* anything else */}
          <Route path="*" element={<NotFound />} />
        </Routes>
        </Suspense>
      </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
    </ErrorBoundary>
  );
}
