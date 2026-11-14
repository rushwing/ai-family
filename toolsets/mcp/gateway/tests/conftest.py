"""Allow gateway and goal_mcp packages to be tested in-place."""

import sys
from pathlib import Path

_GATEWAY_ROOT = Path(__file__).resolve().parents[1]
_GOAL_MCP_ROOT = _GATEWAY_ROOT.parent / "goal-mcp"

for path in (_GATEWAY_ROOT, _GOAL_MCP_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


import os  # noqa: E402
import uuid  # noqa: E402

import psycopg  # noqa: E402
import pytest  # noqa: E402
from psycopg import sql  # noqa: E402
from psycopg.conninfo import make_conninfo  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="session")
def pg_dsn():
    admin_dsn = os.getenv("AIFAMILY_CONFIRMATION_TEST_DSN")
    if not admin_dsn:
        if os.getenv("AIFAMILY_REQUIRE_CONFIRMATION_PG") == "1":
            pytest.fail("AIFAMILY_CONFIRMATION_TEST_DSN required")
        pytest.skip("dedicated PostgreSQL required for durable confirmation tests")
    database = "confirmation_test_" + uuid.uuid4().hex
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    dsn = make_conninfo(admin_dsn, dbname=database)
    try:
        with psycopg.connect(dsn) as conn:
            for path in sorted((ROOT / "data/migrations").glob("*.sql")):
                conn.execute(path.read_text())
            # Repeat all migrations: idempotent upgrade, no dropped records.
            for path in sorted((ROOT / "data/migrations").glob("*.sql")):
                conn.execute(path.read_text())
        yield dsn
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database)))
