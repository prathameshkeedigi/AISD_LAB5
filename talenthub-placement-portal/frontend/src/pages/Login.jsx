import { GraduationCap, LogIn } from 'lucide-react';
import { useState } from 'react';
import api from '../api.js';

const DEMO_ACCOUNTS = [
  { label: 'Student - Rahul Sharma', email: 'rahul@student.talenthub.edu' },
  { label: 'Student - Priya Nair', email: 'priya@student.talenthub.edu' },
  { label: 'Company - ABC Technologies', email: 'hr@abctech.com' },
  { label: 'Company - XYZ Corp', email: 'hr@xyzcorp.com' },
  { label: 'Coordinator', email: 'coordinator@talenthub.edu' },
];

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('rahul@student.talenthub.edu');
  const [password, setPassword] = useState('password123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { data } = await api.post('/auth/login', { email, password });
      onLogin(data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Login failed. Check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-slate-800 border border-slate-700 rounded-xl p-8 space-y-6">
        <div className="flex items-center gap-2 text-indigo-400">
          <GraduationCap className="w-8 h-8" />
          <div>
            <h1 className="text-2xl font-bold">TalentHub</h1>
            <p className="text-xs text-slate-400">Campus Placement Management System</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm text-slate-400">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 outline-none focus:border-indigo-500"
              required
            />
          </div>
          <div>
            <label className="text-sm text-slate-400">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 outline-none focus:border-indigo-500"
              required
            />
          </div>

          {error && <p className="text-sm text-rose-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg py-2.5 font-medium"
          >
            <LogIn className="w-4 h-4" /> {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="border-t border-slate-700 pt-4">
          <p className="text-xs text-slate-500 mb-2">Demo accounts (password: password123)</p>
          <div className="flex flex-wrap gap-2">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.email}
                type="button"
                onClick={() => {
                  setEmail(acc.email);
                  setPassword('password123');
                }}
                className="text-xs px-2 py-1 bg-slate-900 border border-slate-700 rounded-md hover:border-indigo-500 text-slate-300"
              >
                {acc.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
