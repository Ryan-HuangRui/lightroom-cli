from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_export_module_is_loaded_by_plugin_init():
    plugin_init = (ROOT / "lightroom_sdk" / "plugin" / "PluginInit.lua").read_text(encoding="utf-8")

    assert "require, 'ExportModule'" in plugin_init
    assert "_G.LightroomPythonBridge.ExportModule" in plugin_init


def test_export_commands_are_registered_by_plugin_init():
    plugin_init = (ROOT / "lightroom_sdk" / "plugin" / "PluginInit.lua").read_text(encoding="utf-8")

    assert 'router:register("export.photo", ExportModule.exportPhoto, "sync")' in plugin_init
    assert 'router:register("export.batch", ExportModule.exportBatch, "sync")' in plugin_init


def test_export_module_uses_lr_export_session():
    export_module = (ROOT / "lightroom_sdk" / "plugin" / "ExportModule.lua").read_text(encoding="utf-8")

    assert "LrExportSession" in export_module
    assert "exportRenditions" in export_module
