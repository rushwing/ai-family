"""Required imports fail at collection; no environment-gated acceptance skips."""

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fixtures import configuration, token
from home_device_fabric.home_queries import HomeQueryService
from home_device_fabric.state_store import CurrentStateStore
from home_intelligence_api import TokenVerifier, create_app
from starlette.testclient import TestClient


@pytest.fixture(scope="session")
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def setup(signing_key):
    config = configuration()
    store = CurrentStateStore(**config)
    service = HomeQueryService(
        store=store,
        capabilities=[
            {"home_id": "home-example", "device_id": "device-one", "capabilities": []},
        ],
    )
    pem = signing_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    verifier = TokenVerifier(
        issuer="https://idp.example/realm", audience="home-api", public_keys={"test-key": pem}
    )
    clock = [100]
    app = create_app(service=service, verifier=verifier, clock_ms=lambda: clock[0], max_age_ms=10)
    client = TestClient(app)
    return {
        "config": config,
        "store": store,
        "service": service,
        "verifier": verifier,
        "clock": clock,
        "app": app,
        "client": client,
        "headers": {"Authorization": "Bearer " + token(signing_key)},
    }


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter and reporter.stats.get("skipped"):
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
