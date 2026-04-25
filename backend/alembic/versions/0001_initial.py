"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(256), nullable=False),
        sa.Column("email", sa.String(256), nullable=False),
        sa.Column("phone", sa.String(64)),
        sa.Column("location", sa.String(128)),
        sa.Column("linkedin_url", sa.String(512)),
        sa.Column("github_url", sa.String(512)),
        sa.Column("portfolio_url", sa.String(512)),
        sa.Column("salary_min", sa.Integer),
        sa.Column("salary_max", sa.Integer),
        sa.Column("work_authorization", sa.String(128)),
        sa.Column("requires_sponsorship", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("willing_to_relocate", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("security_clearance", sa.String(64)),
        sa.Column("summary", sa.Text),
        sa.Column("standard_answers", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("eeo_answers", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("skills", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("certifications", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("work_history", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("education", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("references", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("cover_letter_templates", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "resume_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("pdf_path", sa.Text, nullable=False),
        sa.Column("parsed_text", sa.Text),
        sa.Column("structured", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(256)),
        sa.Column("ats", sa.String(32)),
        sa.Column("company", sa.String(256), nullable=False),
        sa.Column("role_title", sa.String(256), nullable=False),
        sa.Column("location", sa.String(128)),
        sa.Column("location_type", sa.String(32)),
        sa.Column("salary_min", sa.Integer),
        sa.Column("salary_max", sa.Integer),
        sa.Column("requires_clearance", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("clearance_level", sa.String(64)),
        sa.Column("job_url", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("skills", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("score", sa.Float),
        sa.Column("score_breakdown", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.Enum(
            "discovered", "scored", "queued", "review", "applying",
            "applied", "skipped", "failed", name="posting_status"
        ), nullable=False, server_default="discovered"),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_job_postings_source", "job_postings", ["source"])
    op.create_index("ix_job_postings_ats", "job_postings", ["ats"])
    op.create_index("ix_job_postings_company", "job_postings", ["company"])
    op.create_index("ix_job_postings_source_id", "job_postings", ["source_id"])
    op.create_index("ix_job_postings_status", "job_postings", ["status"])

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company", sa.String(256), nullable=False),
        sa.Column("role_title", sa.String(256), nullable=False),
        sa.Column("location", sa.String(128)),
        sa.Column("location_type", sa.String(32)),
        sa.Column("salary_min", sa.Integer),
        sa.Column("salary_max", sa.Integer),
        sa.Column("source", sa.String(64)),
        sa.Column("job_url", sa.Text),
        sa.Column("contact_person", sa.String(256)),
        sa.Column("notes", sa.Text),
        sa.Column("method", sa.Enum("auto", "manual", name="application_method"),
                  nullable=False, server_default="manual"),
        sa.Column("status", sa.Enum(
            "queued", "applied", "screening", "interview", "offer",
            "rejected", "ghosted", name="application_status"
        ), nullable=False, server_default="queued"),
        sa.Column("date_applied", sa.DateTime(timezone=True)),
        sa.Column("last_response_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("job_posting_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("job_postings.id", ondelete="SET NULL")),
    )
    op.create_index("ix_applications_company", "applications", ["company"])
    op.create_index("ix_applications_status", "applications", ["status"])

    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("color", sa.String(16)),
    )

    op.create_table(
        "application_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("application_id", "tag_id"),
    )

    op.create_table(
        "email_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("gmail_thread_id", sa.String(64), nullable=False, unique=True),
        sa.Column("gmail_message_id", sa.String(64), nullable=False),
        sa.Column("sender", sa.String(512), nullable=False),
        sa.Column("sender_domain", sa.String(256), nullable=False),
        sa.Column("subject", sa.Text, nullable=False),
        sa.Column("snippet", sa.Text),
        sa.Column("body_text", sa.Text),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detected_ats", sa.String(32)),
        sa.Column("classification", sa.String(32), nullable=False, server_default="other"),
        sa.Column("classification_confidence", sa.Float, nullable=False, server_default="0"),
        sa.Column("matched_rules", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("application_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_email_threads_sender_domain", "email_threads", ["sender_domain"])
    op.create_index("ix_email_threads_classification", "email_threads", ["classification"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="CASCADE")),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("ats", sa.String(32)),
        sa.Column("job_url", sa.Text),
        sa.Column("resume_variant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("cover_letter_text", sa.Text),
        sa.Column("answers", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("screenshot_paths", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("extra", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("success", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "paused_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_posting_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="SET NULL")),
        sa.Column("ats", sa.String(32), nullable=False),
        sa.Column("reason", sa.Enum(
            "captcha", "low_confidence_question", "assessment_required",
            "login_2fa", "unrecognized_form", "requirement_mismatch", "approval_required",
            name="paused_reason"
        ), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("pending_questions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("state", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("screenshot_path", sa.Text),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolution", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_paused_sessions_resolved", "paused_sessions", ["resolved"])
    op.create_index("ix_paused_sessions_created_at", "paused_sessions", ["created_at"])

    op.create_table(
        "job_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("identifier", sa.String(512), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("tos_acknowledged", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("last_polled_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_job_sources_kind", "job_sources", ["kind"])

    op.create_table(
        "oauth_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False, unique=True),
        sa.Column("access_token", sa.Text, nullable=False),
        sa.Column("refresh_token", sa.Text),
        sa.Column("token_uri", sa.Text),
        sa.Column("client_id", sa.Text),
        sa.Column("client_secret", sa.Text),
        sa.Column("scopes", sa.Text),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("user_email", sa.String(256)),
        sa.Column("last_history_id", sa.String(64)),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("oauth_tokens")
    op.drop_index("ix_job_sources_kind", table_name="job_sources")
    op.drop_table("job_sources")
    op.drop_index("ix_paused_sessions_created_at", table_name="paused_sessions")
    op.drop_index("ix_paused_sessions_resolved", table_name="paused_sessions")
    op.drop_table("paused_sessions")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_email_threads_classification", table_name="email_threads")
    op.drop_index("ix_email_threads_sender_domain", table_name="email_threads")
    op.drop_table("email_threads")
    op.drop_table("application_tags")
    op.drop_table("tags")
    op.drop_index("ix_applications_status", table_name="applications")
    op.drop_index("ix_applications_company", table_name="applications")
    op.drop_table("applications")
    op.drop_index("ix_job_postings_status", table_name="job_postings")
    op.drop_index("ix_job_postings_source_id", table_name="job_postings")
    op.drop_index("ix_job_postings_company", table_name="job_postings")
    op.drop_index("ix_job_postings_ats", table_name="job_postings")
    op.drop_index("ix_job_postings_source", table_name="job_postings")
    op.drop_table("job_postings")
    op.drop_table("resume_variants")
    op.drop_table("profiles")
    sa.Enum(name="application_status").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="application_method").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="posting_status").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="paused_reason").drop(op.get_bind(), checkfirst=False)
