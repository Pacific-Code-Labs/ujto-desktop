"""The bridge only serves the dashboard's origin, cleans up after itself and reports errors."""

import pytest

from ujto_desktop import config
from ujto_desktop.app import start_url
from ujto_desktop.bridge import Bridge


class FakeWindow:
    def __init__(self, url):
        self.url = url
        self.scripts = []

    def get_current_url(self):
        return self.url

    def evaluate_js(self, script):
        self.scripts.append(script)


UPLOAD = {"url": "https://bucket.s3.amazonaws.com/", "fields": {"key": "uploads/u/1/source", "Content-Type": "audio/mp4"}}


def make_bridge(url=None):
    window = FakeWindow(url or f"{config.APP_ORIGIN}/en/new")
    return Bridge(lambda: window), window


def test_refuses_other_origins():
    bridge, _ = make_bridge("https://evil.example.com/")
    with pytest.raises(PermissionError):
        bridge.download_and_upload("job", "https://youtu.be/x", UPLOAD)
    with pytest.raises(PermissionError):
        bridge.probe("https://youtu.be/x")


def test_rejects_bad_input():
    bridge, _ = make_bridge()
    assert bridge.download_and_upload("job", "file:///etc/passwd", UPLOAD) == {"ok": False, "error": "INVALID_URL"}
    assert bridge.download_and_upload("job", "https://youtu.be/x", {"url": "nope"}) == {"ok": False, "error": "INVALID_UPLOAD"}


def test_success_uploads_and_deletes_temp(monkeypatch, tmp_path):
    bridge, window = make_bridge()
    seen = {}

    def fake_download(job_id, url, work_dir):
        seen["dir"] = work_dir
        audio = work_dir / "audio.m4a"
        audio.write_bytes(b"audio")
        return audio

    monkeypatch.setattr(bridge, "_download", fake_download)
    monkeypatch.setattr(bridge, "_upload", lambda job_id, path, upload: seen.setdefault("uploaded", path.read_bytes()))
    assert bridge.download_and_upload("job-1", "https://youtu.be/x", UPLOAD) == {"ok": True}
    assert seen["uploaded"] == b"audio"
    assert not seen["dir"].exists()  # temp folder removed
    assert any("done" in s for s in window.scripts)


def test_failure_still_deletes_temp(monkeypatch):
    bridge, _ = make_bridge()
    seen = {}

    def failing(job_id, url, work_dir):
        seen["dir"] = work_dir
        (work_dir / "partial").write_bytes(b"x")
        raise RuntimeError("DOWNLOAD_FAILED")

    monkeypatch.setattr(bridge, "_download", failing)
    result = bridge.download_and_upload("job-2", "https://youtu.be/x", UPLOAD)
    assert result == {"ok": False, "error": "DOWNLOAD_FAILED"}
    assert not seen["dir"].exists()


def test_cancel(monkeypatch):
    bridge, _ = make_bridge()

    def slow(job_id, url, work_dir):
        bridge.cancel(job_id)
        bridge._check_cancel(job_id)

    monkeypatch.setattr(bridge, "_download", slow)
    assert bridge.download_and_upload("job-3", "https://youtu.be/x", UPLOAD) == {"ok": False, "error": "UPLOAD_CANCELLED"}


def test_upload_posts_form_fields_then_file(monkeypatch, tmp_path):
    bridge, window = make_bridge()
    audio = tmp_path / "audio.m4a"
    audio.write_bytes(b"x" * 1000)
    captured = {}

    class Resp:
        status_code = 204

    def fake_post(url, data, headers, timeout):
        captured["url"] = url
        captured["body"] = data.read()
        captured["type"] = headers["Content-Type"]
        return Resp()

    import requests

    monkeypatch.setattr(requests, "post", fake_post)
    bridge._upload("job-4", audio, UPLOAD)
    body = captured["body"]
    assert captured["url"] == UPLOAD["url"] and captured["type"].startswith("multipart/form-data")
    assert body.index(b'name="key"') < body.index(b'name="file"')  # S3 needs the file last
    assert any("uploading" in s for s in window.scripts)


def test_deep_link_opens_new_with_url():
    url = start_url(["ujto", "ujto://new?url=https%3A%2F%2Fyoutu.be%2Fabc"])
    assert url == f"{config.APP_URL}/en/new?client=desktop&url=https%3A%2F%2Fyoutu.be%2Fabc"
    assert start_url(["ujto"]) == f"{config.APP_URL}/?client=desktop"
    assert start_url(["ujto", "ujto://new?url=javascript:alert(1)"]) == f"{config.APP_URL}/?client=desktop"


def test_store_edition_has_no_downloads(monkeypatch):
    monkeypatch.setattr(config, "DOWNLOADS_ENABLED", False)
    monkeypatch.setattr(config, "EDITION", "store")
    bridge, _ = make_bridge()
    assert bridge.capabilities() == {"edition": "store", "download": False}
    assert bridge.probe("https://youtu.be/x") == {"ok": False, "error": "NOT_AVAILABLE"}
    assert bridge.download_and_upload("job", "https://youtu.be/x", UPLOAD) == {"ok": False, "error": "NOT_AVAILABLE"}


def test_full_edition_capabilities():
    bridge, _ = make_bridge()
    assert bridge.capabilities() == {"edition": config.EDITION, "download": config.DOWNLOADS_ENABLED}
