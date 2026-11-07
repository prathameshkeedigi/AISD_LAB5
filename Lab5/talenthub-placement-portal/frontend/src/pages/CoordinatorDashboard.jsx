import { BarChart3 } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api.js';
import StatusBadge from '../components/StatusBadge.jsx';

export default function CoordinatorDashboard() {
  const [stats, setStats] = useState(null);
  const [applications, setApplications] = useState([]);

  useEffect(() => {
    const load = async () => {
      const [statsRes, appsRes] = await Promise.all([api.get('/coordinator/stats'), api.get('/coordinator/applications')]);
      setStats(statsRes.data);
      setApplications(appsRes.data);
    };
    load();
  }, []);

  if (!stats) return <p className="text-slate-400">Loading...</p>;

  const cards = [
    { label: 'Total Students', value: stats.total_students, color: 'text-indigo-400' },
    { label: 'Total Companies', value: stats.total_companies, color: 'text-indigo-400' },
    { label: 'Active Job Drives', value: stats.total_jobs, color: 'text-amber-400' },
    { label: 'Total Applications', value: stats.total_applications, color: 'text-slate-200' },
    { label: 'Offers Issued', value: stats.total_offers, color: 'text-emerald-400' },
    { label: 'Placement %', value: `${stats.placement_percentage}%`, color: 'text-emerald-400' },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
        <div className="flex items-center gap-2 text-indigo-400 text-xl font-semibold mb-4">
          <BarChart3 /> Placement Coordinator Analytics
        </div>
        <div className="grid grid-cols-3 gap-4">
          {cards.map((c) => (
            <div key={c.label} className="bg-slate-900 p-4 rounded-lg text-center">
              <div className={`text-3xl font-bold ${c.color}`}>{c.value}</div>
              <div className="text-xs text-slate-400 mt-1">{c.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
        <h3 className="font-semibold text-lg mb-4">All Applications</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-400 border-b border-slate-700">
                <th className="py-2">Student</th>
                <th className="py-2">Company</th>
                <th className="py-2">Role</th>
                <th className="py-2">Status</th>
                <th className="py-2">Offer</th>
              </tr>
            </thead>
            <tbody>
              {applications.map((a) => (
                <tr key={a.id} className="border-b border-slate-800">
                  <td className="py-2">{a.student_name}</td>
                  <td className="py-2">{a.company_name}</td>
                  <td className="py-2">{a.job_title}</td>
                  <td className="py-2"><StatusBadge status={a.status} /></td>
                  <td className="py-2">{a.offer ? `${a.offer.package_lpa} LPA` : '-'}</td>
                </tr>
              ))}
              {applications.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-slate-400">
                    No applications yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
