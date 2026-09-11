from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from cli.main import cli
from lightroom_sdk.schema import get_schema


def test_verified_apply_schema_requires_identity_and_precondition():
    schema = get_schema("develop.applySettingsVerified")

    assert schema is not None
    required = {param.name for param in schema.params if param.required}
    assert required == {"photoId", "expectedStateHash", "operationId", "settings"}
    assert {"actualStateHash", "results", "verification"}.issubset(schema.response_fields)


@patch("cli.helpers.get_bridge")
def test_verified_apply_cli_sends_full_contract(mock_get_bridge):
    bridge = AsyncMock()
    bridge.send_command.return_value = {
        "success": False,
        "error": {"code": "CAPABILITY_NOT_VERIFIED", "message": "Not available before real Lightroom validation"},
    }
    mock_get_bridge.return_value = bridge

    result = CliRunner().invoke(
        cli,
        [
            "-o",
            "json",
            "develop",
            "apply-verified",
            "--photo-id",
            "123",
            "--expected-state-hash",
            "abc",
            "--operation-id",
            "op-1",
            "--settings",
            '{"Exposure":0.25}',
        ],
    )

    assert result.exit_code == 1
    bridge.send_command.assert_called_once_with(
        "develop.applySettingsVerified",
        {
            "photoId": "123",
            "expectedStateHash": "abc",
            "operationId": "op-1",
            "settings": {"Exposure": 0.25},
        },
        timeout=30.0,
    )


def test_plugin_registers_fail_closed_verified_apply_handler():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    plugin_init = (root / "lightroom_sdk" / "plugin" / "PluginInit.lua").read_text(encoding="utf-8")
    develop_module = (root / "lightroom_sdk" / "plugin" / "DevelopModule.lua").read_text(encoding="utf-8")

    registration = 'router:register("develop.applySettingsVerified", DevelopModule.applySettingsVerified, "sync")'
    assert registration in plugin_init
    assert "function DevelopModule.applySettingsVerified(params, callback)" in develop_module
    assert "CAPABILITY_NOT_VERIFIED" in develop_module
