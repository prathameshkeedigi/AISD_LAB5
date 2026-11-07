import { Building2, Plus } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../api.js';
import StatusBadge from '../components/StatusBadge.jsx';

const EMPTY_JOB = { role_title: '', description: '', package_lpa: 0, min_cgpa: 0, max_backlogs: 0, drive_date: '', allowed_branches: '' };

export default function CompanyDashboard() {
  const [jobs, setJobs] = useState([]);
  const [applications, setApplications] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [newJob, setNewJob] = useState(EMPTY_JOB);
  const [offerDrafts, setOfferDrafts] = useState({});
  const [interviewDrafts, setInterviewDrafts] = useState({});
  const [venueDrafts, setVenueDrafts] = useState({});
  const [error, setError] = useState('');

  // Show the backend's plain-language reason (NFR-7.1) instead of failing silently
  const run = async (fn) => {
    setError('');
    try {
      await fn();
    } catch (err) {
      setError(err.response?.data?.detail?.toString() || 'Request failed');
    }
  };

  const loadAll = async () => {
    const [jobsRes, appsRes] = await Promise.all([api.get('/jobs/mine'), api.get('/applications/company/mine')]);
    setJobs(jobsRes.data);
    setApplications(appsRes.data);
  };

  useEffect(() => {
    loadAll();
  }, []);

  const createJob = (e) => {
    e.preventDefault();
    return run(() => saveJob());
  };

  const saveJob = async () => {
    await api.post('/jobs', {
      ...newJob,
      package_lpa: parseFloat(newJob.package_lpa) || 0,
      min_cgpa: parseFloat(newJob.min_cgpa) || 0,
      max_backlogs: parseInt(newJob.max_backlogs) || 0,
      // Comma-separated branches (CSE, ECE, ISE, MECH, CIVIL); empty means a pool drive open to all branches
      allowed_branches: newJob.allowed_branches.split(',').map((b) => b.trim().toUpperCase()).filter(Boolean),
    });
    setNewJob(EMPTY_JOB);
    setShowForm(false);
    await loadAll();
  };

  const setAppStatus = async (applicationId, status) => {
    await api.patch(`/applications/${applicationId}/status`, { status });
    await loadAll();
  };

  const scheduleInterview = async (applicationId) => {
    const when = interviewDrafts[applicationId];
    if (!when) return;
    const venue = venueDrafts[applicationId] || 'To be announced';
    await api.post('/interviews/schedule', { application_id: applicationId, scheduled_at: new Date(when).toISOString(), venue });
    await loadAll();
  };

  const recordResult = async (applicationId, result) => {
    await api.patch(`/interviews/${applicationId}/result`, { result });
    await loadAll();
  };

  const issueOffer = async (applicationId) => {
    const pkg = parseFloat(offerDrafts[applicationId]);
    if (!pkg) return;
    await api.post('/offers', { application_id: applicationId, package_lpa: pkg });
    await loadAll();
  };

  return (
    <div className="space-y-6">
      {error && <div className="bg-rose-950/70 border border-rose-800 text-rose-200 text-sm rounded-lg px-4 py-2">{error}</div>}
      <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2 text-indigo-400 text-xl font-semibold">
            <Building2 /> Company Portal
          </div>
          <button
            onClick={() => setShowForm((s) => !s)}
            className="flex items-center gap-1 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium"
          >
            <Plus className="w-4 h-4" /> Post Job
          </button>
        </div>

        {showForm && (
          <form onSubmit={createJob} className="bg-slate-900 p-4 rounded-lg grid grid-cols-2 gap-3 mb-4">
            <input
              placeholder="Role title"
              value={newJob.role_title}
              onChange={(e) => setNewJob({ ...newJob, role_title: e.target.value })}
              className="col-span-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
              required
            />
            <textarea
              placeholder="Description"
              value={newJob.description}
              onChange={(e) => setNewJob({ ...newJob, description: e.target.value })}
              className="col-span-2 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
            />
            <input
              type="number"
              step="0.1"
              placeholder="Package (LPA)"
              value={newJob.package_lpa}
              onChange={(e) => setNewJob({ ...newJob, package_lpa: e.target.value })}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
            />
            <input
              type="number"
              step="0.1"
              placeholder="Min CGPA"
              value={newJob.min_cgpa}
              onChange={(e) => setNewJob({ ...newJob, min_cgpa: e.target.value })}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
            />
            <input
              type="number"
              placeholder="Max Backlogs"
              value={newJob.max_backlogs}
              onChange={(e) => setNewJob({ ...newJob, max_backlogs: e.target.value })}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
            />
            <input
              type="date"
              required
              value={newJob.drive_date}
              onChange={(e) => setNewJob({ ...newJob, drive_date: e.target.value })}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
            />
            <input
              placeholder="Allowed branches, e.g. CSE, ISE (empty = all)"
              value={newJob.allowed_branches}
              onChange={(e) => setNewJob({ ...newJob, allowed_branches: e.target.value })}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
            />
            <button type="submit" className="col-span-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg py-2 text-sm font-medium">
              Create Listing
            </button>
          </form>
        )}

        <div className="space-y-2">
          {jobs.map((job) => (
            <div key={job.id} className="bg-slate-900 p-3 rounded-lg flex justify-between items-center text-sm">
              <div>
                <div className="font-medium">{job.role_title}</div>
                <div className="text-xs text-slate-400">
                  {job.package_lpa} LPA | Min CGPA {job.min_cgpa} | Max Backlogs {job.max_backlogs} | Drive {job.drive_date} |{' '}
                  {job.allowed_branches.length ? job.allowed_branches.join(', ') : 'All branches'}
                </div>
              </div>
            </div>
          ))}
          {jobs.length === 0 && <p className="text-slate-400 text-sm">No job listings posted yet.</p>}
        </div>
      </div>

      <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
        <h3 className="font-semibold text-lg mb-4">Applicants</h3>
        <div className="space-y-3">
          {applications.map((a) => (
            <div key={a.id} className="bg-slate-900 p-4 rounded-lg space-y-3">
              <div className="flex justify-between items-center">
                <div>
                  <div className="font-medium">{a.student_name} — {a.job_title}</div>
                  <div className="text-xs text-slate-400">
                    CGPA: {a.student_cgpa} | Backlogs: {a.student_backlogs}
                  </div>
                </div>
                <StatusBadge status={a.status} />
              </div>

              {a.status === 'APPLIED' && (
                <div className="flex gap-2">
                  <button
                    onClick={() => run(() => setAppStatus(a.id, 'SHORTLISTED'))}
                    className="px-3 py-1.5 bg-amber-700 hover:bg-amber-600 rounded-md text-xs font-medium"
                  >
                    Shortlist
                  </button>
                  <button
                    onClick={() => run(() => setAppStatus(a.id, 'REJECTED'))}
                    className="px-3 py-1.5 bg-rose-800 hover:bg-rose-700 rounded-md text-xs font-medium"
                  >
                    Reject
                  </button>
                </div>
              )}

              {['SHORTLISTED', 'INTERVIEW_SCHEDULED', 'INTERVIEWED'].includes(a.status) && !a.offer && (
                <div className="flex flex-wrap items-center gap-2">
                  {a.status !== 'INTERVIEWED' && (
                    <>
                      <input
                        type="datetime-local"
                        onChange={(e) => setInterviewDrafts({ ...interviewDrafts, [a.id]: e.target.value })}
                        className="bg-slate-800 border border-slate-700 rounded-md px-2 py-1 text-xs"
                      />
                      <input
                        placeholder="Venue"
                        onChange={(e) => setVenueDrafts({ ...venueDrafts, [a.id]: e.target.value })}
                        className="w-28 bg-slate-800 border border-slate-700 rounded-md px-2 py-1 text-xs"
                      />
                      <button
                        onClick={() => run(() => scheduleInterview(a.id))}
                        className="px-3 py-1.5 bg-sky-700 hover:bg-sky-600 rounded-md text-xs font-medium"
                      >
                        {a.interview ? 'Schedule Next Round' : 'Schedule Interview'}
                      </button>
                    </>
                  )}
                  {a.interview && a.interview.result === 'PENDING' && (
                    <>
                      <button
                        onClick={() => run(() => recordResult(a.id, 'PASS'))}
                        className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 rounded-md text-xs font-medium"
                      >
                        Mark Pass
                      </button>
                      <button
                        onClick={() => run(() => recordResult(a.id, 'FAIL'))}
                        className="px-3 py-1.5 bg-rose-800 hover:bg-rose-700 rounded-md text-xs font-medium"
                      >
                        Mark Fail
                      </button>
                    </>
                  )}
                  {a.status === 'INTERVIEWED' && (
                    <>
                      <input
                        type="number"
                        step="0.1"
                        placeholder="Offer LPA"
                        onChange={(e) => setOfferDrafts({ ...offerDrafts, [a.id]: e.target.value })}
                        className="w-24 bg-slate-800 border border-slate-700 rounded-md px-2 py-1 text-xs"
                      />
                      <button
                        onClick={() => run(() => issueOffer(a.id))}
                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-md text-xs font-medium"
                      >
                        Issue Offer
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
          {applications.length === 0 && <p className="text-slate-400 text-sm">No applicants yet.</p>}
        </div>
      </div>
    </div>
  );
}
