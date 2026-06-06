"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "profile_settings",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("target_roles", sa.JSON(), nullable=False),
        sa.Column("locations", sa.JSON(), nullable=False),
        sa.Column("excluded_roles", sa.JSON(), nullable=False),
        sa.Column("job_sources", sa.JSON(), nullable=False),
        sa.Column("match_threshold", sa.Integer(), nullable=False),
        sa.Column("max_applications_per_day", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_id", name="uq_profile_settings_profile_id"),
    )
    op.create_table(
        "master_resumes",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("source_mime_type", sa.String(length=100), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("parsed_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "resume_sections",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("master_resume_id", sa.String(length=36), nullable=False),
        sa.Column("section_type", sa.String(length=50), nullable=False),
        sa.Column("heading", sa.String(length=255), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["master_resume_id"], ["master_resumes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "resume_evidence",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("master_resume_id", sa.String(length=36), nullable=False),
        sa.Column("resume_section_id", sa.String(length=36), nullable=True),
        sa.Column("evidence_key", sa.String(length=255), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["master_resume_id"], ["master_resumes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_section_id"], ["resume_sections.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_job_id", sa.String(length=255), nullable=True),
        sa.Column("stable_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("apply_url", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_id", "stable_hash", name="uq_jobs_profile_stable_hash"),
    )
    op.create_table(
        "job_requirements",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("structured_json", sa.JSON(), nullable=False),
        sa.Column("analyzed_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", name="uq_job_requirements_job_id"),
    )
    op.create_table(
        "job_matches",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("total_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("skills_match", sa.Integer(), nullable=False),
        sa.Column("experience_match", sa.Integer(), nullable=False),
        sa.Column("role_match", sa.Integer(), nullable=False),
        sa.Column("location_match", sa.Integer(), nullable=False),
        sa.Column("work_authorization_match", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=50), nullable=False),
        sa.Column("reject_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", name="uq_job_matches_job_id"),
    )
    op.create_table(
        "resume_versions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("master_resume_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("tailored_json", sa.JSON(), nullable=False),
        sa.Column("ats_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["master_resume_id"], ["master_resumes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "profile_id", "job_id", "version_number", name="uq_resume_versions_profile_job_version"
        ),
    )
    op.create_table(
        "applications",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("resume_version_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("profile_id", "job_id", name="uq_applications_profile_job"),
    )
    op.create_table(
        "answer_bank",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("requires_review", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("profile_id", "key", name="uq_answer_bank_profile_key"),
    )
    op.create_table(
        "application_answers",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("answer_bank_id", sa.String(length=36), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("needs_user_review", sa.Boolean(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["answer_bank_id"], ["answer_bank.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("run_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("actor_type", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("agent_runs")
    op.drop_table("application_answers")
    op.drop_table("answer_bank")
    op.drop_table("applications")
    op.drop_table("resume_versions")
    op.drop_table("job_matches")
    op.drop_table("job_requirements")
    op.drop_table("jobs")
    op.drop_table("resume_evidence")
    op.drop_table("resume_sections")
    op.drop_table("master_resumes")
    op.drop_table("profile_settings")
    op.drop_table("profiles")
    op.drop_table("users")
