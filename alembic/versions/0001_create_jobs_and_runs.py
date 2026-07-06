"""create jobs and job_runs tables

Revision ID: 0001_create_jobs_and_runs
Revises: None
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


revision = '0001_create_jobs_and_runs'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'jobs',
        sa.Column('job_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('schedule_type', sa.String(length=20), nullable=False),
        sa.Column('cron_expr', sa.String(length=120), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timezone', sa.String(length=100), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('backoff_seconds', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('job_id')
    )
    op.create_index(op.f('ix_jobs_next_run_at'), 'jobs', ['next_run_at'], unique=False)

    op.create_table(
        'job_runs',
        sa.Column('run_id', sa.Uuid(), nullable=False),
        sa.Column('job_id', sa.Uuid(), nullable=False),
        sa.Column('attempt', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('worker_id', sa.String(length=255), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('trace_id', sa.String(length=255), nullable=True),
        sa.Column('result_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.job_id']),
        sa.PrimaryKeyConstraint('run_id')
    )
    op.create_index(op.f('ix_job_runs_job_id'), 'job_runs', ['job_id'], unique=False)
    op.create_index(op.f('ix_job_runs_idempotency_key'), 'job_runs', ['idempotency_key'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_job_runs_idempotency_key'), table_name='job_runs')
    op.drop_index(op.f('ix_job_runs_job_id'), table_name='job_runs')
    op.drop_table('job_runs')
    op.drop_index(op.f('ix_jobs_next_run_at'), table_name='jobs')
    op.drop_table('jobs')
