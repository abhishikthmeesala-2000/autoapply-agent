from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import AnswerBank, Job, Profile, User


def test_jobs_and_answers_are_isolated_per_profile(db_session) -> None:
    user = User(email="test@example.com")
    db_session.add(user)
    db_session.flush()

    profile_one = Profile(user_id=user.id, name="Frontend Engineer", location="Remote")
    profile_two = Profile(user_id=user.id, name="Product Engineer", location="Austin")
    db_session.add_all([profile_one, profile_two])
    db_session.flush()

    job_one = Job(
        profile_id=profile_one.id,
        source="greenhouse",
        source_job_id="gh-1",
        stable_hash="shared-hash",
        title="Frontend Engineer",
        company="Acme",
        location="Remote",
        description="Build things",
        apply_url="https://example.com/apply/1",
    )
    job_two = Job(
        profile_id=profile_two.id,
        source="greenhouse",
        source_job_id="gh-2",
        stable_hash="shared-hash",
        title="Product Engineer",
        company="Beta",
        location="Austin",
        description="Ship things",
        apply_url="https://example.com/apply/2",
    )
    db_session.add_all([job_one, job_two])
    db_session.commit()

    profile_one_jobs = (
        db_session.execute(select(Job).where(Job.profile_id == profile_one.id)).scalars().all()
    )
    profile_two_jobs = (
        db_session.execute(select(Job).where(Job.profile_id == profile_two.id)).scalars().all()
    )

    assert {job.profile_id for job in profile_one_jobs} == {profile_one.id}
    assert {job.profile_id for job in profile_two_jobs} == {profile_two.id}

    db_session.add(
        Job(
            profile_id=profile_one.id,
            source="lever",
            source_job_id="lv-1",
            stable_hash="shared-hash",
            title="Duplicate Job",
            company="Acme",
            description="Duplicate should fail",
            apply_url="https://example.com/apply/3",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

    db_session.add_all(
        [
            AnswerBank(
                profile_id=profile_one.id,
                key="salary_expectation",
                question_text="What is your salary expectation?",
                answer_text="$150k",
                category="salary",
            ),
            AnswerBank(
                profile_id=profile_two.id,
                key="salary_expectation",
                question_text="What is your salary expectation?",
                answer_text="$175k",
                category="salary",
            ),
        ]
    )
    db_session.commit()

    answers = (
        db_session.execute(select(AnswerBank).where(AnswerBank.key == "salary_expectation"))
        .scalars()
        .all()
    )
    assert {answer.profile_id for answer in answers} == {profile_one.id, profile_two.id}
