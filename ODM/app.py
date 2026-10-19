"""
Main ODM application.

Coordinates the complete drone-processing workflow:

1. Check Docker Desktop.
2. Start Docker Desktop if necessary.
3. Wait for the Docker daemon to become ready.
4. Collect ODM configuration.
5. Validate source images.
6. Build the ODM Docker command.
7. Run ODM.
8. Locate the resulting orthomosaic.
9. Run the feature extraction / superpixel pipeline.
"""

import csv
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

from ODM.raster.raster_loader import RasterLoader
from ODM.vegetation_indices import VegetationIndices
from ODM.region_feature_extractor import RegionFeatureExtractor
from ODM.superpixel_overlay_writer import SuperpixelOverlayWriter
from ODM.superpixel_segmenter import SuperpixelSegmenter
from ODM.ui import UserInterface
from services.odm_processing_service import ODMProcessingService


class ODMApplication:
    def __init__(self):
        self.results = {}
        self.odm_service = ODMProcessingService()

    def execute(self):
        while True:
            selection = UserInterface.get_start_option()
            if selection == "1":
                try:
                    ortho_path, rgb_ortho_path = self.odm_service.process_images()
                    self.run_feature_pipeline(ortho_path, rgb_ortho_path)
                except Exception as error:
                    print("\n========================================")
                    print("[ERROR]")
                    print(error)
                    print("========================================")
            elif selection == "2":
                try:
                    ortho_path = UserInterface.get_orthomosaic_path()
                    rgb_ortho_path = UserInterface.get_rgb_orthomosaic_path()
                    self.run_feature_pipeline(ortho_path, rgb_ortho_path)
                except Exception as error:
                    print("\n========================================")
                    print("[ERROR]")
                    print(error)
                    print("========================================")
            elif selection == "3":
                print("\nExiting...")
                break

    # =========================================================
    # FEATURE PIPELINE
    # =========================================================
    def run_feature_pipeline(self, ortho_path, rgb_ortho_path):
        ortho_path = Path(ortho_path)
        if not ortho_path.exists():
            raise FileNotFoundError(f"\nOrthomosaic does not exist:\n{ortho_path}")

        # Set up output folder for superpixel files.
        output_directory = ortho_path.parent / "superpixel_outputs"

        print("\n=== Feature Extraction ===")
        print(f"Orthomosaic (.tif) --> {ortho_path}")

        # Read orthomosaic metadata.
        print("\nReading orthomosaic information...")
        loader = RasterLoader(ortho_path)
        metadata = loader.get_metadata()
        width = metadata["width"]
        height = metadata["height"]
        band_count = metadata["count"]
        pixel_width = metadata["pixel_width"]
        pixel_height = metadata["pixel_height"]

        total_area_m2 = width * height * pixel_width * pixel_height
        print("\n=== Orthomosaic Information ===")
        print(f"Width       : {width:,} pixels")
        print(f"Height      : {height:,} pixels")
        print(f"Bands       : {band_count}")
        print(f"Resolution  : {pixel_width:.4f} × {pixel_height:.4f} m")
        print(f"Total Area  : {total_area_m2:,.2f} m²")

        # Existing band validation retained for now.
        if band_count < 5:
            raise ValueError(
                "\nThe feature pipeline requires at least 5 bands.\n\n"
                "Expected:\n"
                "Band 1 -> Red\n"
                "Band 2 -> Green\n"
                "Band 3 -> NIR\n"
                "Band 4 -> Red Edge\n"
                "Band 5 -> Alpha\n\n"
                f"Found {band_count} bands."
            )

        print("\nSpectral band configuration:")
        print("  Band 1 -> Red")
        print("  Band 2 -> Green")
        print("  Band 3 -> NIR")
        print("  Band 4 -> Red Edge")
        print("  Band 5 -> Alpha")

        superpixel_options = UserInterface.get_superpixel_options()
        region_area = float(superpixel_options["region_area"])
        compactness = float(superpixel_options["compactness"])
        sigma = float(superpixel_options["sigma"])
        tile_size = int(superpixel_options["tile_size"])

        if region_area <= 0:
            raise ValueError("Region area must be greater than zero.")
        if tile_size <= 0:
            raise ValueError("Tile size must be greater than zero.")

        print("\n=== Superpixel Configuration ===")
        print(f"Region Area --> {region_area} m²")
        print(f"Compactness --> {compactness}")
        print(f"Sigma --> {sigma}")
        print(f"Tile Size --> {tile_size} pixels")

        estimated_regions = max(1, round(total_area_m2 / region_area))
        print(f"\nEstimated total regions --> {estimated_regions:,}")

        pixel_area_m2 = pixel_width * pixel_height
        all_regions = {}
        tile_number = 0
        id_offset = 0

        overlay_writer = SuperpixelOverlayWriter(
            ortho_path, output_directory, rgb_ortho_path
        )

        try:
            with rasterio.open(ortho_path) as src:
                total_tiles_x = int(np.ceil(width / tile_size))
                total_tiles_y = int(np.ceil(height / tile_size))
                total_tiles = total_tiles_x * total_tiles_y
                print(f"\nTotal tiles --> {total_tiles:,}")

                for row in range(0, src.height, tile_size):
                    for col in range(0, src.width, tile_size):
                        tile_start = time.time()
                        tile_number += 1
                        window_width = min(tile_size, src.width - col)
                        window_height = min(tile_size, src.height - row)
                        window = Window(
                            col_off=col,
                            row_off=row,
                            width=window_width,
                            height=window_height,
                        )

                        tile_area_m2 = window_width * window_height * pixel_area_m2
                        target_segments = max(1, round(tile_area_m2 / region_area))

                        print("\n" + "=" * 60)
                        print(f"TILE {tile_number} / {total_tiles}")
                        print(f"Position: x={col}, y={row}")
                        print(f"Dimensions: {window_width} × {window_height} pixels")
                        print(f"Tile area: {tile_area_m2:,.2f} m²")
                        print(f"Target region area: {region_area:.2f} m²")
                        print(f"Target superpixels: {target_segments:,}")
                        print("=" * 60)

                        tile = loader.load_window(window)

                        if not loader.tile_has_data(tile):
                            print(
                                f"\nTile {tile_number} contains no valid data. Skipping."
                            )
                            del tile  # skips only when all values are invalid
                            continue

                        print("\n[1/3] Calculating vegetation indices...")
                        vegetation = VegetationIndices(tile)
                        index_rasters = vegetation.calculate_all()
                        for name in index_rasters:
                            print(f"      {name:<12} ✓")

                        print(
                            "\n[2/3] Generating superpixels from vegetation indices..."
                        )
                        segmenter = SuperpixelSegmenter(
                            num_segments=target_segments,
                            compactness=compactness,
                            sigma=sigma,
                        )
                        labels = segmenter.run(tile, index_rasters=index_rasters)

                        if labels is None:
                            tile_elapsed = time.time() - tile_start
                            print(f"\nTile {tile_number} skipped.")
                            print(f"Tile time: {tile_elapsed:.1f} seconds")
                            print(
                                f"\nTile {tile_number} skipped: "
                                "superpixel segmentation returned no labels :("
                            )
                            del tile
                            del segmenter
                            continue

                        valid_labels = labels[labels >= 0]
                        valid_superpixels = np.unique(valid_labels).size
                        print(f"      Completed: {valid_superpixels:,} superpixels")

                        # Write this tile's labels to the georeferenced raster.
                        overlay_writer.write_labels(
                            labels,
                            window,
                            id_offset,
                        )

                        overlay_writer.write_overlay(labels, window)

                        # Make the next tile's IDs unique.
                        if valid_labels.size:
                            id_offset += int(valid_labels.max()) + 1

                        for name, raster in index_rasters.items():
                            self._print_feature_diagnostic(name, raster)

                        print("\n[3/3] Extracting region statistics...")
                        extractor = RegionFeatureExtractor(
                            labels=labels,
                            pixel_area_m2=pixel_area_m2,
                            tile_number=tile_number,
                        )
                        extractor.add_feature("Red", tile[0])
                        extractor.add_feature("Green", tile[1])
                        extractor.add_feature("NIR", tile[2])
                        extractor.add_feature("Red Edge", tile[3])
                        extractor.add_features(index_rasters)
                        regions = extractor.get_features()
                        print(f"      Regions extracted: {len(regions):,}")
                        all_regions.update(regions)

                        del tile
                        del labels
                        del valid_labels
                        del index_rasters
                        del vegetation
                        del extractor
                        del segmenter

                        tile_elapsed = time.time() - tile_start
                        completed_percent = (tile_number / total_tiles) * 100
                        print(f"\nTile {tile_number} complete ✓")
                        print(f"Tile time: {tile_elapsed:.1f} seconds")
                        print(
                            "Overall progress: "
                            f"{tile_number} / {total_tiles} "
                            f"({completed_percent:.1f}%)"
                        )

        finally:
            overlay_writer.close()

        # Export a JPEG preview after closing the overlay GeoTIFF.
        jpg_path = output_directory / "superpixel_overlay.jpg"

        SuperpixelOverlayWriter.save_overlay_jpg(
            output_directory / "superpixel_overlay.tif",
            jpg_path,
        )

        print(
            "Superpixel overlay GeoTIFF --> "
            f"{output_directory / 'superpixel_overlay.tif'}"
        )
        print(f"Superpixel overlay JPEG --> {jpg_path}")

        print("\n=== Feature Pipeline Complete ===")
        print(f"Total regions extracted --> {len(all_regions):,}")

        csv_path = ortho_path.parent.parent / "region_features.csv"
        self._save_regions_to_csv(all_regions, csv_path)
        self.results = all_regions
        self._print_sample_regions(all_regions)
        print(
            "\nSuperpixel label raster --> "
            f"{output_directory / 'superpixel_labels.tif'}"
        )
        return all_regions

    # =========================================================
    # SAVE REGION FEATURES
    # =========================================================
    @staticmethod
    def _save_regions_to_csv(regions, output_path):
        if not regions:
            print("\nNo region data to save.")
            return

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = {"region_id"}
        for features in regions.values():
            fieldnames.update(features.keys())

        fieldnames = sorted(fieldnames)
        if "region_id" in fieldnames:
            fieldnames.remove("region_id")
            fieldnames.insert(0, "region_id")

        with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for region_id, features in regions.items():
                row = {"region_id": region_id}
                for name, value in features.items():
                    if isinstance(value, np.generic):
                        value = value.item()
                    row[name] = value
                writer.writerow(row)

        print("\n=== CSV Output ===")
        print(f"Region feature CSV --> {output_path}")
        print(f"Rows written --> {len(regions):,}")

    # =========================================================
    # BAND DIAGNOSTICS
    # =========================================================
    @staticmethod
    def _print_band_diagnostics(bands):
        print("\nRAW BAND CHECK")
        print(f"Shape: {bands.shape}")
        names = ["Red", "Green", "NIR", "Red Edge", "Alpha"]
        for index in range(bands.shape[0]):
            band = bands[index]
            finite = np.isfinite(band)
            name = names[index] if index < len(names) else "Unknown"
            if not np.any(finite):
                print(f"Band {index + 1} ({name}): NO FINITE VALUES")
                continue
            values = band[finite]
            print(
                f"Band {index + 1} ({name}): "
                f"min={np.min(values):.4f}, "
                f"max={np.max(values):.4f}, "
                f"mean={np.mean(values):.4f}, "
                f"nonzero={np.count_nonzero(values):,}"
            )

    # =========================================================
    # FEATURE DIAGNOSTICS
    # =========================================================
    @staticmethod
    def _print_feature_diagnostic(name, feature):
        finite = np.isfinite(feature)
        finite_count = int(np.count_nonzero(finite))
        nan_count = int(np.count_nonzero(~finite))
        print(f"{name} CHECK")
        if finite_count == 0:
            print(f"{name} contains NO finite values.")
            return
        values = feature[finite]
        print(f"{name} min: {np.min(values)}")
        print(f"{name} max: {np.max(values)}")
        print(f"{name} mean: {np.mean(values)}")
        print(f"{name} finite: {finite_count:,}")
        print(f"{name} NaN: {nan_count:,}")

    # =========================================================
    # SAMPLE REGION OUTPUT
    # =========================================================
    @staticmethod
    def _print_sample_regions(regions, count=5):
        if not regions:
            print("\nNo regions were extracted.")
            return
        print("\n=== Sample Region Features ===")
        for region_id, features in list(regions.items())[:count]:
            print(f"\nRegion {region_id}")
            for name, value in features.items():
                if isinstance(value, (float, np.floating)):
                    if np.isnan(value):
                        print(f"  {name}: NaN")
                    else:
                        print(f"  {name}: {value:.6f}")
                else:
                    print(f"  {name}: {value}")
