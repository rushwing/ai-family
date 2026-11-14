"""Fictional single-store + real-PG authority, never a production policy adapter."""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg
from home_device_fabric.state_store import CurrentStateStore
from psycopg import sql
from psycopg.types.json import Jsonb
from state_schema.initial_capabilities import load_initial_capabilities

HOME = "home-example"
NOW = int(datetime(2026, 11, 14, tzinfo=timezone.utc).timestamp() * 1000)
STAMP = "2026-11-14T00:00:00Z"


def context(member="A", role="adult"):
    return {
        "subject_id": "fixture-subject",
        "family_member_id": member,
        "home_id": HOME,
        "role": role,
    }


def configuration():
    inventory = {
        "schema_version": 1,
        "home": {"id": HOME, "name": "Fictional", "residence_type": "other"},
        "floors": [],
        "areas": [],
        "labels": [],
        "area_groups": [],
        "devices": [
            {"id": f"device-{i}", "home_id": HOME, "name": "Fixture", "area_id": None, "labels": []}
            for i in range(8)
        ],
    }
    capabilities = [
        {"home_id": HOME, "device_id": f"device-{i}", "capabilities": [d.to_dict()]}
        for i, d in enumerate(load_initial_capabilities().capabilities)
    ]
    capabilities.append({"home_id": HOME, "device_id": "device-6", "capabilities": []})
    bindings = {
        "schema_version": 1,
        "bindings": [
            {
                "home_id": HOME,
                "device_id": f"device-{i}",
                "provider": "ha",
                "provider_instance_id": "ha-example",
                "mapping": {"entity_ids": [f"switch.fixture_{i}"], "device_registry_id": None},
            }
            for i in range(8)
        ],
    }
    return {"registered_inventory": inventory, "capabilities": capabilities, "bindings": bindings}


def request(**changes):
    return {
        "schema_version": 1,
        "home_id": HOME,
        "device_id": "device-0",
        "capability_id": "home.switchable",
        "capability_version": 1,
        "action_id": "set_on",
        "arguments": {"is_on": True},
        "idempotency_key": "key-fixture",
        "trace_id": "trace-fixture",
        **changes,
    }


def snapshot(device="device-0", status="online", stamp=STAMP, epoch=1, sequence=1):
    return {
        "home_id": HOME,
        "device_id": device,
        "desired_state": None,
        "reported_state": {},
        "availability": {
            "status": status,
            "observed_at": stamp if status != "unknown" else None,
            "ordering": {"epoch": epoch, "sequence": sequence} if status != "unknown" else None,
        },
    }


class FixtureAuthority:
    coordination = "single_store_v1"

    def __init__(self, dsn, store, config):
        self.dsn, self.store, self.config = dsn, store, config
        self.table = "fixture_guard_" + uuid.uuid4().hex
        self.scopes = 0
        self.before_scope = lambda count: None
        self.after_lock = lambda count: None
        self.mutate_result = lambda result: result
        with psycopg.connect(dsn) as conn:
            conn.execute(
                sql.SQL("""CREATE TABLE {} (
                family_member_id text, subject_id text, role text, home_id text, device_id text,
                capability_id text, capability_version int, action_id text,
                granted boolean, generation text, binding jsonb,
                PRIMARY KEY (family_member_id,subject_id,role,home_id,device_id,
                             capability_id,capability_version,action_id))""").format(
                    sql.Identifier(self.table)
                )
            )
            conn.execute(
                sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(
                    sql.Identifier(self.table)
                )
            )
            conn.execute(
                sql.SQL("ALTER TABLE {} FORCE ROW LEVEL SECURITY").format(
                    sql.Identifier(self.table)
                )
            )
            conn.execute(
                sql.SQL(
                    "CREATE POLICY fixture_scope ON {} "
                    "USING (family_member_id=app_current_member()) "
                    "WITH CHECK (family_member_id=app_current_member())"
                ).format(sql.Identifier(self.table))
            )
            # FOR SHARE requires UPDATE privilege. This is a fixture-only table;
            # production policy administration/permissions are outside this slice.
            conn.execute(
                sql.SQL("GRANT SELECT,UPDATE ON {} TO aifam_app").format(sql.Identifier(self.table))
            )
        self.grant(request())
        self.grant(
            request(
                device_id="device-1",
                capability_id="home.positionable",
                action_id="set_position",
                arguments={"position_percent": 50},
            )
        )

    def grant(
        self,
        req,
        *,
        member="A",
        subject="fixture-subject",
        role="adult",
        granted=True,
        generation="generation-1",
    ):
        binding = next(
            (b for b in self.config["bindings"]["bindings"] if b["device_id"] == req["device_id"]),
            None,
        )
        with psycopg.connect(self.dsn) as conn:
            conn.execute(
                sql.SQL(
                    "INSERT INTO {} VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT DO NOTHING"
                ).format(sql.Identifier(self.table)),
                (
                    member,
                    subject,
                    role,
                    req["home_id"],
                    req["device_id"],
                    req["capability_id"],
                    req["capability_version"],
                    req["action_id"],
                    granted,
                    generation,
                    Jsonb(binding),
                ),
            )

    def update(self, *, granted=None, generation=None, binding=None, connection=None):
        def execute(conn):
            if granted is not None:
                conn.execute(
                    sql.SQL("UPDATE {} SET granted=%s").format(sql.Identifier(self.table)),
                    (granted,),
                )
            if generation is not None:
                conn.execute(
                    sql.SQL("UPDATE {} SET generation=%s").format(sql.Identifier(self.table)),
                    (generation,),
                )
            if binding is not None:
                conn.execute(
                    sql.SQL("UPDATE {} SET binding=%s").format(sql.Identifier(self.table)),
                    (Jsonb(binding),),
                )

        if connection is not None:
            execute(connection)
        else:
            with psycopg.connect(self.dsn) as conn:
                execute(conn)

    @contextmanager
    def lease(self, conn, principal, target, timeout_seconds):
        self.scopes += 1
        self.before_scope(self.scopes)
        row = conn.execute(
            sql.SQL(
                "SELECT granted,generation,binding FROM {} WHERE family_member_id=%s "
                "AND subject_id=%s AND role=%s AND home_id=%s AND device_id=%s "
                "AND capability_id=%s AND capability_version=%s AND action_id=%s FOR SHARE"
            ).format(sql.Identifier(self.table)),
            (
                principal["family_member_id"],
                principal["subject_id"],
                principal["role"],
                target["home_id"],
                target["device_id"],
                target["capability_id"],
                target["capability_version"],
                target["action_id"],
            ),
        ).fetchone()
        self.after_lock(self.scopes)
        result = {
            "principal": principal,
            "target": target,
            "granted": row[0] if row else False,
            "generation": row[1] if row else None,
            "binding": row[2] if row else None,
        }
        yield self.mutate_result(json.loads(json.dumps(result)))


class Environment:
    def __init__(self, dsn):
        self.config = configuration()
        self.clock = [NOW]
        self.store = CurrentStateStore(
            inventories=[self.config["registered_inventory"]],
            grants=[
                context(member, role) | {"access": "write"}
                for member, role in (("A", "adult"), ("A", "admin"), ("B", "adult"))
            ],
        )
        self.store.rebuild(
            context(),
            home_id=HOME,
            states={"schema_version": 1, "states": [snapshot(f"device-{i}") for i in range(8)]},
            now_ms=NOW,
        )
        self.store.advance_epoch(context(), home_id=HOME, epoch=1)
        self.authority = FixtureAuthority(dsn, self.store, self.config)
        self.dsn = dsn

    def guard(self, **changes):
        from gateway.home_guard import HomeActionGuard

        return HomeActionGuard(
            **(
                dict(
                    dsn=self.dsn,
                    **self.config,
                    provider_instance_id="ha-example",
                    configuration_generation="generation-1",
                    authority=self.authority,
                    store=self.store,
                    clock=lambda: self.clock[0],
                    max_availability_age_ms=1000,
                )
                | changes
            )
        )
