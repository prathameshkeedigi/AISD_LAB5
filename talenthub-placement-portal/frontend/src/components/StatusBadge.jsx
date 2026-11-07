const STYLES = {
  APPLIED: 'bg-slate-700 text-slate-300 border-slate-600',
  SHORTLISTED: 'bg-amber-950/60 text-amber-300 border-amber-700',
  REJECTED: 'bg-rose-950/80 text-rose-300 border-rose-800',
  INTERVIEW_SCHEDULED: 'bg-sky-950/60 text-sky-300 border-sky-700',
  INTERVIEWED: 'bg-indigo-950/60 text-indigo-300 border-indigo-700',
  OFFERED: 'bg-emerald-950/60 text-emerald-300 border-emerald-700',
  ACCEPTED: 'bg-emerald-900/70 text-emerald-200 border-emerald-600',
  DECLINED: 'bg-rose-950/80 text-rose-300 border-rose-800',
  PASS: 'bg-emerald-950/60 text-emerald-300 border-emerald-700',
  FAIL: 'bg-rose-950/80 text-rose-300 border-rose-800',
  PENDING: 'bg-slate-700 text-slate-300 border-slate-600',
  ISSUED: 'bg-emerald-950/60 text-emerald-300 border-emerald-700',
};

export default function StatusBadge({ status }) {
  const style = STYLES[status] || 'bg-slate-700 text-slate-300 border-slate-600';
  return (
    <span className={`px-3 py-1 rounded-full text-xs border ${style}`}>
      {status.replaceAll('_', ' ')}
    </span>
  );
}
