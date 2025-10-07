from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('patient_intake_form', sa.Column('user_id', sa.Integer(), nullable=False))
    op.create_foreign_key('fk_patient_intake_user', 'patient_intake_form', 'users', ['user_id'], ['id'])

def downgrade():
    op.drop_constraint('fk_patient_intake_user', 'patient_intake_form', type_='foreignkey')
    op.drop_column('patient_intake_form', 'user_id')
