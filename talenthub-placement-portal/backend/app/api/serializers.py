"""Shape domain objects into response dicts with only the fields callers need (NFR-3.4)."""
from app.domain.enums import ApplicationStatus as St


def job_out(job, result=None, applied=None) -> dict:
    data = {
        "id": job.id, "company_id": job.company_id, "role_title": job.role_title, "description": job.description,
        "package_lpa": job.package_lpa, "min_cgpa": job.min_cgpa, "max_backlogs": job.max_backlogs,
        "drive_date": job.drive_date, "is_open": job.is_open,
        "allowed_branches": [b.branch for b in job.allowed_branches],
        "company_name": job.company.name if job.company else None,
    }
    if result is not None:
        data.update(eligible=result.eligible, reason=result.reason, already_applied=applied)
    return data


def _slot(s) -> dict:
    result = "PENDING" if s.passed is None else ("PASS" if s.passed else "FAIL")
    return {"id": s.id, "round_no": s.round_no, "scheduled_at": s.scheduled_at, "venue": s.venue,
            "result": result, "notes": s.notes}


def _offer_status(status) -> str:
    return {St.ACCEPTED: "ACCEPTED", St.DECLINED: "DECLINED"}.get(St(status), "ISSUED")


def application_out(a) -> dict:
    s, job = a.student, a.job
    history = a.history or []
    slots = [_slot(x) for x in a.interviews]
    return {
        "id": a.id, "student_id": a.student_id, "job_id": a.job_id, "status": a.status,
        "applied_at": history[0].changed_at if history else None,
        "updated_at": history[-1].changed_at if history else None,
        "student_name": s.user.full_name if s else None, "student_usn": s.usn if s else None,
        "student_branch": s.branch.value if s else None, "student_cgpa": s.cgpa if s else None,
        "student_backlogs": s.active_backlogs if s else None,
        "job_title": job.role_title if job else None,
        "company_name": job.company.name if job and job.company else None,
        "interview": slots[-1] if slots else None,
        "interviews": slots,
        "offer": ({"id": a.offer.id, "package_lpa": a.offer.package_lpa, "status": _offer_status(a.status),
                   "issued_at": a.offer.issued_at} if a.offer else None),
    }
