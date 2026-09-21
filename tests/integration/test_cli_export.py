from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch("cli.helpers.get_bridge")
def test_export_photo_passes_export_options(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "1",
        "success": True,
        "result": {"exported": 1, "files": ["/tmp/out/photo.jpg"]},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(
        cli,
        [
            "export",
            "photo",
            "123",
            "--output-dir",
            "/tmp/out",
            "--format",
            "JPEG",
            "--quality",
            "92",
            "--color-space",
            "sRGB",
            "--resize-long-edge",
            "2048",
            "--filename-suffix",
            "_lumenflow",
            "--overwrite",
        ],
    )

    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "export.photo",
        {
            "photoId": "123",
            "outputDir": "/tmp/out",
            "format": "JPEG",
            "quality": 92,
            "colorSpace": "sRGB",
            "resizeLongEdge": 2048,
            "filenameSuffix": "_lumenflow",
            "overwrite": True,
        },
        timeout=300.0,
    )


@patch("cli.helpers.get_bridge")
def test_export_batch_splits_photo_ids(mock_get_bridge, runner):
    mock_bridge = AsyncMock()
    mock_bridge.send_command.return_value = {
        "id": "2",
        "success": True,
        "result": {"exported": 2, "files": ["/tmp/out/a.jpg", "/tmp/out/b.jpg"]},
    }
    mock_get_bridge.return_value = mock_bridge

    result = runner.invoke(
        cli,
        [
            "export",
            "batch",
            "--photo-ids",
            "123, 456",
            "--output-dir",
            "/tmp/out",
            "--format",
            "JPEG",
        ],
    )

    assert result.exit_code == 0
    mock_bridge.send_command.assert_called_once_with(
        "export.batch",
        {
            "photoIds": ["123", "456"],
            "outputDir": "/tmp/out",
            "format": "JPEG",
        },
        timeout=900.0,
    )


def test_export_batch_rejects_empty_photo_ids(runner):
    result = runner.invoke(cli, ["export", "batch", "--photo-ids", " , ", "--output-dir", "/tmp/out"])

    assert result.exit_code == 2
    assert "photo id" in result.output.lower()
