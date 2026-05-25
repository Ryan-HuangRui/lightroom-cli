from lightroom_sdk.schema import ParamType, get_schema, get_schemas_by_group


def test_export_photo_schema_exists():
    schema = get_schema("export.photo")

    assert schema is not None
    assert schema.cli_path == "export.photo"
    assert schema.mutating is True
    assert schema.supports_dry_run is True
    assert schema.timeout == 300.0
    assert "files" in schema.response_fields


def test_export_batch_schema_exists():
    schema = get_schema("export.batch")

    assert schema is not None
    assert schema.cli_path == "export.batch"
    assert schema.mutating is True
    assert schema.supports_dry_run is True
    assert schema.timeout == 900.0
    assert "results" in schema.response_fields


def test_export_schema_group_lists_photo_and_batch():
    schemas = get_schemas_by_group("export")
    cli_paths = [schema.cli_path for schema in schemas.values()]

    assert cli_paths == ["export.photo", "export.batch"]


def test_export_photo_quality_is_bounded_integer():
    schema = get_schema("export.photo")
    quality = next(param for param in schema.params if param.name == "quality")

    assert quality.type == ParamType.INTEGER
    assert quality.min == 1
    assert quality.max == 100


def test_export_photo_format_is_enum():
    schema = get_schema("export.photo")
    export_format = next(param for param in schema.params if param.name == "format")

    assert export_format.type == ParamType.ENUM
    assert export_format.enum_values == ["JPEG", "TIFF", "DNG", "ORIGINAL"]
