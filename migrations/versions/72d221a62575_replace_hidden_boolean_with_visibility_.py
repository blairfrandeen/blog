"""replace hidden boolean with visibility enum

Revision ID: 72d221a62575
Revises: 8725469afee5
Create Date: 2024-03-05 16:01:37.584097

"""
from alembic import op
import sqlalchemy as sa
import enum


# revision identifiers, used by Alembic.
revision = '72d221a62575'
down_revision = '8725469afee5'
branch_labels = None
depends_on = None

class Visibility(enum.IntEnum):
    HIDDEN = 0
    UNLISTED = 1
    PUBLISHED = 2

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('visibility', sa.Enum(Visibility), nullable=False,
                                      server_default = '0'))
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.execute("UPDATE post SET visibility = CASE WHEN hidden = true THEN 'HIDDEN' ELSE 'PUBLISHED' END")
        batch_op.drop_column('hidden')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('hidden', sa.BOOLEAN(), nullable=True))
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.execute("UPDATE post SET hidden = CASE WHEN visibility = 'HIDDEN' THEN true ELSE false END")
        batch_op.drop_column('visibility')

    # ### end Alembic commands ###
