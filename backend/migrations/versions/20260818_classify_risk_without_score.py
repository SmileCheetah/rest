"""classify risk without a numeric score

Revision ID: 20260818_risk_class
Revises: 20260818_in_progress
"""

import sqlalchemy as sa
from alembic import op

revision = "20260818_risk_class"
down_revision = "20260818_in_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_risk_assessments_risk_level"),
        "risk_assessments",
        type_="check",
    )
    op.execute(
        "UPDATE risk_assessments SET risk_level = 'MOVE_POSSIBLE' "
        "WHERE risk_level = 'SAFE'"
    )
    op.execute(
        "UPDATE risk_assessments SET risk_level = 'REST_RECOMMENDED' "
        "WHERE risk_level = 'CAUTION'"
    )
    op.create_check_constraint(
        op.f("ck_risk_assessments_risk_level"),
        "risk_assessments",
        "risk_level IN "
        "('MOVE_POSSIBLE', 'REST_RECOMMENDED', 'REST_REQUIRED')",
    )
    op.drop_constraint(
        op.f("ck_risk_assessments_risk_score_range"),
        "risk_assessments",
        type_="check",
    )
    op.drop_column("risk_assessments", "risk_score")


def downgrade() -> None:
    op.add_column(
        "risk_assessments",
        sa.Column(
            "risk_score",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.alter_column("risk_assessments", "risk_score", server_default=None)
    op.create_check_constraint(
        op.f("ck_risk_assessments_risk_score_range"),
        "risk_assessments",
        "risk_score BETWEEN 0 AND 100",
    )
    op.drop_constraint(
        op.f("ck_risk_assessments_risk_level"),
        "risk_assessments",
        type_="check",
    )
    op.execute(
        "UPDATE risk_assessments SET risk_level = 'SAFE' "
        "WHERE risk_level = 'MOVE_POSSIBLE'"
    )
    op.execute(
        "UPDATE risk_assessments SET risk_level = 'CAUTION' "
        "WHERE risk_level = 'REST_RECOMMENDED'"
    )
    op.create_check_constraint(
        op.f("ck_risk_assessments_risk_level"),
        "risk_assessments",
        "risk_level IN ('SAFE', 'CAUTION', 'REST_REQUIRED')",
    )
