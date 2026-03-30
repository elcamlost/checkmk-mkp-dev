import json
import tarfile

import pytest

from checkmk_mkp_dev import build_mkp

PKG_KWARGS = {
    "name": "my_plugin",
    "title": "My Plugin",
    "author": "Test Author",
    "description": "Test Description",
    "download_url": "https://example.com",
    "version": "1.0.0",
    "min_version": "2.3.0",
}


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    src = tmp_path_factory.mktemp("source")
    (src / "notifications").mkdir()
    (src / "notifications" / "my_plugin").write_text("#!/usr/bin/env python3\npass\n")
    (src / "cmk_addons_plugins" / "my_plugin" / "rulesets").mkdir(parents=True)
    (src / "cmk_addons_plugins" / "my_plugin" / "rulesets" / "params.py").write_text("# ruleset\n")
    return src


@pytest.fixture(scope="module")
def mkp_path(tmp_path_factory, source):
    output = tmp_path_factory.mktemp("output") / "my_plugin.mkp"
    build_mkp(source=source, output=output, **PKG_KWARGS)
    return output


@pytest.fixture(scope="module")
def mkp(mkp_path):
    return tarfile.open(mkp_path, "r:gz")


@pytest.fixture(scope="module")
def info_json(mkp):
    return json.loads(mkp.extractfile("info.json").read())


class TestMkpStructure:
    def test_contains_info(self, mkp):
        assert "info" in mkp.getnames()

    def test_contains_info_json(self, mkp):
        assert "info.json" in mkp.getnames()

    def test_contains_notifications_tar(self, mkp):
        assert "notifications.tar" in mkp.getnames()

    def test_contains_plugins_tar(self, mkp):
        assert "cmk_addons_plugins.tar" in mkp.getnames()


class TestInfoJson:
    def test_name(self, info_json):
        assert info_json["name"] == PKG_KWARGS["name"]

    def test_version(self, info_json):
        assert info_json["version"] == PKG_KWARGS["version"]

    def test_min_required(self, info_json):
        assert info_json["version.min_required"] == PKG_KWARGS["min_version"]

    def test_packaged_equals_min_required(self, info_json):
        assert info_json["version.packaged"] == info_json["version.min_required"]

    def test_usable_until_is_null(self, info_json):
        assert info_json["version.usable_until"] is None

    def test_num_files_matches_files(self, info_json):
        total = sum(len(v) for v in info_json["files"].values())
        assert info_json["num_files"] == total

    def test_files_keys(self, info_json):
        assert set(info_json["files"].keys()) == {"notifications", "cmk_addons_plugins"}


class TestNoPycFiles:
    def test_pyc_excluded(self, tmp_path):
        src = tmp_path / "source"
        (src / "notifications").mkdir(parents=True)
        (src / "notifications" / "script").write_text("pass")
        (src / "notifications" / "__pycache__").mkdir()
        (src / "notifications" / "__pycache__" / "script.cpython-312.pyc").write_bytes(b"\x00")

        output = tmp_path / "test.mkp"
        build_mkp(source=src, output=output, **PKG_KWARGS)

        with tarfile.open(output, "r:gz") as mkp:
            tmp2 = tmp_path / "extracted"
            tmp2.mkdir()
            mkp.extract("notifications.tar", tmp2, filter="data")
            with tarfile.open(tmp2 / "notifications.tar") as ntar:
                assert not any(".pyc" in name for name in ntar.getnames())
                assert not any("__pycache__" in name for name in ntar.getnames())
