"""Request/response schemas. Input ranges are validated here before any use (NFR-3.3)."""
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ApplicationStatus, Branch

Cgpa = Annotated[Decimal, Field(ge=0, le=10, max_digits=4, decimal_places=2)]
Backlogs = Annotated[int, Field(ge=0, le=60)]
Package = Annotated[Decimal, Field(gt=0, max_digits=6, decimal_places=2)]


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    name: str
    linked_id: Optional[int] = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usn: str
    name: str
    email: str
    branch: Branch
    cgpa: Decimal
    active_backlogs: int
    cleared_backlogs: int
    has_accepted_offer: bool = False


class StudentCreate(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    usn: str = Field(pattern=r"^[0-9A-Za-z]{6,20}$")
    branch: Branch
    cgpa: Cgpa
    active_backlogs: Backlogs = 0
    cleared_backlogs: Backlogs = 0


class AcademicsUpdate(BaseModel):
    cgpa: Cgpa
    active_backlogs: Backlogs
    cleared_backlogs: Optional[Backlogs] = None


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str


class SeasonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    start_date: date
    end_date: date


class SeasonOut(SeasonCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class JobCreate(BaseModel):
    role_title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    package_lpa: Annotated[Decimal, Field(ge=0, max_digits=6, decimal_places=2)] = Decimal("0")
    min_cgpa: Cgpa
    max_backlogs: Backlogs = 0
    drive_date: date
    allowed_branches: list[Branch] = []
    company_id: Optional[int] = None  # used only when the coordinator publishes


class CriteriaUpdate(BaseModel):
    min_cgpa: Cgpa
    max_backlogs: Backlogs
    allowed_branches: Optional[list[Branch]] = None


class JobOut(BaseModel):
    id: int
    company_id: int
    role_title: str
    description: str
    package_lpa: Decimal
    min_cgpa: Decimal
    max_backlogs: int
    drive_date: date
    is_open: bool
    allowed_branches: list[Branch]
    company_name: Optional[str] = None
    eligible: Optional[bool] = None
    reason: Optional[str] = None
    already_applied: Optional[bool] = None


class ApplicationCreate(BaseModel):
    job_id: int = Field(gt=0)


class ApplicationStatusUpdate(BaseModel):
    status: Literal["SHORTLISTED", "REJECTED"]


class InterviewScheduleRequest(BaseModel):
    application_id: int = Field(gt=0)
    scheduled_at: datetime
    venue: str = Field(default="To be announced", min_length=1, max_length=120)
    round_no: Optional[int] = Field(default=None, ge=1, le=20)
    notes: str = Field(default="", max_length=1000)


class InterviewResultRequest(BaseModel):
    result: Literal["PASS", "FAIL"]
    round_no: Optional[int] = Field(default=None, ge=1, le=20)
    final: bool = True
    notes: str = Field(default="", max_length=1000)


class OfferCreate(BaseModel):
    application_id: int = Field(gt=0)
    package_lpa: Package


class OfferRespondRequest(BaseModel):
    accept: bool


class ApplicationOut(BaseModel):
    id: int
    student_id: int
    job_id: int
    status: ApplicationStatus
    applied_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    student_name: Optional[str] = None
    student_usn: Optional[str] = None
    student_branch: Optional[str] = None
    student_cgpa: Optional[Decimal] = None
    student_backlogs: Optional[int] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    interview: Optional[dict] = None
    interviews: list[dict] = []
    offer: Optional[dict] = None


class ShortlistOut(BaseModel):
    shortlisted: int
    ineligible: dict[int, str]


class CoordinatorStats(BaseModel):
    total_students: int
    total_companies: int
    total_jobs: int
    total_applications: int
    total_offers: int
    total_accepted: int
    placement_percentage: float
    status_counts: dict[str, int]
