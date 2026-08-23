from __future__ import annotations


def _manifest(name, path_or_module, source="builtin", *, enabled=True):
    from apeiria.plugin.scanner import PluginManifest

    return PluginManifest(
        name=name,
        path_or_module=path_or_module,
        enabled=enabled,
        source=source,
    )


def test_merge_attaches_metadata_when_matched() -> None:
    from apeiria.web.plugin_metadata import merge_plugin_metadata

    manifests = [_manifest("admin", "apeiria.builtin_plugins.admin")]
    metadata_map = {
        "admin": {
            "name": "管理",
            "description": "管理命令",
            "usage": "/status",
            "type": "application",
            "homepage": "https://example.com",
            "supported_adapters": ["~onebot.v11"],
        }
    }

    result = merge_plugin_metadata(manifests, metadata_map)

    assert len(result) == 1
    row = result[0]
    assert row["name"] == "admin"
    assert row["source"] == "builtin"
    assert row["enabled"] is True
    assert row["path_or_module"] == "apeiria.builtin_plugins.admin"
    assert row["display_name"] == "管理"
    assert row["description"] == "管理命令"
    assert row["usage"] == "/status"
    assert row["type"] == "application"
    assert row["homepage"] == "https://example.com"
    assert row["supported_adapters"] == ["~onebot.v11"]


def test_merge_nulls_metadata_when_unmatched() -> None:
    from apeiria.web.plugin_metadata import merge_plugin_metadata

    manifests = [_manifest("ghost", "some.module", source="local")]

    result = merge_plugin_metadata(manifests, {})

    row = result[0]
    assert row["name"] == "ghost"
    assert row["display_name"] is None
    assert row["description"] is None
    assert row["usage"] is None
    assert row["type"] is None
    assert row["homepage"] is None
    assert row["supported_adapters"] is None


def test_merge_matches_by_module_tail() -> None:
    from apeiria.web.plugin_metadata import merge_plugin_metadata

    manifests = [_manifest("nonebot-plugin-foo", "nonebot_plugin_foo", source="pypi")]
    metadata_map = {
        "nonebot_plugin_foo": {
            "name": "Foo",
            "description": "desc",
            "usage": "usage",
            "type": "application",
            "homepage": "",
            "supported_adapters": None,
        }
    }

    result = merge_plugin_metadata(manifests, metadata_map)

    assert result[0]["display_name"] == "Foo"
    assert result[0]["supported_adapters"] is None


def test_merge_matches_pypi_requirement_string() -> None:
    from apeiria.web.plugin_metadata import merge_plugin_metadata

    manifests = [_manifest("服务器状态查看", "nonebot-plugin-status", source="pypi")]
    metadata_map = {
        "nonebot_plugin_status": {
            "name": "服务器状态",
            "description": "查看服务器状态",
            "usage": "/status",
            "type": "application",
            "homepage": "",
            "supported_adapters": None,
        }
    }

    result = merge_plugin_metadata(manifests, metadata_map)

    assert result[0]["display_name"] == "服务器状态"
    assert result[0]["description"] == "查看服务器状态"
    assert result[0]["type"] == "application"


def test_merge_includes_consistent_module_identifier() -> None:
    from apeiria.web.plugin_metadata import merge_plugin_metadata

    manifests = [
        _manifest("admin", "apeiria.builtin_plugins.admin", source="builtin"),
        _manifest("服务器状态查看", "nonebot-plugin-status>=0.9.0", source="pypi"),
        _manifest("localp", "/abs/plugins/localp", source="local"),
    ]

    rows = merge_plugin_metadata(manifests, {})

    by_name = {r["name"]: r for r in rows}
    assert by_name["admin"]["module"] == "admin"
    assert by_name["服务器状态查看"]["module"] == "nonebot_plugin_status"
    assert by_name["localp"]["module"] == "plugins.localp"


def test_merge_matches_pypi_requirement_with_version_specifier() -> None:
    from apeiria.web.plugin_metadata import merge_plugin_metadata

    manifests = [
        _manifest("status", "nonebot-plugin-status>=0.9.0", source="pypi"),
    ]
    metadata_map = {
        "nonebot_plugin_status": {
            "name": "服务器状态",
            "description": "查看服务器状态",
            "usage": "/status",
            "type": "application",
            "homepage": "",
            "supported_adapters": None,
        }
    }

    result = merge_plugin_metadata(manifests, metadata_map)

    assert result[0]["display_name"] == "服务器状态"


def test_resolve_version_precedence(monkeypatch) -> None:
    from apeiria.plugin import scanner

    def fake_framework() -> str | None:
        return "0.1.0"

    def fake_local(_path) -> str | None:
        return None

    monkeypatch.setattr(scanner, "framework_version", fake_framework)
    monkeypatch.setattr(scanner, "read_local_plugin_version", fake_local)

    # 1. PluginMetadata.extra["version"] wins over everything.
    assert (
        scanner.resolve_version(
            meta={"version": "9.9.9"}, source="dependency", requirement="x"
        )
        == "9.9.9"
    )

    # 2. Dependency falls back to the installed distribution version.
    monkeypatch.setattr(
        scanner, "read_installed_version", lambda req: "0.62.0" if req == "x" else None
    )
    assert (
        scanner.resolve_version(meta={}, source="dependency", requirement="x")
        == "0.62.0"
    )

    # 3. Builtin uses the framework version.
    assert scanner.resolve_version(meta={}, source="builtin") == "0.1.0"

    # 4. Local without declared version -> None.
    assert scanner.resolve_version(meta={}, source="local", path="/tmp/plugin") is None
