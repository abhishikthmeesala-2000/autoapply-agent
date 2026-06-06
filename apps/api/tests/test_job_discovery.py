from __future__ import annotations

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Job, Profile, ProfileSetting, User
from app.job_discovery.connectors import GenericCareerPageConnector
from app.job_discovery.service import discover_jobs_for_profile
from app.main import app, get_db_session, get_job_discovery_client


def _create_profile(db_session, *, sources: list[str], target_roles: list[str]) -> Profile:
    user = User(email="jobs@example.com")
    db_session.add(user)
    db_session.flush()
    profile = Profile(user_id=user.id, name="Target", location="Remote")
    db_session.add(profile)
    db_session.flush()
    db_session.add(
        ProfileSetting(
            profile_id=profile.id,
            target_roles=target_roles,
            locations=["Remote"],
            excluded_roles=[],
            job_sources=sources,
            match_threshold=70,
            max_applications_per_day=5,
        )
    )
    db_session.commit()
    return profile


def _mock_client() -> httpx.Client:
    def responder(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "boards-api.greenhouse.io" in url:
            return httpx.Response(
                200,
                json={
                    "company_name": "Acme",
                    "jobs": [
                        {
                            "id": 101,
                            "title": "Backend Engineer",
                            "content": "Build APIs and Python services.",
                            "location": {"name": "Remote"},
                            "absolute_url": "https://careers.acme.example/jobs/101",
                        },
                        {
                            "id": 102,
                            "title": "Designer",
                            "content": "Design systems.",
                            "location": {"name": "Remote"},
                            "absolute_url": "https://careers.acme.example/jobs/102",
                        },
                    ],
                },
            )

        if "lever" in url:
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "lever-1",
                        "text": "Backend Engineer",
                        "descriptionPlain": "Build services with FastAPI.",
                        "categories": {"team": "Acme", "location": "Remote"},
                        "hostedUrl": "https://jobs.lever.co/acme/lever-1",
                    }
                ],
            )

        if "ashby" in url:
            return httpx.Response(
                200,
                json={
                    "companyName": "Acme",
                    "jobs": [
                        {
                            "id": "ashby-1",
                            "title": "Backend Engineer",
                            "descriptionHtml": "<p>Python, APIs, data.</p>",
                            "location": "Remote",
                            "absoluteUrl": "https://jobs.ashbyhq.com/acme/ashby-1",
                        }
                    ],
                },
            )

        if "careers.example.com" in url:
            return httpx.Response(
                200,
                text="""
                <html>
                  <head>
                    <title>Platform Engineer</title>
                    <meta name="description" content="Platform Engineer role building job automation.">
                    <meta property="og:site_name" content="Example Co">
                  </head>
                  <body>
                    <main>
                      <p>Remote</p>
                      <p>Build systems for engineers.</p>
                    </main>
                  </body>
                </html>
                """,
            )

        if "blocked.example.com" in url:
            return httpx.Response(403, text="blocked")

        return httpx.Response(404, json={"error": "not found"})

    return httpx.Client(transport=httpx.MockTransport(responder), base_url="https://example.com")


def test_service_discovers_jobs_across_ats_sources_and_dedupes(db_session) -> None:
    greenhouse_url = "https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true"
    lever_url = "https://api.lever.co/v0/postings/acme?mode=json"
    ashby_url = "https://jobs.ashbyhq.com/acme?format=json"
    profile = _create_profile(
        db_session,
        sources=[greenhouse_url, lever_url, ashby_url],
        target_roles=["backend engineer"],
    )

    client = _mock_client()

    first = discover_jobs_for_profile(db=db_session, profile_id=profile.id, client=client)
    assert first.sources_processed == 3
    assert first.jobs_found == 3
    assert first.jobs_inserted == 3
    assert first.jobs_deduped == 0

    second = discover_jobs_for_profile(db=db_session, profile_id=profile.id, client=client)
    assert second.jobs_found == 3
    assert second.jobs_inserted == 0
    assert second.jobs_deduped == 3

    jobs = db_session.execute(select(Job).where(Job.profile_id == profile.id)).scalars().all()
    assert len(jobs) == 3
    assert {job.profile_id for job in jobs} == {profile.id}
    assert {job.source for job in jobs} == {"greenhouse", "lever", "ashby"}


def test_generic_career_page_connector_extracts_visible_page_text() -> None:
    connector = GenericCareerPageConnector()
    client = _mock_client()

    jobs = connector.discover(
        source_url="https://careers.example.com/jobs/platform-engineer",
        target_roles=["platform engineer"],
        client=client,
    )

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title.startswith("Platform Engineer")
    assert job.company == "Example Co"
    assert job.location == "Remote"


def test_blocked_source_is_reported_without_crashing(db_session) -> None:
    blocked_url = "https://blocked.example.com/jobs"
    profile = _create_profile(db_session, sources=[blocked_url], target_roles=["engineer"])

    result = discover_jobs_for_profile(db=db_session, profile_id=profile.id, client=_mock_client())

    assert result.jobs_found == 0
    assert result.jobs_inserted == 0
    assert result.blocked_sources == [blocked_url]


def test_discovery_endpoint_uses_profile_settings_and_client_override(db_session) -> None:
    greenhouse_url = "https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true"
    profile = _create_profile(
        db_session,
        sources=[greenhouse_url],
        target_roles=["backend engineer"],
    )

    def override_db():
        yield db_session

    def override_client():
        client = _mock_client()
        try:
            yield client
        finally:
            client.close()

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_job_discovery_client] = override_client

    try:
        with TestClient(app) as client:
            response = client.post(f"/profiles/{profile.id}/agent/discover-jobs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == profile.id
    assert body["jobs_inserted"] == 1
    assert body["jobs_found"] == 1
    assert body["jobs_deduped"] == 0
