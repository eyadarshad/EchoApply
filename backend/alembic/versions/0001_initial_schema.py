"""Initial schema — all core tables matching init.sql exactly

Revision ID: 0001
Revises: None
Create Date: 2026-07-04

This migration creates the exact database schema expected by the backend Python services:
- pgvector extension
- uuid-ossp extension
- users
- profiles (with profile_embedding vector(768))
- jobs (with jd_embedding vector(768))
- applications
- tailored_resumes
- technique_library
- job_cache
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # --- Users table ---
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("email", sa.Text(), unique=True, nullable=False),
        sa.Column("major", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # --- Profiles table ---
    op.create_table(
        "profiles",
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("parsed_resume_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("github_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("linkedin_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("portfolio_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("profile_embedding", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    # Add vector type column manually
    op.execute("ALTER TABLE profiles ALTER COLUMN profile_embedding TYPE vector(768) USING profile_embedding::vector(768);")

    # --- Jobs table ---
    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("remote", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("apply_url", sa.Text(), nullable=True),
        sa.Column("jd_embedding", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("job_hash", sa.Text(), unique=True, nullable=False),
    )
    op.execute("ALTER TABLE jobs ALTER COLUMN jd_embedding TYPE vector(768) USING jd_embedding::vector(768);")
    op.create_index("idx_jobs_job_hash", "jobs", ["job_hash"])

    # --- Applications table ---
    op.create_table(
        "applications",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.UUID(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "job_hash", name="unique_user_job_hash"),
    )
    op.create_index("idx_applications_user_hash", "applications", ["user_id", "job_hash"])

    # --- Tailored Resumes table ---
    op.create_table(
        "tailored_resumes",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.UUID(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("pdf_path", sa.Text(), nullable=True),
        sa.Column("docx_path", sa.Text(), nullable=True),
        sa.Column("ats_score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # --- Technique Library table ---
    op.create_table(
        "technique_library",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("technique", sa.Text(), nullable=False),
        sa.Column("applies_to_major", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("reader_weight", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("last_verified", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # --- Job Cache table ---
    op.create_table(
        "job_cache",
        sa.Column("query_hash", sa.Text(), primary_key=True),
        sa.Column("results_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_job_cache_expires_at", "job_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_table("job_cache")
    op.drop_table("technique_library")
    op.drop_table("tailored_resumes")
    op.drop_table("applications")
    op.drop_table("jobs")
    op.drop_table("profiles")
    op.drop_table("users")
