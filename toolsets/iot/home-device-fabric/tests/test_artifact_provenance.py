"""Hermetic release-digest checks: no index access or dependency installation."""

import hashlib
import json
import os
import zipfile

import artifact_provenance as mod
import pytest
from artifact_provenance import _release_json

pytestmark = pytest.mark.tc025_02


@pytest.fixture
def wheelhouse(tmp_path, monkeypatch):
    filename = "example-1.0-py3-none-any.whl"
    wheel = tmp_path / filename
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(zipfile.ZipInfo("example-1.0.dist-info/METADATA",
                                          (2026, 1, 1, 0, 0, 0)),
                         "Name: example\nVersion: 1.0\n")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    release = {"urls": [{"filename": filename, "packagetype": "bdist_wheel",
                         "digests": {"sha256": digest},
                         "url": "https://files.pythonhosted.org/packages/" + filename}]}
    calls = []

    def metadata(url):
        calls.append(url)
        return release, hashlib.sha256(json.dumps(release).encode()).hexdigest()

    monkeypatch.setattr(mod, "_release_json", metadata)
    return tmp_path, wheel, release, calls


def test_official_filename_and_bytes_are_recorded(wheelhouse):
    directory, wheel, _, calls = wheelhouse
    records = mod.verify_dependency_wheels(directory)
    assert calls == ["https://pypi.org/pypi/example/1.0/json"]
    assert len(records) == 1
    assert records[0]["sha256"] == records[0]["official_sha256"] == hashlib.sha256(
        wheel.read_bytes()).hexdigest()
    assert records[0]["release_json_url"] == calls[0]
    assert len(records[0]["release_json_sha256"]) == 64


@pytest.mark.parametrize("damage, error", [
    ("bytes", "dependency_digest_mismatch"),
    ("missing", "dependency_release_file_missing_or_ambiguous"),
    ("ambiguous", "dependency_release_file_missing_or_ambiguous"),
    ("sdist", "dependency_release_file_missing_or_ambiguous"),
    ("digest", "invalid_official_dependency_record"),
    ("mirror", "invalid_official_dependency_record"),
    ("extra", "unexpected_dependency_artifact"),
])
def test_bad_artifacts_fail_closed(wheelhouse, damage, error):
    directory, wheel, release, _ = wheelhouse
    if damage == "bytes":
        with wheel.open("ab") as stream:
            stream.write(b"changed")
    elif damage == "missing":
        release["urls"].clear()
    elif damage == "ambiguous":
        release["urls"].append(dict(release["urls"][0]))
    elif damage == "sdist":
        release["urls"][0]["packagetype"] = "sdist"
    elif damage == "digest":
        release["urls"][0]["digests"]["sha256"] = "not-a-digest"
    elif damage == "mirror":
        release["urls"][0]["url"] = "https://mirror.invalid/wheel"
    else:
        (directory / "unexpected.txt").write_text("unverified")
    with pytest.raises(ValueError, match=error):
        mod.verify_dependency_wheels(directory)


def test_metadata_unavailable_cannot_be_accepted(wheelhouse, monkeypatch):
    directory, *_ = wheelhouse

    def unavailable(url):
        raise OSError("fixture index unavailable")

    monkeypatch.setattr(mod, "_release_json", unavailable)
    with pytest.raises(OSError, match="fixture index unavailable"):
        mod.verify_dependency_wheels(directory)


def test_empty_wheelhouse_cannot_be_accepted(tmp_path):
    with pytest.raises(ValueError, match="unexpected_dependency_artifact"):
        mod.verify_dependency_wheels(tmp_path)


@pytest.mark.parametrize("bad, error", [
    ("valid", None),
    ("redirect", "dependency_metadata_redirect"),
    ("oversize", "dependency_metadata_too_large"),
    ("invalid_json", "Expecting value"),
])
def test_release_response_rejections(wheelhouse, monkeypatch, bad, error):
    directory, _, release, _ = wheelhouse
    url = "https://pypi.org/pypi/example/1.0/json"

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return url if bad != "redirect" else "https://mirror.invalid/json"

        def read(self, limit):
            if bad == "oversize":
                return b"x" * limit
            return json.dumps(release).encode() if bad in ("valid", "redirect") else b"not JSON"

    class Opener:
        def open(self, requested, timeout):
            assert requested == url and timeout == 30
            return Response()

    monkeypatch.setattr(mod.urllib.request, "build_opener", lambda *a: Opener())
    monkeypatch.setattr(mod, "_release_json", _release_json)
    if error is None:
        assert len(mod.verify_dependency_wheels(directory)) == 1
    else:
        with pytest.raises(ValueError, match=error):
            mod.verify_dependency_wheels(directory)


@pytest.mark.tc025_03
def test_junit_counts_are_executed_and_grouped(tmp_path):
    report = tmp_path / "results.xml"
    report.write_text('<testsuites><testsuite><testcase name="a"><properties>'
                      '<property name="tc_groups" value="tc024_04,tc025_01"/>'
                      '</properties></testcase><testcase name="b"/></testsuite></testsuites>')
    result, = mod.summarize_test_results([report], [2])
    assert result["totals"] == {"executed": 2, "passed": 2, "failed": 0,
                                "errors": 0, "skipped": 0}
    assert result["per_tc"]["tc025_01"]["executed"] == 1
    assert result["sha256"] == hashlib.sha256(report.read_bytes()).hexdigest()


@pytest.mark.parametrize("outcome", ["failure", "error", "skipped", "empty"])
@pytest.mark.tc025_03
def test_bad_junit_cannot_be_acceptance(tmp_path, outcome):
    report = tmp_path / "results.xml"
    case = "" if outcome == "empty" else f'<testcase><{outcome}/></testcase>'
    report.write_text(f"<testsuites><testsuite>{case}</testsuite></testsuites>")
    with pytest.raises(ValueError, match="test_report_not_passing"):
        mod.summarize_test_results([report], [2])


@pytest.mark.parametrize("damage, error", [
    ("absent", "invalid_dependency_metadata"),
    ("duplicate", "invalid_dependency_metadata"),
    ("oversize", "invalid_dependency_metadata"),
    ("missing_name", "invalid_dependency_identity"),
    ("missing_version", "invalid_dependency_identity"),
])
def test_wheel_metadata_required(wheelhouse, damage, error):
    directory, wheel, _, calls = wheelhouse
    with zipfile.ZipFile(wheel, "w") as archive:
        entries = [] if damage == "absent" else ["example-1.0.dist-info/METADATA"]
        if damage == "duplicate":
            entries.append("other-1.0.dist-info/METADATA")
        payload = ("Version: 1.0\n" if damage == "missing_name" else
                   "Name: example\n" if damage == "missing_version" else
                   "x" * 1_048_577 if damage == "oversize" else
                   "Name: example\nVersion: 1.0\n")
        for entry in entries:
            archive.writestr(zipfile.ZipInfo(entry, (2026, 1, 1, 0, 0, 0)), payload)
    with pytest.raises(ValueError, match=error):
        mod.verify_dependency_wheels(directory)
    assert calls == []


def test_acquisition_ignores_proxy_environment(monkeypatch):
    environment = {"PATH": "/fixture/bin", "PIP_INDEX_URL": "https://mirror.invalid",
                   "pip_extra_index_url": "https://mirror.invalid", "PIP_CONFIG_FILE": "bad"}
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "FTP_PROXY"):
        for key in (name, name.lower()):
            environment[key] = "http://proxy.invalid:9999"
            monkeypatch.setenv(key, environment[key])
    assert mod.dependency_download_environment(environment) == {
        "PATH": "/fixture/bin", "PIP_CONFIG_FILE": os.devnull}
    # Exercise the real opener construction; intercept before any network call.
    seen = []

    def open_without_network(opener, *args, **kwargs):
        seen.append(opener)
        assert not any(isinstance(handler, mod.urllib.request.ProxyHandler)
                       and handler.proxies for handler in opener.handlers)
        raise OSError("network deliberately intercepted")

    monkeypatch.setattr(mod.urllib.request.OpenerDirector, "open", open_without_network)
    with pytest.raises(OSError, match="network deliberately intercepted"):
        mod._release_json("https://pypi.org/pypi/example/1.0/json")
    assert len(seen) == 1


@pytest.mark.tc025_03
@pytest.mark.parametrize("expected", [1, 3])
def test_truncated_or_unexpected_junit_count_rejected(tmp_path, expected):
    report = tmp_path / "results.xml"
    report.write_text('<testsuite><testcase name="a"/><testcase name="b"/></testsuite>')
    with pytest.raises(ValueError, match="test_report_count_mismatch"):
        mod.summarize_test_results([report], [expected])


@pytest.mark.tc025_03
@pytest.mark.parametrize("expected", [[], [0], [-1], [2, 2]])
def test_junit_requires_one_positive_baseline_per_report(tmp_path, expected):
    with pytest.raises(ValueError, match="test_report_expected_counts_required"):
        mod.summarize_test_results([tmp_path / "unused.xml"], expected)
