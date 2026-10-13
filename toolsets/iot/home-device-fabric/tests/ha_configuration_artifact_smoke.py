"""Installed-only independent configuration smoke, effective under -I and -O."""

import dataclasses
import hashlib
import json
import pickle
import sys

from home_device_fabric.ha_configuration import HAConfiguration, HAConfigurationError


def require(condition):
    if not condition:
        raise RuntimeError("installed_configuration_check_failed")


def main():
    token = "fictional-prefix-" + "T" * 203 + "-suffix-marker"
    settings = {"schema_version": 1, "base_url": "HTTPS://PRIVATE-FICTIONAL.INVALID:443/"}
    config = HAConfiguration(settings, access_token=token)
    expected = {
        "schema_version": 1, "base_url": "<redacted-endpoint>", "access_token": "<redacted>",
        "request_timeout_ms": 10000, "reconnect_initial_delay_ms": 1000,
        "reconnect_max_delay_ms": 30000, "reconnect_max_attempts": 8,
    }
    require(config.base_url == "https://private-fictional.invalid:443")
    require(config.access_token_for_transport() == token)
    require(config.to_redacted_dict() == expected)
    require(json.loads(config.to_redacted_json()) == expected)
    require(config.reconnect_delays_ms() == (1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000))
    settings["base_url"] = "http://mutated.invalid"
    config.to_redacted_dict()["request_timeout_ms"] = -1
    require(config.to_redacted_dict() == expected)
    output = repr([config]) + str(config) + config.to_redacted_json()
    refused = 0
    for operation in (vars, dataclasses.asdict, json.dumps, pickle.dumps,
                      lambda value: value.__getstate__(), lambda value: value.__reduce__()):
        try:
            operation(config)
        except TypeError as exc:
            refused += 1
            output += str(exc)
        else:
            raise RuntimeError("raw_configuration_export_allowed")
    require(refused == 6)
    rejected = 0
    for data, credential, code, path in (
        ({"schema_version": 1, "base_url": "http://[private-marker]"}, token,
         "invalid_endpoint", ("settings", "base_url")),
        ({"schema_version": 1, "base_url": "http://h.invalid", "private-marker": "private"}, token,
         "unknown_field", ("settings", "<unknown>")),
        ({"schema_version": 1, "base_url": "http://h.invalid", "request_timeout_ms": True}, token,
         "invalid_setting", ("settings", "request_timeout_ms")),
        ({"schema_version": 1, "base_url": "http://h.invalid"}, "private-marker\n",
         "invalid_token", ("access_token",)),
    ):
        try:
            HAConfiguration(data, access_token=credential)
        except HAConfigurationError as exc:
            require(exc.code == code and exc.path == path)
            require(exc.__context__ is None and exc.__cause__ is None)
            output += str(exc) + repr(exc)
            rejected += 1
        else:
            raise RuntimeError("invalid_configuration_accepted")
    require(rejected == 4)
    for marker in (token, "fictional-prefix", "suffix-marker", str(len(token)),
                   hashlib.sha256(token.encode()).hexdigest(), "private-marker",
                   "private-fictional.invalid"):
        require(marker not in output)
    try:
        config.base_url = "http://mutation.invalid"
    except AttributeError:
        pass
    else:
        raise RuntimeError("mutable_configuration")
    print(json.dumps({"python": sys.version, "optimized": not __debug__,
                      "rejected": rejected, "refused_exports": refused,
                      "schedule_count": 8, "redaction": True}, sort_keys=True))


if __name__ == "__main__":
    main()
