"""Alembic revisions of the smart home backend.

Every change to the schema of the store is a revision in this package, applied in
order by ``alembic upgrade head``. Nothing else is allowed to create, alter or
drop a table, so a deployment can always be rebuilt from an empty database and a
review reads the schema as a diff.

The revisions themselves live in ``versions``.
"""
