import { GraduationCap, LogOut } from 'lucide-react';

export default function Header({ user, onLogout }) {
  return (
    <header className="max-w-5xl mx-auto flex justify-between items-center border-b border-slate-800 pb-4 mb-8">
      <div className="flex items-center gap-2">
        <GraduationCap className="w-7 h-7 text-indigo-400" />
        <div>
          <h1 className="text-2xl font-bold text-indigo-400">TalentHub</h1>
          <p className="text-sm text-slate-400">Campus Placement Management System</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <div className="text-sm font-medium">{user.name}</div>
          <div className="text-xs text-slate-400 capitalize">{user.role.toLowerCase()}</div>
        </div>
        <button
          onClick={onLogout}
          className="flex items-center gap-1 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm text-slate-300"
        >
          <LogOut className="w-4 h-4" /> Logout
        </button>
      </div>
    </header>
  );
}
