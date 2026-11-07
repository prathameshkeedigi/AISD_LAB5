"""Fixed value lists from the Lab 4 schema. Enums, not lookup tables, so no status can be added without its rules."""
from enum import Enum


class Branch(str, Enum):
    CSE = "CSE"
    ECE = "ECE"
    ISE = "ISE"
    MECH = "MECH"
    CIVIL = "CIVIL"


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    COMPANY_REP = "COMPANY_REP"
    COORDINATOR = "COORDINATOR"


class ApplicationStatus(str, Enum):
    APPLIED = "APPLIED"
    SHORTLISTED = "SHORTLISTED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    INTERVIEWED = "INTERVIEWED"
    OFFERED = "OFFERED"
    ACCEPTED = "ACCEPTED"
    # End states added by ADR-005 (decision D1)
    REJECTED = "REJECTED"
    DECLINED = "DECLINED"


class ConsentPurpose(str, Enum):
    PLACEMENT = "PLACEMENT"
    MARKETING_ANALYTICS = "MARKETING_ANALYTICS"
