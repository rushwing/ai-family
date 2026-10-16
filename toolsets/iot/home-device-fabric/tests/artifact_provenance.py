"""Fail-closed official-release verification for downloaded dependency wheels."""

import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
import zipfile
from email.parser import BytesParser
from xml.etree import ElementTree

INDEX_URL = "https://pypi.org/simple"


def dependency_download_environment(environment):
    """Ignore pip options and proxy routing, including lowercase proxy aliases."""
    result = {k: v for k, v in environment.items()
              if not k.upper().startswith("PIP_") and not k.upper().endswith("_PROXY")}
    result["PIP_CONFIG_FILE"] = os.devnull
    return result


def summarize_test_results(paths, expected_counts):
    if len(paths) != len(expected_counts) or any(n <= 0 for n in expected_counts):
        raise ValueError("test_report_expected_counts_required")
    reports = []
    for path, expected in zip(paths, expected_counts, strict=True):
        root = ElementTree.parse(path).getroot()
        totals = {"executed": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0}
        groups = {}
        for case in root.iter("testcase"):
            outcome = ("errors" if case.find("error") is not None else
                       "failed" if case.find("failure") is not None else
                       "skipped" if case.find("skipped") is not None else "passed")
            totals[outcome] += 1
            if outcome != "skipped":
                totals["executed"] += 1
            for prop in case.findall("properties/property"):
                if prop.get("name") == "tc_groups":
                    for name in prop.get("value", "").split(","):
                        counts = groups.setdefault(name, dict.fromkeys(totals, 0))
                        counts[outcome] += 1
                        if outcome != "skipped":
                            counts["executed"] += 1
        if (not totals["executed"] or totals["failed"] or totals["errors"]
                or totals["skipped"]):
            raise ValueError("test_report_not_passing")
        if totals["executed"] != expected:
            raise ValueError("test_report_count_mismatch")
        reports.append({"filename": path.name, "expected_executed": expected,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "totals": totals, "per_tc": groups})
    return reports


def _release_json(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=30) as response:
        if response.geturl() != url:
            raise ValueError("dependency_metadata_redirect")
        payload = response.read(2_097_153)
    if len(payload) > 2_097_152:
        raise ValueError("dependency_metadata_too_large")
    return json.loads(payload), hashlib.sha256(payload).hexdigest()


def verify_dependency_wheels(directory):
    """Verify exact filenames and bytes; never install on partial verification.

    Network and metadata errors propagate as build failures. URLs are assembled
    from bounded wheel METADATA fields, never from pip output or mirror config.
    """
    paths = sorted(directory.iterdir())
    if not paths or any(p.suffix != ".whl" or not p.is_file() for p in paths):
        raise ValueError("unexpected_dependency_artifact")
    records = []
    for wheel in paths:
        with zipfile.ZipFile(wheel) as archive:
            entries = [p for p in archive.namelist() if p.endswith(".dist-info/METADATA")]
            if len(entries) != 1 or archive.getinfo(entries[0]).file_size > 1_048_576:
                raise ValueError("invalid_dependency_metadata")
            metadata = BytesParser().parsebytes(archive.read(entries[0]))
        names, versions = metadata.get_all("Name", []), metadata.get_all("Version", [])
        if (len(names) != 1 or len(versions) != 1
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", names[0])
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.!+_-]{0,127}", versions[0])):
            raise ValueError("invalid_dependency_identity")
        name, version = names[0], versions[0]
        url = "https://pypi.org/pypi/" + urllib.parse.quote(name, safe="") + "/" + (
            urllib.parse.quote(version, safe="")) + "/json"
        release, metadata_sha256 = _release_json(url)
        matches = [entry for entry in release["urls"] if entry["filename"] == wheel.name
                   and entry["packagetype"] == "bdist_wheel"]
        if len(matches) != 1:
            raise ValueError("dependency_release_file_missing_or_ambiguous")
        entry = matches[0]
        expected = entry["digests"]["sha256"]
        artifact_url = urllib.parse.urlsplit(entry["url"])
        if (not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)
                or artifact_url.scheme != "https"
                or artifact_url.netloc != "files.pythonhosted.org"
                or artifact_url.query or artifact_url.fragment):
            raise ValueError("invalid_official_dependency_record")
        actual = hashlib.sha256(wheel.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("dependency_digest_mismatch: " + wheel.name)
        records.append({"filename": wheel.name, "name": name, "version": version,
                        "sha256": actual, "official_sha256": expected,
                        "release_json_url": url, "release_json_sha256": metadata_sha256,
                        "official_file_url": entry["url"]})
    return records
