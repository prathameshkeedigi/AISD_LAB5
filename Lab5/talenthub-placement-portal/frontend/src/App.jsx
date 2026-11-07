import { useEffect, useState } from 'react';
import Header from './components/Header.jsx';
import CompanyDashboard from './pages/CompanyDashboard.jsx';
import CoordinatorDashboard from './pages/CoordinatorDashboard.jsx';
import Login from './pages/Login.jsx';
import StudentDashboard from './pages/StudentDashboard.jsx';

export default function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const stored = localStorage.getItem('talenthub_user');
    if (stored) setUser(JSON.parse(stored));
  }, []);

  const handleLogin = (data) => {
    localStorage.setItem('talenthub_token', data.access_token);
    localStorage.setItem('talenthub_user', JSON.stringify(data));
    setUser(data);
  };

  const handleLogout = () => {
    localStorage.removeItem('talenthub_token');
    localStorage.removeItem('talenthub_user');
    setUser(null);
  };

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans p-6">
      <Header user={user} onLogout={handleLogout} />
      <main className="max-w-5xl mx-auto">
        {user.role === 'STUDENT' && <StudentDashboard />}
        {user.role === 'COMPANY_REP' && <CompanyDashboard />}
        {user.role === 'COORDINATOR' && <CoordinatorDashboard />}
      </main>
    </div>
  );
}
