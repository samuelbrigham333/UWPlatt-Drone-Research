from pathlib import Path

import numpy as np
import rasterio

from PIL import Image
from rasterio.enums import ColorInterp, Resampling


class OrthomosaicPreviewService:
    """
    Reads an orthomosaic GeoTIFF and creates a displayable PNG preview.

    The generated PNG is for visualization only.
    The original GeoTIFF remains the source of truth for raster
    coordinates, pixel values, and spatial metadata.
    """

    DEFAULT_MAX_DIMENSION = 6000
    DEFAULT_RESAMPLING = Resampling.lanczos

    @staticmethod
    def inspect_raster(raster_path: str | Path) -> dict:
        """Return basic information about a raster."""

        path = Path(raster_path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Raster not found: {path}")

        with rasterio.open(path) as dataset:
            return {
                "path": str(path),
                "width": dataset.width,
                "height": dataset.height,
                "band_count": dataset.count,
                "crs": str(dataset.crs),
                "transform": dataset.transform,
                "color_interpretation": dataset.colorinterp,
                "band_descriptions": dataset.descriptions,
                "data_types": dataset.dtypes,
                "nodata": dataset.nodata,
            }

    @staticmethod
    def _calculate_preview_dimensions(
        width: int,
        height: int,
        max_dimension: int,
    ) -> tuple[int, int]:
        """Calculate resized dimensions while preserving aspect ratio."""

        if max_dimension <= 0:
            raise ValueError("max_dimension must be greater than zero.")

        scale = min(1.0, max_dimension / max(width, height))

        preview_width = max(1, round(width * scale))
        preview_height = max(1, round(height * scale))

        return preview_width, preview_height

    @staticmethod
    def _print_band_statistics(
        band_data: np.ndarray,
        band_index: int,
    ) -> None:
        """Print useful statistics for a raster band."""

        values = band_data[np.isfinite(band_data)]

        if values.size == 0:
            print(f"Band {band_index}: no valid values")
            return

        percentiles = np.percentile(values, [2, 50, 98])

        print(
            f"Band {band_index}: "
            f"min={values.min():.2f}, "
            f"p2={percentiles[0]:.2f}, "
            f"median={percentiles[1]:.2f}, "
            f"p98={percentiles[2]:.2f}, "
            f"max={values.max():.2f}"
        )

    @staticmethod
    def read_rgb(
        raster_path: str | Path,
        rgb_bands: tuple[int, int, int] = (1, 2, 3),
        max_dimension: int = DEFAULT_MAX_DIMENSION,
        resampling: Resampling = DEFAULT_RESAMPLING,
    ) -> np.ndarray:
        """
        Read RGB and optional alpha bands from a GeoTIFF.

        Returns a channel-first RGBA array:
            (4, height, width)

        Transparent and invalid pixels are represented with alpha = 0.
        """

        path = Path(raster_path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Raster not found: {path}")

        if len(rgb_bands) != 3:
            raise ValueError("Exactly three RGB band indexes are required.")

        with rasterio.open(path) as dataset:

            if dataset.count < 3:
                raise ValueError(
                    f"Raster must contain at least 3 bands. "
                    f"Found {dataset.count}."
                )

            color_interpretation = dataset.colorinterp

            print("\n--- Raster Information ---")
            print(f"Dimensions: {dataset.width} x {dataset.height}")
            print(f"Band count: {dataset.count}")
            print(f"Color interpretation: {color_interpretation}")
            print(f"Band descriptions: {dataset.descriptions}")
            print(f"Data types: {dataset.dtypes}")
            print(f"Nodata: {dataset.nodata}")

            # Identify RGB and alpha bands from metadata.
            red_band = None
            green_band = None
            blue_band = None
            alpha_band = None

            for index, interpretation in enumerate(
                color_interpretation,
                start=1,
            ):
                if interpretation == ColorInterp.red:
                    red_band = index

                elif interpretation == ColorInterp.green:
                    green_band = index

                elif interpretation == ColorInterp.blue:
                    blue_band = index

                elif interpretation == ColorInterp.alpha:
                    alpha_band = index

            if all(
                band is not None
                for band in (red_band, green_band, blue_band)
            ):
                selected_rgb_bands = (
                    red_band,
                    green_band,
                    blue_band,
                )

                print(
                    f"Using metadata RGB bands: {selected_rgb_bands}"
                )

            else:
                selected_rgb_bands = rgb_bands

                print(
                    "WARNING: Raster metadata does not identify "
                    "all three RGB channels."
                )
                print(
                    f"Using configured RGB bands: {selected_rgb_bands}"
                )
                print(
                    "Verify that these bands are actually "
                    "red, green, and blue."
                )

            # Validate band indexes.
            for band in selected_rgb_bands:
                if band < 1 or band > dataset.count:
                    raise ValueError(
                        f"Invalid RGB band index {band}. "
                        f"Raster contains {dataset.count} bands."
                    )

            # Calculate preview dimensions.
            preview_width, preview_height = (
                OrthomosaicPreviewService._calculate_preview_dimensions(
                    dataset.width,
                    dataset.height,
                    max_dimension,
                )
            )

            print(f"Preview dimensions: {preview_width} x {preview_height}")
            print(f"Resampling method: {resampling.name}")

            # Read RGB bands.
            rgb_data = dataset.read(
                indexes=list(selected_rgb_bands),
                out_shape=(
                    3,
                    preview_height,
                    preview_width,
                ),
                resampling=resampling,
            )

            # Read validity masks for RGB bands.
            # This excludes nodata and masked pixels from the preview.
            rgb_masks = dataset.read_masks(
                indexes=list(selected_rgb_bands),
                out_shape=(
                    3,
                    preview_height,
                    preview_width,
                ),
                resampling=Resampling.nearest,
            )

            valid_mask = np.all(rgb_masks > 0, axis=0)

            # Print RGB statistics.
            for channel_index, band_index in enumerate(
                selected_rgb_bands
            ):
                print(
                    f"\nRGB channel {channel_index + 1} "
                    f"(source band {band_index}):"
                )

                channel = rgb_data[channel_index]
                valid_values = channel[
                    valid_mask & np.isfinite(channel)
                ]

                if valid_values.size:
                    percentiles = np.percentile(
                        valid_values,
                        [2, 50, 98],
                    )

                    print(f"Min: {valid_values.min()}")
                    print(f"2nd percentile: {percentiles[0]}")
                    print(f"Median: {percentiles[1]}")
                    print(f"98th percentile: {percentiles[2]}")
                    print(f"Max: {valid_values.max()}")

            # Read alpha if the raster has an alpha band.
            if alpha_band is not None:
                print(f"\nAlpha band: {alpha_band}")

                alpha_data = dataset.read(
                    alpha_band,
                    out_shape=(
                        preview_height,
                        preview_width,
                    ),
                    resampling=resampling,
                )

                OrthomosaicPreviewService._print_band_statistics(
                    alpha_data,
                    alpha_band,
                )

                # Exclude invalid RGB pixels.
                alpha_data = alpha_data.copy()
                alpha_data[~valid_mask] = 0

            else:
                print("\nNo alpha band identified.")

                # Opaque where RGB data is valid, transparent otherwise.
                alpha_data = np.where(
                    valid_mask,
                    255,
                    0,
                ).astype(np.uint8)

            # Ensure pixels with invalid RGB values are transparent.
            finite_rgb = np.all(
                np.isfinite(rgb_data),
                axis=0,
            )

            valid_mask &= finite_rgb
            alpha_data[~valid_mask] = 0

            # Return a consistent four-channel array.
            return np.concatenate(
                [
                    rgb_data,
                    alpha_data[np.newaxis, :, :],
                ],
                axis=0,
            )

    @staticmethod
    def _convert_rgb_to_uint8(
        rgb_data: np.ndarray,
        valid_mask: np.ndarray | None = None,
    ) -> np.ndarray:
        """
        Convert RGB data to uint8 using a shared 2nd-98th percentile stretch.

        Transparent and invalid pixels are excluded from the stretch.
        The same stretch is applied to all three channels to help
        preserve the relative color balance.
        """

        rgb_data = rgb_data.astype(np.float32)

        # Only pixels with finite RGB values are valid.
        finite_pixels = np.all(
            np.isfinite(rgb_data),
            axis=2,
        )

        if valid_mask is not None:
            finite_pixels &= valid_mask

        if not np.any(finite_pixels):
            raise ValueError(
                "RGB raster contains no valid visible pixel values."
            )

        # Use only valid RGB pixels to calculate contrast.
        valid_values = rgb_data[finite_pixels].reshape(-1)

        lower = np.percentile(valid_values, 2)
        upper = np.percentile(valid_values, 98)

        print("\n--- RGB Contrast Stretch ---")
        print(f"Lower value (2nd percentile): {lower}")
        print(f"Upper value (98th percentile): {upper}")

        if upper <= lower:
            raise ValueError(
                "Unable to calculate RGB contrast stretch. "
                "The valid pixel values have no usable range."
            )

        normalized = (rgb_data - lower) / (upper - lower)
        normalized = np.clip(normalized, 0.0, 1.0)

        # Replace invalid pixels with black.
        normalized[~finite_pixels] = 0

        return (normalized * 255).astype(np.uint8)

    @staticmethod
    def _convert_alpha_to_uint8(
        alpha_data: np.ndarray,
    ) -> np.ndarray:
        """
        Convert alpha values to uint8 using the observed alpha maximum.

        This supports both 8-bit and 16-bit alpha values, including
        16-bit rasters whose alpha values are stored in a smaller range.
        """

        alpha_data = alpha_data.astype(np.float32)

        finite_pixels = np.isfinite(alpha_data)

        if not np.any(finite_pixels):
            raise ValueError("Alpha band contains no valid values.")

        maximum = float(np.max(alpha_data[finite_pixels]))

        if maximum <= 0:
            raise ValueError(
                "Alpha band contains only zero or negative values. "
                "Check the source raster's alpha band."
            )

        alpha = np.zeros(alpha_data.shape, dtype=np.float32)

        alpha[finite_pixels] = (
            alpha_data[finite_pixels] / maximum
        )

        alpha = np.clip(alpha, 0.0, 1.0)

        return (alpha * 255).astype(np.uint8)

    @staticmethod
    def create_preview(rgba: np.ndarray) -> Image.Image:
        """
        Convert a channel-first RGBA array into a Pillow image.
        """

        if rgba.ndim != 3:
            raise ValueError(
                f"Expected a 3-dimensional array. Got {rgba.ndim}."
            )

        if rgba.shape[0] != 4:
            raise ValueError(
                f"Expected 4 channels. Got {rgba.shape[0]}."
            )

        # Separate RGB and alpha.
        rgb_data = rgba[:3]
        alpha_data = rgba[3]

        # Convert alpha first so it can provide the RGB validity mask.
        alpha_uint8 = (
            OrthomosaicPreviewService._convert_alpha_to_uint8(
                alpha_data
            )
        )

        valid_mask = alpha_uint8 > 0

        # Convert RGB from channel-first to channel-last.
        rgb_data = np.moveaxis(rgb_data, 0, 2)

        # Convert RGB using only visible pixels.
        rgb_uint8 = (
            OrthomosaicPreviewService._convert_rgb_to_uint8(
                rgb_data,
                valid_mask,
            )
        )

        # Combine RGB and alpha.
        image_array = np.dstack(
            [
                rgb_uint8,
                alpha_uint8,
            ]
        )

        return Image.fromarray(image_array, mode="RGBA")

    @staticmethod
    def save_preview(
        preview: Image.Image,
        output_path: str | Path,
    ) -> Path:
        """Save the preview as a PNG."""

        output_path = Path(output_path).resolve()

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        preview.save(
            output_path,
            format="PNG",
        )

        print(f"\nPreview saved: {output_path}")
        print(f"Preview dimensions: {preview.size}")

        return output_path

    @staticmethod
    def generate_preview(
        raster_path: str | Path,
        output_path: str | Path,
        rgb_bands: tuple[int, int, int] = (1, 2, 3),
        max_dimension: int = DEFAULT_MAX_DIMENSION,
        resampling: Resampling = DEFAULT_RESAMPLING,
    ) -> Path:
        """Run the complete preview workflow."""

        raster_data = OrthomosaicPreviewService.read_rgb(
            raster_path=raster_path,
            rgb_bands=rgb_bands,
            max_dimension=max_dimension,
            resampling=resampling,
        )

        preview = OrthomosaicPreviewService.create_preview(
            raster_data
        )

        return OrthomosaicPreviewService.save_preview(
            preview,
            output_path,
        )