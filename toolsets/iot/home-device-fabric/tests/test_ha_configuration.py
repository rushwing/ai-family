"""Independent literal REQ-022 expectations; no runtime validators as oracles."""

import copy
import dataclasses
import hashlib
import importlib
import json
import logging
import pickle
from types import SimpleNamespace

import pytest

DEFAULT_SETTINGS = object()
TOKEN = "fictional-prefix-SAMPLE-credential-suffix-7391"
URL = "https://fictional-private-host.invalid:443"
SNAPSHOT = {
    "schema_version": 1, "base_url": "<redacted-endpoint>", "access_token": "<redacted>",
    "request_timeout_ms": 10000, "reconnect_initial_delay_ms": 1000,
    "reconnect_max_delay_ms": 30000, "reconnect_max_attempts": 8,
}


def runtime():
    return importlib.import_module("home_device_fabric.ha_configuration")


def settings(**changes):
    return {"schema_version": 1, "base_url": URL, **changes}


def construct(data=DEFAULT_SETTINGS, token=TOKEN):
    return runtime().HAConfiguration(
        settings() if data is DEFAULT_SETTINGS else data, access_token=token)


def error(data, code, path, token=TOKEN):
    with pytest.raises(runtime().HAConfigurationError) as caught:
        construct(data, token)
    exc = caught.value
    assert exc.code == code and exc.path == path
    assert exc.args == (code + ": " + ".".join(path),)
    assert exc.__cause__ is None and exc.__context__ is None
    return exc


@pytest.mark.tc022_01
def test_construction_defaults_isolation_and_exports():
    import home_device_fabric

    data = settings()
    first = construct(data)
    second = construct(settings(base_url="http://other.invalid"), "other-fictional-token")
    data["base_url"] = "http://mutated.invalid"
    exported = first.to_redacted_dict()
    exported["request_timeout_ms"] = -1
    assert first.to_redacted_dict() == SNAPSHOT
    assert first.base_url == URL and first.schema_version == 1
    assert first.access_token_for_transport() == TOKEN
    assert second.base_url == "http://other.invalid"
    assert second.access_token_for_transport() == "other-fictional-token"
    assert home_device_fabric.__all__ == ["Delivery", "MockProvider", "ProviderProtocol"]
    assert not dataclasses.is_dataclass(first)
    assert not hasattr(first, "__dict__") and not hasattr(first, "to_dict")


@pytest.mark.tc022_01
@pytest.mark.parametrize("name", [
    "base_url", "schema_version", "request_timeout_ms", "reconnect_initial_delay_ms",
    "reconnect_max_delay_ms", "reconnect_max_attempts", "_HAConfiguration__endpoint",
    "_HAConfiguration__numbers", "_HAConfiguration__credential", "arbitrary",
])
def test_immutable_assignment_and_deletion(name):
    config = construct()
    with pytest.raises(AttributeError, match="^immutable_configuration$"):
        setattr(config, name, "fictional-mutation")
    with pytest.raises(AttributeError, match="^immutable_configuration$"):
        delattr(config, name)
    with pytest.raises(AttributeError, match="^immutable_configuration$"):
        config.__init__(settings(), access_token="replacement")
    assert config.to_redacted_dict() == SNAPSHOT and config.access_token_for_transport() == TOKEN


@pytest.mark.tc022_01
@pytest.mark.parametrize("data,code,path", [
    ([], "invalid_settings", ("settings",)),
    (None, "invalid_settings", ("settings",)),
    ("fictional-private-input", "invalid_settings", ("settings",)),
    ({1: "private"}, "invalid_settings", ("settings",)),
    ({}, "missing_field", ("settings", "schema_version")),
    ({"schema_version": 1}, "missing_field", ("settings", "base_url")),
    (settings(access_token="embedded-private"), "unknown_field", ("settings", "<unknown>")),
    (settings(**{"private-key-marker": 1}), "unknown_field", ("settings", "<unknown>")),
    (settings(schema_version=2), "unsupported_version", ("settings", "schema_version")),
    (settings(schema_version=True), "invalid_setting", ("settings", "schema_version")),
    (settings(schema_version="1"), "invalid_setting", ("settings", "schema_version")),
    (settings(base_url=1), "invalid_setting", ("settings", "base_url")),
])
def test_settings_errors(data, code, path):
    error(data, code, path)


@pytest.mark.tc022_01
def test_subclass_hooks_never_run():
    class HostileStr(str):
        def __str__(self):
            raise AssertionError("hostile str invoked")

        def __hash__(self):
            raise AssertionError("hostile hash invoked")

    class HostileDict(dict):
        def __iter__(self):
            raise AssertionError("hostile dict invoked")

    class HostileInt(int):
        def __lt__(self, other):
            raise AssertionError("hostile numeric invoked")

    error(HostileDict(), "invalid_settings", ("settings",))
    error(settings(base_url=HostileStr(URL)), "invalid_setting", ("settings", "base_url"))
    error(settings(schema_version=HostileInt(1)), "invalid_setting", ("settings", "schema_version"))
    error(settings(), "invalid_token", ("access_token",), HostileStr(TOKEN))


@pytest.mark.tc022_02
@pytest.mark.parametrize("raw,normalized", [
    ("HTTP://EXAMPLE.INVALID/", "http://example.invalid"),
    ("https://h.invalid:443/", "https://h.invalid:443"),
    ("http://h.invalid:80/", "http://h.invalid:80"),
    ("https://h.invalid:00443/", "https://h.invalid:00443"),
    ("http://h.invalid:1", "http://h.invalid:1"),
    ("http://h.invalid:65535", "http://h.invalid:65535"),
    ("http://127.0.0.1/", "http://127.0.0.1"),
    ("https://255.255.255.255", "https://255.255.255.255"),
    ("http://0.0.0.0", "http://0.0.0.0"),
    ("https://[2001:DB8::A]:443/", "https://[2001:db8::a]:443"),
    ("http://[::1]", "http://[::1]"),
    ("http://[::ffff:192.0.2.1]", "http://[::ffff:192.0.2.1]"),
    ("http://singlelabel", "http://singlelabel"),
    ("https://a-b.9example.invalid", "https://a-b.9example.invalid"),
    ("http://" + "a" * 63 + ".invalid", "http://" + "a" * 63 + ".invalid"),
    ("http://" + ".".join(["a" * 63] * 3 + ["a" * 61]),
     "http://" + ".".join(["a" * 63] * 3 + ["a" * 61])),
    ("http://h.invalid:" + "0" * 2030 + "1", "http://h.invalid:" + "0" * 2030 + "1"),
])
def test_normalized_endpoint(raw, normalized):
    assert construct(settings(base_url=raw)).base_url == normalized


@pytest.mark.tc022_02
@pytest.mark.parametrize("raw", [
    "", "http://", "//h.invalid", "h.invalid", "ftp://h.invalid", "https:h.invalid",
    "https:///h.invalid", "http://user:private@h.invalid", "http://@h.invalid",
    "http://h.invalid?", "http://h.invalid?private", "http://h.invalid#", "http://h.invalid#private",
    "http://h.invalid/path", "http://h.invalid//", "http://h.invalid/.",
    "http://h.invalid\\private", "http://h.invalid/%", "http://h.invalid/%GG",
    "http://%68.invalid", "http://h%2einvalid", "http://h.invalid:",
    "http://h.invalid:0", "http://h.invalid:65536", "http://h.invalid:-1",
    "http://h.invalid:+80", "http://h.invalid:1.0", "http://h.invalid:８０",
    "http:// h.invalid", "http://h.invalid ", "http://h.invalid\n", "http://h.invalid\x00",
    "http://é.invalid", "http://h..invalid", "http://.h.invalid", "http://h.invalid.",
    "http://-h.invalid", "http://h-.invalid", "http://h_1.invalid",
    "http://" + "a" * 64 + ".invalid",
    "http://" + ".".join(["a" * 63] * 4),
    "http://127.000.0.1", "http://256.0.0.1", "http://127.1", "http://2130706433",
    "http://1.2.3.4.5", "http://0x7f.0.0.1", "http://[::1", "http://::1",
    "http://[::1]]", "http://[bad::gg]", "http://[::1]private", "http://[::1]:",
    "http://[fe80::1%eth0]", "http://[fe80::1%25eth0]", "http://[127.0.0.1]",
    "http://h.invalid:" + "0" * 2031 + "1", "http://h.invalid:" + "9" * 1900,
])
def test_endpoint_rejections(raw):
    exc = error(settings(base_url=raw), "invalid_endpoint", ("settings", "base_url"))
    assert raw not in str(exc) if raw else True


@pytest.mark.tc022_03
@pytest.mark.parametrize("token", [None, "", " ", "with space", "\t", "a\n", "\x00",
                                         "\x7f", "é", "😀", "a" * 8193, 1, False, [], {}])
def test_invalid_tokens(token):
    error(settings(), "invalid_token", ("access_token",), token)


@pytest.mark.tc022_03
def test_missing_token():
    with pytest.raises(runtime().HAConfigurationError) as caught:
        runtime().HAConfiguration(settings())
    assert caught.value.code == "missing_token" and caught.value.path == ("access_token",)


@pytest.mark.tc022_03
@pytest.mark.parametrize("token", ["!", "~" * 8192, "fictional.JWT-like_A-z.123",
                                   "".join(chr(i) for i in range(33, 127))])
def test_valid_token_bounds(token):
    config = construct(token=token)
    assert config.access_token_for_transport() == token
    assert config.to_redacted_dict() == SNAPSHOT


@pytest.mark.tc022_03
def test_supported_inspection_serialization_and_logs(caplog, monkeypatch):
    # Caller logging is explicit test orchestration. Supply a fixed logging-only
    # timestamp while the runtime's actual time module remains denied.
    monkeypatch.setattr(logging, "time", SimpleNamespace(time=lambda: 0.0, time_ns=lambda: 0))
    token = "fictional-prefix-" + "T" * 203 + "-suffix-marker"
    config = construct(token=token)
    output = [repr(config), str(config), repr([config]), repr({"config": config}),
              str(config.to_redacted_dict()), config.to_redacted_json()]
    assert json.loads(config.to_redacted_json()) == SNAPSHOT
    assert config.to_redacted_json() == json.dumps(SNAPSHOT, sort_keys=True, separators=(",", ":"))
    for operation in (vars, dataclasses.asdict, json.dumps, pickle.dumps, copy.copy, copy.deepcopy,
                      lambda value: value.__getstate__(), lambda value: value.__reduce__()):
        with pytest.raises(TypeError) as caught:
            operation(config)
        output.extend([str(caught.value), repr(caught.value)])
    # Directly inspect the internal wrapper only to prove its repr/serialization
    # behavior. Reading its private value is expressly outside the public surface.
    secret = object.__getattribute__(config, "_HAConfiguration__credential")
    output.extend([repr(secret), repr([secret])])
    for operation in (vars, dataclasses.asdict, json.dumps, pickle.dumps, copy.copy, copy.deepcopy,
                      lambda value: value.__getstate__(), lambda value: value.__reduce__()):
        with pytest.raises(TypeError) as caught:
            operation(secret)
        output.append(str(caught.value))
    with caplog.at_level(logging.INFO):
        logging.getLogger("req022-test").info("configuration=%s %r", config, [config])
    output.append(caplog.text)
    rendered = "\n".join(output)
    for marker in (token, "fictional-prefix", "suffix-marker",
                   hashlib.sha256(token.encode()).hexdigest(),
                   str(len(token)), URL, "fictional-private-host", "token_length", "token_hash"):
        assert marker not in rendered
    assert config.to_redacted_dict() == SNAPSHOT


@pytest.mark.tc022_03
@pytest.mark.parametrize("case", ["url", "key", "token", "number"])
def test_value_free_errors_and_chains(case, caplog, monkeypatch):
    monkeypatch.setattr(logging, "time", SimpleNamespace(time=lambda: 0.0, time_ns=lambda: 0))
    private = "fictional-private-value-unique-6839"
    data, token = settings(), private
    if case == "url":
        data["base_url"] = "http://[" + private + "]"
    elif case == "key":
        data[private] = private
    elif case == "number":
        data["request_timeout_ms"] = private
    else:
        token = private + "\n"
    with pytest.raises(runtime().HAConfigurationError) as caught:
        construct(data, token)
    exc = caught.value
    assert exc.__cause__ is None and exc.__context__ is None
    with caplog.at_level(logging.INFO):
        logging.getLogger("req022-test").info("rejection=%s %r", exc, exc)
    rendered = repr(exc) + str(exc) + repr(vars(exc)) + repr(exc.args) + caplog.text
    assert private not in rendered and URL not in rendered


@pytest.mark.tc022_04
@pytest.mark.parametrize("field,low,high", [
    ("request_timeout_ms", 1, 120000), ("reconnect_initial_delay_ms", 1, 60000),
    ("reconnect_max_delay_ms", 1, 300000), ("reconnect_max_attempts", 1, 32),
])
@pytest.mark.parametrize("boundary", ["low", "high", "below", "above"])
def test_integer_boundaries(field, low, high, boundary):
    value = {"low": low, "high": high, "below": low - 1, "above": high + 1}[boundary]
    data = settings(**{field: value})
    if field == "reconnect_initial_delay_ms":
        data["reconnect_max_delay_ms"] = 300000
    if field == "reconnect_max_delay_ms":
        data["reconnect_initial_delay_ms"] = 1
    if boundary in ("below", "above"):
        error(data, "out_of_bounds", ("settings", field))
    else:
        assert getattr(construct(data), field) == value


@pytest.mark.tc022_04
@pytest.mark.parametrize("field", ["request_timeout_ms", "reconnect_initial_delay_ms",
                                  "reconnect_max_delay_ms", "reconnect_max_attempts"])
@pytest.mark.parametrize("value", [None, True, False, 1.0, 1.5, "1", float("nan"),
                                  float("inf"), float("-inf")])
def test_strict_integer_no_coercion(field, value):
    error(settings(**{field: value}), "invalid_setting", ("settings", field))


@pytest.mark.tc022_04
@pytest.mark.parametrize("initial,maximum,attempts,expected", [
    (1000, 30000, 8, (1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000)),
    (1, 1, 1, (1,)), (1, 1, 32, (1,) * 32),
    (60000, 300000, 4, (60000, 120000, 240000, 300000)),
    (60000, 300000, 32, (60000, 120000, 240000) + (300000,) * 29),
    (1000, 1000, 3, (1000, 1000, 1000)), (7, 20, 4, (7, 14, 20, 20)),
])
def test_schedule_literal_budget(initial, maximum, attempts, expected):
    config = construct(settings(reconnect_initial_delay_ms=initial,
                                reconnect_max_delay_ms=maximum, reconnect_max_attempts=attempts))
    first = config.reconnect_delays_ms()
    assert type(first) is tuple and all(type(n) is int for n in first)
    assert first == expected and len(first) == attempts and first[-1] == expected[-1]
    assert config.reconnect_delays_ms() == expected


@pytest.mark.tc022_04
def test_order_and_default_schedule():
    error(settings(reconnect_initial_delay_ms=30001), "invalid_reconnect_order",
          ("settings", "reconnect_max_delay_ms"))
    assert construct().reconnect_delays_ms() == (1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000)


@pytest.mark.tc022_05
def test_counted_file_environment_datetime_denial(monkeypatch, offline):
    import builtins
    import datetime
    import io
    import os
    from collections.abc import Mapping

    module = runtime()  # Normal imports precede file denial.
    data = settings()
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(1)
        raise AssertionError("ambient access denied")

    class DeniedEnvironment(Mapping):
        __getitem__ = deny
        __iter__ = deny
        __len__ = deny

    class DeniedDatetime(datetime.datetime):
        now = classmethod(deny)
        utcnow = classmethod(deny)
        today = classmethod(deny)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", deny)
        patch.setattr(io, "open", deny)
        patch.setattr(os, "environ", DeniedEnvironment())
        patch.setattr(datetime, "datetime", DeniedDatetime)
        config = module.HAConfiguration(data, access_token=TOKEN)
        assert config.to_redacted_dict() == SNAPSHOT
        assert config.reconnect_delays_ms() == (1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000)
        assert config.access_token_for_transport() == TOKEN
        config.to_redacted_json()
        repr(config)
        for malformed in (settings(base_url="http://[malformed]"), settings(private="marker"),
                          settings(request_timeout_ms=None)):
            with pytest.raises(module.HAConfigurationError):
                module.HAConfiguration(malformed, access_token=TOKEN)
    assert attempts == [] and offline == []


@pytest.mark.tc022_04
@pytest.mark.parametrize("field", ["request_timeout_ms", "reconnect_initial_delay_ms",
                                  "reconnect_max_delay_ms", "reconnect_max_attempts"])
@pytest.mark.parametrize("value", [-1, -1000, 10**100])
def test_negative_and_extreme_integers(field, value):
    error(settings(**{field: value}), "out_of_bounds", ("settings", field))
