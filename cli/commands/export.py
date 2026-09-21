import click

from cli.decorators import json_input_options
from cli.helpers import execute_command
from cli.output import OutputFormatter

EXPORT_FORMATS = ["JPEG", "TIFF", "DNG", "ORIGINAL"]
COLOR_SPACES = ["sRGB", "AdobeRGB", "ProPhotoRGB"]


def _export_options(func):
    func = click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing exported files")(func)
    func = click.option(
        "--filename-suffix",
        default=None,
        help="Suffix to append before the exported file extension",
    )(func)
    func = click.option(
        "--resize-long-edge",
        type=int,
        default=None,
        help="Constrain the long edge to this many pixels",
    )(func)
    func = click.option("--color-space", type=click.Choice(COLOR_SPACES), default=None, help="Output color space")(func)
    func = click.option("--quality", type=click.IntRange(1, 100), default=None, help="JPEG quality from 1 to 100")(func)
    func = click.option(
        "--format",
        "export_format",
        type=click.Choice(EXPORT_FORMATS),
        default=None,
        help="Export format",
    )(func)
    func = click.option("--output-dir", required=True, help="Destination directory for exported files")(func)
    func = click.option("--dry-run", is_flag=True, default=False, help="Preview without executing")(func)
    return func


def _add_common_options(
    params,
    output_dir,
    export_format,
    quality,
    color_space,
    resize_long_edge,
    filename_suffix,
    overwrite,
):
    params["outputDir"] = output_dir
    if export_format is not None:
        params["format"] = export_format
    if quality is not None:
        params["quality"] = quality
    if color_space is not None:
        params["colorSpace"] = color_space
    if resize_long_edge is not None:
        params["resizeLongEdge"] = resize_long_edge
    if filename_suffix:
        params["filenameSuffix"] = filename_suffix
    if overwrite:
        params["overwrite"] = overwrite
    return params


@click.group()
def export():
    """Export commands (photo, batch)"""
    pass


@export.command("photo")
@click.argument("photo_id")
@_export_options
@json_input_options
@click.pass_context
def export_photo(
    ctx,
    photo_id,
    output_dir,
    export_format,
    quality,
    color_space,
    resize_long_edge,
    filename_suffix,
    overwrite,
    dry_run,
    **kwargs,
):
    """Export one photo through Lightroom Classic"""
    params = _add_common_options(
        {"photoId": photo_id},
        output_dir,
        export_format,
        quality,
        color_space,
        resize_long_edge,
        filename_suffix,
        overwrite,
    )
    execute_command(ctx, "export.photo", params, timeout=300.0)


@export.command("batch")
@click.option("--photo-ids", required=True, help="Comma-separated photo IDs")
@_export_options
@json_input_options
@click.pass_context
def export_batch(
    ctx,
    photo_ids,
    output_dir,
    export_format,
    quality,
    color_space,
    resize_long_edge,
    filename_suffix,
    overwrite,
    dry_run,
    **kwargs,
):
    """Export multiple photos through Lightroom Classic"""
    parsed_photo_ids = [photo_id.strip() for photo_id in photo_ids.split(",") if photo_id.strip()]
    if not parsed_photo_ids:
        fmt = ctx.obj.get("output", "text") if ctx.obj else "text"
        click.echo(
            OutputFormatter.format_error(
                "At least one photo id is required",
                fmt,
                code="VALIDATION_ERROR",
            ),
            err=True,
        )
        ctx.exit(2)
        return

    params = _add_common_options(
        {"photoIds": parsed_photo_ids},
        output_dir,
        export_format,
        quality,
        color_space,
        resize_long_edge,
        filename_suffix,
        overwrite,
    )
    execute_command(ctx, "export.batch", params, timeout=900.0)
