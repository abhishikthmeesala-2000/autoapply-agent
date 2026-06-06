from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def new_uuid() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    profiles: Mapped[list[Profile]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="profiles")
    setting: Mapped[Optional[ProfileSetting]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", uselist=False
    )


class ProfileSetting(Base, TimestampMixin):
    __tablename__ = "profile_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    target_roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    locations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    excluded_roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    job_sources: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    match_threshold: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    max_applications_per_day: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="setting")


class MasterResume(Base, TimestampMixin):
    __tablename__ = "master_resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    sections: Mapped[list[ResumeSection]] = relationship(
        back_populates="master_resume", cascade="all, delete-orphan"
    )
    evidence_items: Mapped[list[ResumeEvidence]] = relationship(
        back_populates="master_resume", cascade="all, delete-orphan"
    )


class ResumeSection(Base, TimestampMixin):
    __tablename__ = "resume_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    master_resume_id: Mapped[str] = mapped_column(
        ForeignKey("master_resumes.id", ondelete="CASCADE"), nullable=False
    )
    section_type: Mapped[str] = mapped_column(String(50), nullable=False)
    heading: Mapped[str] = mapped_column(String(255), nullable=False)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    master_resume: Mapped[MasterResume] = relationship(back_populates="sections")
    evidence_items: Mapped[list[ResumeEvidence]] = relationship(back_populates="resume_section")


class ResumeEvidence(Base, TimestampMixin):
    __tablename__ = "resume_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    master_resume_id: Mapped[str] = mapped_column(
        ForeignKey("master_resumes.id", ondelete="CASCADE"), nullable=False
    )
    resume_section_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("resume_sections.id", ondelete="CASCADE")
    )
    evidence_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)

    master_resume: Mapped[MasterResume] = relationship(back_populates="evidence_items")
    resume_section: Mapped[Optional[ResumeSection]] = relationship(back_populates="evidence_items")


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("profile_id", "stable_hash", name="uq_jobs_profile_stable_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_job_id: Mapped[Optional[str]] = mapped_column(String(255))
    stable_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    apply_url: Mapped[Optional[str]] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(50), default="discovered", nullable=False)

    requirement: Mapped[Optional[JobRequirement]] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )
    match: Mapped[Optional[JobMatch]] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )
    resume_versions: Mapped[list[ResumeVersion]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobRequirement(Base, TimestampMixin):
    __tablename__ = "job_requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    structured_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    analyzed_by: Mapped[str] = mapped_column(String(100), default="qwen3", nullable=False)

    job: Mapped[Job] = relationship(back_populates="requirement")


class JobMatch(Base, TimestampMixin):
    __tablename__ = "job_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    total_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    skills_match: Mapped[int] = mapped_column(Integer, nullable=False)
    experience_match: Mapped[int] = mapped_column(Integer, nullable=False)
    role_match: Mapped[int] = mapped_column(Integer, nullable=False)
    location_match: Mapped[int] = mapped_column(Integer, nullable=False)
    work_authorization_match: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    reject_reason: Mapped[Optional[str]] = mapped_column(String(255))

    job: Mapped[Job] = relationship(back_populates="match")


class ResumeVersion(Base, TimestampMixin):
    __tablename__ = "resume_versions"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "job_id", "version_number", name="uq_resume_versions_profile_job_version"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    master_resume_id: Mapped[str] = mapped_column(
        ForeignKey("master_resumes.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tailored_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    ats_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))

    job: Mapped[Job] = relationship(back_populates="resume_versions")
    applications: Mapped[list[Application]] = relationship(back_populates="resume_version")


class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("profile_id", "job_id", name="uq_applications_profile_job"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    resume_version_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    job: Mapped[Job] = relationship(back_populates="applications")
    resume_version: Mapped[Optional[ResumeVersion]] = relationship(back_populates="applications")
    answers: Mapped[list[ApplicationAnswer]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class AnswerBank(Base, TimestampMixin):
    __tablename__ = "answer_bank"
    __table_args__ = (UniqueConstraint("profile_id", "key", name="uq_answer_bank_profile_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ApplicationAnswer(Base, TimestampMixin):
    __tablename__ = "application_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    answer_bank_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("answer_bank.id", ondelete="SET NULL")
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    needs_user_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)

    application: Mapped[Application] = relationship(back_populates="answers")


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    run_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
