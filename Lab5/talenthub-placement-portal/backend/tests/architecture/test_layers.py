"""Iteration 10 – search-based architecture drift checks (NFR-2.1 to NFR-2.7, NFR-3.6, ADR-001/004)."""
import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"
ROUTERS = sorted((APP / "api").glob("*.py"))
SERVICES = sorted((APP / "services").glob("*.py"))


def _src(p: Path) -> str:
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", ROUTERS, ids=lambda p: p.name)
def test_NFR2_2_routers_do_not_touch_repositories_or_queries(path):
    src = _src(path)
    assert "app.repositories" not in src
    assert not re.search(r"(?<![.\w])(select|insert|update|delete)\(", src)  # SQLAlchemy constructs, not methods
    assert "db.execute" not in src and "db.add" not in src and "db.commit" not in src


@pytest.mark.parametrize("path", SERVICES, ids=lambda p: p.name)
def test_NFR2_4_services_raise_no_http_exceptions(path):
    src = _src(path)
    assert "fastapi" not in src
    assert "HTTPException" not in src


@pytest.mark.parametrize("path", SERVICES, ids=lambda p: p.name)
def test_NFR2_3_services_do_not_import_each_other(path):
    # Exception: the pure eligibility rule function, which FR-4.5 requires every use case to call.
    imports = re.findall(r"from app\.services[.\w]* import (\w+)|import app\.services\.(\w+)", _src(path))
    names = {a or b for a, b in imports} - {"eligibility_service", "EligibilityResult", "check_eligibility"}
    assert not names, f"{path.name} imports other services: {names}"


def test_NFR2_6_eligibility_rules_live_in_one_function():
    hits = [p.name for p in APP.rglob("*.py") if re.search(r"cgpa\s*(>=|<|>|<=)\s*\w*min", _src(p))]
    assert hits == ["eligibility_service.py"]


def test_eligibility_service_is_pure():
    src = _src(APP / "services" / "eligibility_service.py")
    assert "sqlalchemy" not in src and "repositories" not in src and "await" not in src


@pytest.mark.parametrize("path", sorted(APP.rglob("*.py")), ids=lambda p: p.name)
def test_NFR3_6_no_sql_built_from_strings(path):
    src = _src(path)
    assert not re.search(r"text\(\s*f[\"']", src)
    assert not re.search(r"execute\(\s*f[\"']", src)


def test_FR1_2_only_deps_decodes_tokens():
    users = [p.name for p in APP.rglob("*.py") if "decode_access_token(" in _src(p)]
    assert sorted(users) == ["deps.py", "security.py"]


def test_NFR2_5_runtime_imports_are_in_requirements():
    reqs = _src(APP.parent / "requirements.txt").lower()
    for pkg in ("fastapi", "sqlalchemy", "pydantic", "passlib", "jose", "aiosqlite"):
        assert pkg in reqs
