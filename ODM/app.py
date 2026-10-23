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

import time
import traceback
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

from ODM.feature_inspector import FeatureInspector
from ODM.raster.raster_loader import RasterLoader
from ODM.region_feature_extractor import RegionFeatureExtractor
from ODM.superpixel_overlay_writer import SuperpixelOverlayWriter
from ODM.tile_processor import TileProcessor
from ODM.ui import UserInterface
from services.odm_processing_service import ODMProcessingService
from services.region_csv_exporter import RegionCSVExporter


class ODMApplication:
    def __init__(self):
        self.results = {}

        self.odm_service = ODMProcessingService()
        self.csv_exporter = RegionCSVExporter()

    def execute(self):
        while True:
            selection = UserInterface.get_start_option()
            if selection == "1":
                try:
                    ortho_path, rgb_ortho_path = self.odm_service.process_images()
                    #line 47 commented out so that it does not kick you into superpixel generation automatically 
                    #self.run_feature_pipeline(ortho_path, rgb_ortho_path)
                except Exception as error:
                    print("\n========================================")
                    print("[ERROR]")
                    print(error)
                    traceback.print_exc()
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
                    traceback.print_exc()
                    print("========================================")
            elif selection == "3":
                print("\nExiting...")
                break

    # * =========================================================*
    # * FEATURE PIPELINE*
    # * =========================================================*
    def run_feature_pipeline(self, ortho_path, rgb_ortho_path):
        ortho_path = Path(ortho_path)
        if not ortho_path.exists():
            raise FileNotFoundError(f"\nOrthomosaic does not exist:\n{ortho_path}")
        # * Set up output folder for superpixel files.*
        output_directory = ortho_path.parent / "superpixel_outputs"
        print("\n=== Feature Extraction ===")
        print(f"Orthomosaic (.tif) --> {ortho_path}")
        # * Read orthomosaic metadata.*
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
        # * Existing band validation retained for now.*
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
        overlay_writer = None
        try:
            overlay_writer = SuperpixelOverlayWriter(
                ortho_path, output_directory, rgb_ortho_path
            )
            with rasterio.open(ortho_path) as src:
                total_tiles_x = int(np.ceil(width / tile_size))
                total_tiles_y = int(np.ceil(height / tile_size))
                total_tiles = total_tiles_x * total_tiles_y
                print(f"\nTotal tiles --> {total_tiles:,}")
                processor = TileProcessor(
                    compactness=compactness,
                    sigma=sigma,
                )
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
                            del tile  # * skips only when all values are invalid**
                            continue
                        labels, index_rasters = processor.process(
                            tile,
                            target_segments,
                        )
                        if labels is None:
                            tile_elapsed = time.time() - tile_start
                            print(f"\nTile {tile_number} skipped.")
                            print(f"Tile time: {tile_elapsed:.1f} seconds")
                            print(
                                f"\nTile {tile_number} skipped: "
                                "superpixel segmentation returned no labels :("
                            )
                            del tile
                            continue
                        valid_labels = labels[labels >= 0]
                        valid_superpixels = np.unique(valid_labels).size
                        print(f"      Completed: {valid_superpixels:,} superpixels")
                        # * Write this tile's labels to the georeferenced raster.*
                        overlay_writer.write_labels(
                            labels,
                            window,
                            id_offset,
                        )
                        overlay_writer.write_overlay(labels, window)
                        overlay_writer.write_multispectral_overlay(labels, window)
                        # * Make the next tile's IDs unique.*
                        if valid_labels.size:
                            id_offset += int(valid_labels.max()) + 1
                        for name, raster in index_rasters.items():
                            FeatureInspector.print_feature_diagnostic(name, raster)
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
                        del extractor
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
            if overlay_writer is not None:
                overlay_writer.close()
        # * Export a JPEG preview after closing the overlay GeoTIFF.*
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
        multispectral_jpg_path = output_directory / "multispectral_overlay.jpg"
        SuperpixelOverlayWriter.save_overlay_jpg(
            output_directory / "multispectral_overlay.tif",
            multispectral_jpg_path,
        )
        print(
            "Multispectral overlay GeoTIFF --> "
            f"{output_directory / 'multispectral_overlay.tif'}"
        )
        print(f"Multispectral overlay JPEG --> {multispectral_jpg_path}")
        print("\n=== Feature Pipeline Complete ===")
        print(f"Total regions extracted --> {len(all_regions):,}")

        csv_path = ortho_path.parent.parent / "region_features.csv"

        self.csv_exporter.export(
            all_regions,
            csv_path,
        )

        #self.results = all_regions

        #FeatureInspector.print_sample_regions(all_regions)

        print(
            "\nSuperpixel label raster --> "
            f"{output_directory / 'superpixel_labels.tif'}"
        )
        return all_regions
