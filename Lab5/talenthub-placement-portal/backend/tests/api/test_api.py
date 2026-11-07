"""Iteration 7 – API, access control and security (FR-1.x, NFR-3.x), plus the full workflow through HTTP."""
import os

from app.core import security
from tests.conftest import login

RAHUL, PRIYA, AMAN = "rahul@student.talenthub.edu", "priya@student.talenthub.edu", "aman@student.talenthub.edu"
ABC, XYZ, COORD = "hr@abctech.com", "hr@xyzcorp.com", "coordinator@talenthub.edu"


async def _job_id(client, headers, title):
    jobs = (await client.get("/jobs", headers=headers)).json()
    return next(j["id"] for j in jobs if j["role_title"] == title)


async def test_NFR3_1_invalid_and_expired_tokens_are_401(client):
    assert (await client.get("/students/me", headers={"Authorization": "Bearer garbage"})).status_code == 401
    expired = security.create_access_token({"sub": "1", "role": "STUDENT"}, expires_minutes=-1)
    assert (await client.get("/students/me", headers={"Authorization": f"Bearer {expired}"})).status_code == 401


async def test_NFR3_7_secret_comes_from_environment(client):
    assert security.SECRET_KEY == os.environ["TALENTHUB_SECRET_KEY"]
    assert "SECRET_KEY = \"" not in open(security.__file__).read()


async def test_FR2_5_student_profile_shows_eligibility_values(client):
    me = (await client.get("/students/me", headers=await login(client, RAHUL))).json()
    assert me["usn"] and me["branch"] == "CSE" and me["has_accepted_offer"] is False
    assert {"cgpa", "active_backlogs", "cleared_backlogs"} <= me.keys()


async def test_NFR3_4_company_cannot_list_all_students(client):
    assert (await client.get("/students", headers=await login(client, ABC))).status_code == 403


async def test_FR4_7_jobs_show_reason_and_ineligible_apply_is_400_with_reason(client):
    h = await login(client, AMAN)
    jobs = (await client.get("/jobs", headers=h)).json()
    blocked = next(j for j in jobs if not j["eligible"])
    assert "below minimum" in blocked["reason"] or "not in drive scope" in blocked["reason"]
    r = await client.post("/applications", json={"job_id": blocked["id"]}, headers=h)
    assert r.status_code == 400 and r.json()["detail"] == blocked["reason"]


async def test_FR1_4_company_cannot_see_other_company_applicants(client):
    h = await login(client, RAHUL)
    job = await _job_id(client, h, "Software Developer")  # an ABC drive
    await client.post("/applications", json={"job_id": job}, headers=h)
    assert (await client.get(f"/applications/job/{job}", headers=await login(client, XYZ))).status_code == 403
    assert (await client.get(f"/applications/job/{job}", headers=await login(client, ABC))).status_code == 200


async def test_NFR3_3_out_of_range_input_is_422(client):
    h = await login(client, ABC)
    base = {"role_title": "X", "min_cgpa": 6.5, "max_backlogs": 0, "drive_date": "2026-12-20", "allowed_branches": []}
    assert (await client.post("/jobs", json={**base, "min_cgpa": 11}, headers=h)).status_code == 422
    assert (await client.post("/jobs", json={**base, "max_backlogs": -1}, headers=h)).status_code == 422
    assert (await client.post("/jobs", json={**base, "allowed_branches": ["Computer Science"]}, headers=h)).status_code == 422


async def test_full_workflow_and_FR8_5_and_NFR3_2(client):
    student, company, coord = await login(client, PRIYA), await login(client, ABC), await login(client, COORD)
    job = await _job_id(client, student, "Software Developer")
    app = (await client.post("/applications", json={"job_id": job}, headers=student)).json()
    assert app["status"] == "APPLIED"
    aid = app["id"]

    # offer before interview is refused (FR-8.2)
    assert (await client.post("/offers", json={"application_id": aid, "package_lpa": 8}, headers=company)).status_code == 400

    r = await client.post(f"/jobs/{job}/shortlist", headers=coord)
    assert r.status_code == 200 and r.json()["shortlisted"] == 1
    r = await client.post("/interviews/schedule", headers=company, json={
        "application_id": aid, "scheduled_at": "2026-12-01T10:00:00Z", "venue": "Seminar Hall"})
    assert r.status_code == 200 and r.json()["status"] == "INTERVIEW_SCHEDULED"
    r = await client.patch(f"/interviews/{aid}/result", json={"result": "PASS"}, headers=company)
    assert r.json()["status"] == "INTERVIEWED"
    r = await client.post("/offers", json={"application_id": aid, "package_lpa": 8.5}, headers=company)
    assert r.json()["status"] == "OFFERED" and "offer_letter_key" not in r.json()["offer"]

    # another student cannot accept Priya's offer (NFR-3.2)
    assert (await client.patch(f"/offers/{aid}/respond", json={"accept": True},
                               headers=await login(client, RAHUL))).status_code == 404
    r = await client.patch(f"/offers/{aid}/respond", json={"accept": True}, headers=student)
    assert r.json()["status"] == "ACCEPTED"

    other = await _job_id(client, student, "Backend Engineer")  # XYZ drive
    r = await client.post("/applications", json={"job_id": other}, headers=student)
    assert r.status_code == 400 and r.json()["detail"] == "Already accepted an offer this season"

    stats = (await client.get("/coordinator/stats", headers=coord)).json()
    assert stats["total_accepted"] == 1 and stats["status_counts"]["ACCEPTED"] == 1
    csv_r = await client.get(f"/jobs/{job}/shortlist.csv", headers=coord)
    assert csv_r.status_code == 200 and csv_r.text.startswith("usn,full_name,branch,cgpa,status")
