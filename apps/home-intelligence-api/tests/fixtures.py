"""Fictional installed/source smoke fixtures; keys generated per execution."""

import time

import jwt


def context(home="home-example", subject="subject-example", member="member-example", role="adult"):
    return {"subject_id": subject, "family_member_id": member, "home_id": home, "role": role}


def configuration():
    def inventory(home):
        return {
            "schema_version": 1,
            "home": {"id": home, "name": "Fictional", "residence_type": "apartment"},
            "floors": [],
            "labels": [],
            "area_groups": [],
            "areas": [
                {
                    "id": area,
                    "home_id": home,
                    "name": "Fictional area",
                    "area_type": "living_room",
                    "floor_id": None,
                }
                for area in ("area-empty", "area-main")
            ],
            "devices": [
                {
                    "id": device,
                    "home_id": home,
                    "name": "Fictional device",
                    "area_id": "area-main" if device == "device-one" else None,
                }
                for device in ("device-two", "device-one")
            ],
        }

    return {
        "inventories": [inventory("home-example"), inventory("home-other")],
        "grants": [
            {**context(), "access": "write"},
            {**context(subject="subject-reader", member="member-reader"), "access": "read"},
            {
                **context(subject="subject-child", member="member-child", role="kid"),
                "access": "read",
            },
            {**context("home-other", subject="subject-other"), "access": "read"},
        ],
    }


def claims(**changes):
    now = int(time.time())
    return {
        "iss": "https://idp.example/realm",
        "aud": "home-api",
        "iat": now - 1,
        "exp": now + 300,
        "sub": "subject-example",
        "family_member_id": "member-example",
        "role": "adult",
        **changes,
    }


def token(key, **changes):
    return jwt.encode(claims(**changes), key, algorithm="RS256", headers={"kid": "test-key"})


def state():
    return {
        "home_id": "home-example",
        "device_id": "device-one",
        "desired_state": None,
        "reported_state": {
            "is_on": {
                "status": "known",
                "value": False,
                "observed_at": "2026-10-23T00:00:00Z",
                "ordering": {"epoch": 1, "sequence": 1},
            },
        },
        "availability": {
            "status": "offline",
            "observed_at": "2026-10-23T00:00:00Z",
            "ordering": {"epoch": 1, "sequence": 1},
        },
    }
