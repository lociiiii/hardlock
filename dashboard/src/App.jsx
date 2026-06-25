import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Apps from './pages/Apps';
import AppDetail from './pages/AppDetail';
import Logs from './pages/Logs';

export default function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/apps" replace /> : <Login />}
      />
      <Route element={<ProtectedRoute />}>
        <Route path="/apps" element={<Apps />} />
        <Route path="/apps/:id" element={<AppDetail />} />
        <Route path="/logs" element={<Logs />} />
      </Route>
      <Route path="*" element={<Navigate to="/apps" replace />} />
    </Routes>
  );
}
