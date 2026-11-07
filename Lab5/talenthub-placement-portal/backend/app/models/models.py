"""The 12-table schema from our Lab 4 design (TalentHub_Normalized_Schema.md), 3NF/BCNF.

Derived values (current season, a job's season, has_accepted_offer, timelines) are not stored;
they are computed in the repository layer, which replaces the Lab 4 SQL views."""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String,
    UniqueConstraint, text,
)
from sqlalchemy.orm import declarative_base, relationship

from app.domain.enums import ApplicationStatus, Branch, ConsentPurpose, UserRole

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


def _enum(e, name):
    return Enum(e, name=name, native_enum=False, create_constraint=True, validate_strings=True, length=32)


# ---------- Group A: people and identity ----------
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(role = 'COMPANY_REP' AND company_id IS NOT NULL) OR (role <> 'COMPANY_REP' AND company_id IS NULL)",
            name="ck_users_rep_has_company",
        ),
    )
    id = Column(Integer, primary_key=True)
    email = Column(String(254), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String(120), nullable=False)
    role = Column(_enum(UserRole, "user_role"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    company = relationship("Company")
    student = relationship("Student", back_populates="user", uselist=False)


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    description = Column(String, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    jobs = relationship("JobListing", back_populates="company")


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("cgpa >= 0 AND cgpa <= 10", name="ck_students_cgpa_range"),
        CheckConstraint("active_backlogs >= 0", name="ck_students_active_backlogs"),
        CheckConstraint("cleared_backlogs >= 0", name="ck_students_cleared_backlogs"),
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    usn = Column(String(20), unique=True, nullable=False)
    branch = Column(_enum(Branch, "branch"), nullable=False)
    cgpa = Column(Numeric(4, 2), nullable=False)
    active_backlogs = Column(Integer, nullable=False, default=0)
    cleared_backlogs = Column(Integer, nullable=False, default=0)
    is_anonymised = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="student")
    applications = relationship("Application", back_populates="student")


# ---------- Group B: seasons and drives ----------
class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (CheckConstraint("end_date > start_date", name="ck_seasons_dates"),)
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True, nullable=False)
    start_date = Column(Date, unique=True, nullable=False)
    end_date = Column(Date, nullable=False)


class JobListing(Base):
    """No season_id: a drive's season is the one whose date range contains drive_date (Lab 4 decision)."""

    __tablename__ = "job_listings"
    __table_args__ = (
        CheckConstraint("min_cgpa >= 0 AND min_cgpa <= 10", name="ck_jobs_min_cgpa"),
        CheckConstraint("max_backlogs >= 0", name="ck_jobs_max_backlogs"),
        CheckConstraint("package_lpa >= 0", name="ck_jobs_package"),
    )
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    role_title = Column(String(120), nullable=False)
    description = Column(String, nullable=False, default="")
    package_lpa = Column(Numeric(6, 2), nullable=False, default=0)  # advertised package (kept for the UI)
    min_cgpa = Column(Numeric(4, 2), nullable=False)
    max_backlogs = Column(Integer, nullable=False, default=0)
    drive_date = Column(Date, nullable=False)
    is_open = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    company = relationship("Company", back_populates="jobs")
    allowed_branches = relationship("JobAllowedBranch", cascade="all, delete-orphan", lazy="selectin")
    applications = relationship("Application", back_populates="job")


class JobAllowedBranch(Base):
    """No rows for a job = pool drive (R4)."""

    __tablename__ = "job_allowed_branches"
    job_id = Column(Integer, ForeignKey("job_listings.id", ondelete="CASCADE"), primary_key=True)
    branch = Column(_enum(Branch, "branch"), primary_key=True)


# ---------- Group C: application pipeline ----------
class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("student_id", "job_id", name="uq_applications_student_job"),)
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("job_listings.id"), nullable=False)
    # Documented copy of the latest history row; changed only by the transition function (FR-5.6)
    status = Column(_enum(ApplicationStatus, "application_status"), nullable=False, default=ApplicationStatus.APPLIED)

    student = relationship("Student", back_populates="applications")
    job = relationship("JobListing", back_populates="applications")
    history = relationship("ApplicationStatusHistory", order_by="ApplicationStatusHistory.id")
    interviews = relationship("InterviewSlot", order_by="InterviewSlot.round_no")
    offer = relationship("Offer", uselist=False)


class ApplicationStatusHistory(Base):
    """Append-only; the single source of event times and of who made each change (NFR-9.1)."""

    __tablename__ = "application_status_history"
    __table_args__ = (UniqueConstraint("application_id", "status", name="uq_history_app_status"),)
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    status = Column(_enum(ApplicationStatus, "application_status"), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class InterviewSlot(Base):
    __tablename__ = "interview_slots"
    __table_args__ = (
        UniqueConstraint("application_id", "round_no", name="uq_slots_app_round"),
        CheckConstraint("round_no >= 1", name="ck_slots_round"),
    )
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    round_no = Column(Integer, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    venue = Column(String(120), nullable=False)
    passed = Column(Boolean, nullable=True)  # NULL until the result is recorded
    notes = Column(String, nullable=False, default="")


class Offer(Base):
    """Acceptance is shown by applications.status = ACCEPTED, not by a column here."""

    __tablename__ = "offers"
    __table_args__ = (CheckConstraint("package_lpa > 0", name="ck_offers_package"),)
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), unique=True, nullable=False)
    package_lpa = Column(Numeric(6, 2), nullable=False)
    offer_letter_key = Column(String(64), unique=True, nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class EligibilityDecision(Base):
    """Insert-only record of every check (NFR-9.3). student+job, because an APPLY rejection has no application."""

    __tablename__ = "eligibility_decisions"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("job_listings.id"), nullable=False)
    failed_rule = Column(String(2), nullable=True)  # NULL = eligible
    reason = Column(String, nullable=False)
    context = Column(String(10), nullable=False)  # APPLY or SHORTLIST
    checked_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


# ---------- Group D: privacy ----------
class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (
        Index(
            "uq_consents_one_active", "student_id", "purpose", unique=True,
            sqlite_where=text("withdrawn_at IS NULL"), postgresql_where=text("withdrawn_at IS NULL"),
        ),
    )
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    purpose = Column(_enum(ConsentPurpose, "consent_purpose"), nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)  # NULL = active
