import { Briefcase, CheckCircle2, GraduationCap, XCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api.js';
import StatusBadge from '../components/StatusBadge.jsx';

export default function StudentDashboard() {
  const [profile, setProfile] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [applications, setApplications] = useState([]);
  const [message, setMessage] = useState(null);

  const loadAll = async () => {
    const [profileRes, jobsRes, appsRes] = await Promise.all([
      api.get('/students/me'),
      api.get('/jobs'),
      api.get('/applications/me'),
    ]);
    setProfile(profileRes.data);
    setJobs(jobsRes.data);
    setApplications(appsRes.data);
  };

  useEffect(() => {
    loadAll();
  }, []);

  const appliedJobIds = new Set(applications.map((a) => a.job_id));

  const apply = async (jobId) => {
    setMessage(null);
    try {
      await api.post('/applications', { job_id: jobId });
      setMessage({ ok: true, text: 'Application submitted successfully!' });
      await loadAll();
    } catch (err) {
      setMessage({ ok: false, text: err?.response?.data?.detail || 'Could not submit application.' });
    }
  };

  const respondToOffer = async (applicationId, accept) => {
    await api.patch(`/offers/${applicationId}/respond`, { accept });
    await loadAll();
  };

  if (!profile) return <p className="text-slate-400">Loading...</p>;

  return (
    <div className="space-y-6">
      <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 space-y-4">
        <div className="flex items-center gap-2 text-indigo-400 text-xl font-semibold">
          <GraduationCap /> Student Portal ({profile.name})
        </div>
        <div className="grid grid-cols-3 gap-4 text-sm bg-slate-900/50 p-4 rounded-lg">
          <div><span className="text-slate-400">Branch:</span> {profile.branch}</div>
          <div><span className="text-slate-400">CGPA:</span> {profile.cgpa}</div>
          <div><span className="text-slate-400">Active Backlogs:</span> {profile.active_backlogs}</div>
        </div>
      </div>

      {message && (
        <div
          className={`p-4 rounded-lg flex items-center gap-3 ${
            message.ok
              ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
              : 'bg-rose-950/80 text-rose-300 border border-rose-800'
          }`}
        >
          {message.ok ? <CheckCircle2 /> : <XCircle />}
          <span>{message.text}</span>
        </div>
      )}

      <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
        <h3 className="font-semibold text-lg flex items-center gap-2 mb-4">
          <Briefcase className="w-5 h-5 text-indigo-400" /> Job Listings
        </h3>
        <div className="space-y-3">
          {jobs.map((job) => (
            <div key={job.id} className="bg-slate-900 p-4 rounded-lg flex justify-between items-center">
              <div>
                <div className="font-medium">{job.company_name} - {job.role_title}</div>
                <div className="text-xs text-slate-400 mt-1">
                  Package: {job.package_lpa} LPA | Min CGPA: {job.min_cgpa} | Max Backlogs: {job.max_backlogs}
                </div>
                {!job.eligible && <div className="text-xs text-rose-400 mt-1">{job.reason}</div>}
              </div>
              {appliedJobIds.has(job.id) ? (
                <span className="text-xs text-slate-400 px-3 py-1.5">Already Applied</span>
              ) : (
                <button
                  onClick={() => apply(job.id)}
                  disabled={!job.eligible}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-white text-sm font-medium"
                >
                  Apply
                </button>
              )}
            </div>
          ))}
          {jobs.length === 0 && <p className="text-slate-400 text-sm">No job listings available yet.</p>}
        </div>
      </div>

      <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
        <h3 className="font-semibold text-lg mb-4">My Applications</h3>
        <div className="space-y-3">
          {applications.map((a) => (
            <div key={a.id} className="bg-slate-900 p-4 rounded-lg space-y-2">
              <div className="flex justify-between items-center">
                <div>
                  <div className="font-medium">{a.company_name} - {a.job_title}</div>
                  <div className="text-xs text-slate-400">Applied {new Date(a.applied_at).toLocaleDateString()}</div>
                </div>
                <StatusBadge status={a.status} />
              </div>
              {a.interview && (
                <div className="text-xs text-slate-400">
                  Interview: {new Date(a.interview.scheduled_at).toLocaleString()} —{' '}
                  <StatusBadge status={a.interview.result} />
                </div>
              )}
              {a.offer && a.status === 'OFFERED' && (
                <div className="flex items-center gap-3 pt-1">
                  <span className="text-xs text-slate-300">Offer: {a.offer.package_lpa} LPA</span>
                  <button
                    onClick={() => respondToOffer(a.id, true)}
                    className="px-3 py-1 bg-emerald-700 hover:bg-emerald-600 rounded-md text-xs font-medium"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => respondToOffer(a.id, false)}
                    className="px-3 py-1 bg-rose-800 hover:bg-rose-700 rounded-md text-xs font-medium"
                  >
                    Decline
                  </button>
                </div>
              )}
            </div>
          ))}
          {applications.length === 0 && <p className="text-slate-400 text-sm">You haven't applied to any jobs yet.</p>}
        </div>
      </div>
    </div>
  );
}
