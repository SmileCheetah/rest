"""allow schedules to persist the in-progress state

Revision ID: 20260818_in_progress
Revises: 69b16d4208ea
"""

from alembic import op

revision = "20260818_in_progress"
down_revision = "69b16d4208ea"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("schedule_status", "schedules", type_="check")
    op.create_check_constraint(
        "schedule_status",
        "schedules",
        "status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED')",
    )


def downgrade() -> None:
    op.execute("UPDATE schedules SET status = 'PENDING' WHERE status = 'IN_PROGRESS'")
    op.drop_constraint("schedule_status", "schedules", type_="check")
    op.create_check_constraint(
        "schedule_status",
        "schedules",
        "status IN ('PENDING', 'COMPLETED')",
    )
