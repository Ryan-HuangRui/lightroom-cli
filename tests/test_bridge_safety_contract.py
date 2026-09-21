"""Safety contract advertised by the running Lightroom bridge."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from cli.main import cli

ROOT = Path(__file__).resolve().parents[1]


def test_plugin_status_advertises_protocol_version_and_capabilities():
    plugin_init = (ROOT / "lightroom_sdk" / "plugin" / "PluginInit.lua").read_text(encoding="utf-8")

    assert 'BRIDGE_PROTOCOL_VERSION = "2"' in plugin_init
    assert "protocolVersion = BRIDGE_PROTOCOL_VERSION" in plugin_init
    assert "capabilities = BRIDGE_CAPABILITIES" in plugin_init
    assert "safe_object_develop_write = false" in plugin_init
    assert "verified_export_result = false" in plugin_init


@patch("cli.helpers.get_bridge")
def test_status_builds_versioned_bridge_contract(mock_get_bridge):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "result": {
            "connected": True,
            "version": "1.2.2",
            "protocolVersion": "2",
            "capabilities": {
                "safe_object_develop_write": False,
                "verified_export_result": False,
            },
        }
    }
    mock_get_bridge.return_value = mock_bridge

    result = CliRunner().invoke(cli, ["-o", "json", "system", "status"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    contract = payload["bridge_contract"]
    assert contract["plugin_version"] == "1.2.2"
    assert contract["protocol_version"] == "2"
    assert contract["version_match"] is True
    assert contract["capabilities"]["safe_object_develop_write"] is False


def test_system_status_schema_exposes_bridge_contract():
    from lightroom_sdk.schema import get_schema

    schema = get_schema("system.status")

    assert schema is not None
    assert "bridge_contract" in schema.response_fields


def test_legacy_apply_has_one_definition_and_reports_actual_success_count():
    develop_module = (ROOT / "lightroom_sdk" / "plugin" / "DevelopModule.lua").read_text(encoding="utf-8")

    assert develop_module.count("function DevelopModule.applySettings(params, callback)") == 1
    assert "applied = appliedCount" in develop_module
