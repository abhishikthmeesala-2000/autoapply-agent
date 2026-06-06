from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def test_migrations_create_expected_tables(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)

    expected_tables = {
        "users",
        "profiles",
        "profile_settings",
        "master_resumes",
        "resume_sections",
        "resume_evidence",
        "jobs",
        "job_requirements",
        "job_matches",
        "resume_versions",
        "applications",
        "application_answers",
        "answer_bank",
        "agent_runs",
        "audit_logs",
    }

    assert expected_tables.issubset(set(inspector.get_table_names()))


def test_profile_scoped_tables_include_profile_id(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    scoped_tables = {
        "profile_settings",
        "master_resumes",
        "resume_sections",
        "resume_evidence",
        "jobs",
        "job_requirements",
        "job_matches",
        "resume_versions",
        "applications",
        "application_answers",
        "answer_bank",
        "agent_runs",
        "audit_logs",
    }

    profile_columns = {column["name"] for column in inspector.get_columns("profiles")}
    assert "user_id" in profile_columns

    for table_name in scoped_tables:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert "profile_id" in columns, table_name
