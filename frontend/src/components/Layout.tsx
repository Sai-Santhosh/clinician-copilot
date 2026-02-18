import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import clsx from 'clsx';

export default function Layout() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div style={{ marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--color-primary)' }}>
            Clinician Copilot
          </h1>
          <p style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem' }}>
            AI-Powered Documentation
          </p>
        </div>

        <nav>
          <NavLink
            to="/patients"
            className={({ isActive }) => clsx('nav-item', isActive && 'active')}
          >
            Patients
          </NavLink>

          {user?.role === 'admin' && (
            <NavLink
              to="/audit"
              className={({ isActive }) => clsx('nav-item', isActive && 'active')}
            >
              Audit Logs
            </NavLink>
          )}
        </nav>

        <div style={{ marginTop: 'auto', paddingTop: '2rem', borderTop: '1px solid var(--color-border)' }}>
          <div style={{ marginBottom: '1rem' }}>
            <p style={{ fontSize: '0.875rem', fontWeight: 500 }}>{user?.email}</p>
            <span className={clsx('badge', {
              'badge-info': user?.role === 'admin',
              'badge-success': user?.role === 'clinician',
              'badge-warning': user?.role === 'viewer',
            })}>
              {user?.role}
            </span>
          </div>
          <button className="btn btn-outline" onClick={handleLogout} style={{ width: '100%' }}>
            Logout
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
