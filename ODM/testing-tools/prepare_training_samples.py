"""
Prepare individual superpixel examples for the React training workspace.

Responsibilities:
1. Read the actual superpixel label GeoTIFF written by SuperpixelOverlayWriter.
2. Match the same geographic region in aligned RGB and multispectral rasters.
3. Mask pixels outside each region and render both previews as PNG images.
4. Save the previews in a standalone JSON manifest that React can open.

This is a development bridge for labeling, NOT a model-training algorithm.
For very large projects, replace the single JSON manifest with a paginated
Tauri/Python endpoint instead of loading every preview at once.
"""

import argparse
import base64
import json
from collections import defaultdict
from io import BytesIO
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.windows import Window


# ==========================================================
# IMAGE PREVIEW HELPERS
# ==========================================================


def normalize_band(values, mask):
    """Convert a multispectral band to 8-bit display values."""
    valid = values[mask & np.isfinite(values)]
    if valid.size == 0:
        return np.zeros(values.shape, dtype=np.uint8)

    low, high = np.percentile(valid, (2, 98))
    if high <= low:
        high = low + 1

    scaled = (np.nan_to_num(values, nan=float(low)) - low) * (255 / (high - low))
    return np.clip(scaled, 0, 255).astype(np.uint8)


def as_png_uri(channels, mask, max_side):
    """Render a masked three-band crop as an embedded transparent PNG."""
    rgb = np.moveaxis(channels, 0, -1).astype(np.uint8)
    alpha = (mask.astype(np.uint8) * 255)
    image = Image.fromarray(np.dstack([rgb, alpha]), mode="RGBA")
    image.thumbnail((max_side, max_side), Image.Resampling.NEAREST)

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


# ==========================================================
# RASTER PROCESSING
# ==========================================================


def collect_bounds(labels):
    """Collect bounding boxes for all IDs without loading the entire raster."""
    bounds = {}
    counts = defaultdict(int)

    for _, window in labels.block_windows(1):
        block = labels.read(1, window=window)
        for item in np.unique(block):
            label_id = int(item)
            if label_id == 0:  # 0 is nodata in the existing label raster.
                continue
            rows, cols = np.where(block == item)
            if rows.size == 0:
                continue
            top = int(window.row_off) + int(rows.min())
            bottom = int(window.row_off) + int(rows.max()) + 1
            left = int(window.col_off) + int(cols.min())
            right = int(window.col_off) + int(cols.max()) + 1
            counts[label_id] += int(rows.size)

            if label_id not in bounds:
                bounds[label_id] = [left, top, right, bottom]
            else:
                old = bounds[label_id]
                old[0] = min(old[0], left)
                old[1] = min(old[1], top)
                old[2] = max(old[2], right)
                old[3] = max(old[3], bottom)

    return bounds, counts


def require_same_grid(reference, other, name):
    """Make sure preview crops refer to precisely the same pixels."""
    if (
        reference.width != other.width
        or reference.height != other.height
        or reference.crs != other.crs
        or not reference.transform.almost_equals(other.transform)
    ):
        raise ValueError(f"{name} does not match the superpixel label grid.")


def build_manifest(label_path, rgb_path, multispectral_path, output_path, max_side=240, limit=0):
    """Create one isolated RGB and multispectral crop per superpixel label."""
    with rasterio.open(label_path) as labels, \
         rasterio.open(rgb_path) as rgb, \
         rasterio.open(multispectral_path) as ms:

        require_same_grid(labels, rgb, "Aligned RGB orthomosaic")
        require_same_grid(labels, ms, "Multispectral orthomosaic")
        if rgb.count < 3 or ms.count < 3:
            raise ValueError("Both input orthomosaics need at least three bands.")

        boxes, counts = collect_bounds(labels)
        manifest = {
            "version": 1,
            "source": str(label_path.resolve()),
            "multispectralDisplay": "False color: NIR / Red / Green (bands 3 / 1 / 2)",
            "samples": [],
        }

        ordered_ids = sorted(boxes)
        if limit > 0:
            ordered_ids = ordered_ids[:limit]

        for sequence, label_id in enumerate(ordered_ids, start=1):
            left, top, right, bottom = boxes[label_id]
            window = Window(left, top, right - left, bottom - top)
            mask = labels.read(1, window=window) == label_id

            rgb_channels = rgb.read([1, 2, 3], window=window)
            # The original backend assumes band 3=NIR, 1=red and 2=green.
            ms_channels = ms.read([3, 1, 2], window=window)
            ms_display = np.stack([
                normalize_band(band.astype(np.float32), mask)
                for band in ms_channels
            ])

            if rgb_channels.dtype != np.uint8:
                rgb_channels = np.stack([
                    normalize_band(band.astype(np.float32), mask)
                    for band in rgb_channels
                ])

            manifest["samples"].append({
                "id": label_id,
                "pixels": counts[label_id],
                "rgb": as_png_uri(rgb_channels, mask, max_side),
                "multispectral": as_png_uri(ms_display, mask, max_side),
            })
            if sequence % 25 == 0:
                print(f"Prepared {sequence} / {len(ordered_ids)} superpixels", flush=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, separators=(",", ":")), encoding="utf-8")
    print(f"Prepared {len(manifest['samples'])} superpixels: {output_path}")


# ==========================================================
# COMMAND-LINE ENTRY POINT
# ==========================================================


def main():
    parser = argparse.ArgumentParser(description="Prepare labeled superpixel visual previews")
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--rgb", type=Path, required=True)
    parser.add_argument("--multispectral", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-side", type=int, default=240)
    parser.add_argument("--limit", type=int, default=0, help="0 means all superpixels")
    args = parser.parse_args()

    if args.max_side < 16 or args.limit < 0:
        parser.error("max-side must be >=16 and limit must be >=0")

    build_manifest(args.labels, args.rgb, args.multispectral, args.output, max_side=args.max_side, limit=args.limit)


if __name__ == "__main__":
    main()
