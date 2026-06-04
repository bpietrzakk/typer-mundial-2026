import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, ProtectedRoute } from './context/AuthContext';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Register from './pages/Register';
import Matches from './pages/Matches';
import MyPredictions from './pages/MyPredictions';
import Ranking from './pages/Ranking';
import League from './pages/League';
import BonusPicks from './pages/BonusPicks';

// layout wrapper — navbar + page content for authenticated routes
function AppLayout({ children }) {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* public routes — no navbar */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* protected routes — with navbar */}
          <Route
            path="/matches"
            element={
              <ProtectedRoute>
                <AppLayout><Matches /></AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/predictions"
            element={
              <ProtectedRoute>
                <AppLayout><MyPredictions /></AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/ranking"
            element={
              <ProtectedRoute>
                <AppLayout><Ranking /></AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/leagues"
            element={
              <ProtectedRoute>
                <AppLayout><League /></AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/leagues/:id"
            element={
              <ProtectedRoute>
                <AppLayout><League /></AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/bonus"
            element={
              <ProtectedRoute>
                <AppLayout><BonusPicks /></AppLayout>
              </ProtectedRoute>
            }
          />

          {/* catch-all — redirect to matches */}
          <Route path="*" element={<Navigate to="/matches" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
