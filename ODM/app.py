"""
Main ODM application pipeline.

Responsibilities
----------------
1. Run ODM processing when requested.
2. Analyze an existing orthomosaic.
3. Process large orthomosaics tile-by-tile.
4. Generate SLIC superpixels for each tile.
5. Calculate vegetation indices from the real spectral bands.
6. Calculate HSV features from RGB.
7. Extract statistics for every superpixel region.

Expected 5-band multispectral order:

    Band 0 -> Blue
    Band 1 -> Green
    Band 2 -> Red
    Band 3 -> Red Edge
    Band 4 -> NIR

No Alpha band is assumed.
"""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

from ODM.ui import UserInterface
from ODM.docker_manager import DockerManager
from ODM.command_builder import ODMCommandBuilder
from ODM.runner import ODMRunner

from ODM.raster.raster_loader import RasterLoader
from ODM.raster.vegetation_indices import VegetationIndices
from ODM.hsv_features import HSVFeatures

from ODM.superpixel_segmenter import SuperpixelSegmenter
from ODM.region_feature_extractor import RegionFeatureExtractor

from ODM.superpixel_overlay_writer import SuperpixelOverlayWriter

class ODMApplication:

    def __init__(self):

        self.results = {}

    # =========================================================
    # MAIN ENTRY POINT
    # =========================================================

    def execute(self):

        while True:

            print(
                "\n=== DRONE PROCESSING ==="
            )

            print(
                "1. Run ODM Processing"
            )

            print(
                "2. Analyze Existing Ortho"
            )

            print(
                "3. Exit"
            )

            selection = input(
                "\nSelection --> "
            ).strip()

            if selection == "1":

                ortho_path = (
                    self.run_odm_pipeline()
                )

                self.run_feature_pipeline(
                    ortho_path
                )

            elif selection == "2":

                print(
                    "\n=== Feature Extraction ==="
                )

                ortho_path = Path(
                    input(
                        "Orthomosaic (.tif) --> "
                    ).strip()
                )

                if not ortho_path.exists():

                    print(
                        f"\nFile does not exist:\n"
                        f"{ortho_path}"
                    )

                    continue

                self.run_feature_pipeline(
                    ortho_path
                )

            elif selection == "3":

                print(
                    "\nExiting..."
                )

                break

            else:

                print(
                    "\nInvalid selection."
                )

    # =========================================================
    # ODM PIPELINE
    # =========================================================

    def run_odm_pipeline(self):

        print(
            "\n=== ODM Processing ==="
        )

        # -----------------------------------------------------
        # DOCKER
        # -----------------------------------------------------

        self.ensure_docker_running()

        # -----------------------------------------------------
        # USER CONFIGURATION
        # -----------------------------------------------------

        config = (
            UserInterface.get_odm_configuration()
        )

        # -----------------------------------------------------
        # BUILD ODM COMMAND
        # -----------------------------------------------------

        command_builder = ODMCommandBuilder(
            config
        )

        command = (
            command_builder.build()
        )

        print(
            "\nRunning ODM..."
        )

        runner = ODMRunner(
            command
        )

        runner.run()

        # -----------------------------------------------------
        # DETERMINE ORTHOMOSAIC
        # -----------------------------------------------------

        ortho_path = self._find_orthomosaic(
            config
        )

        print(
            "\nODM processing complete."
        )

        print(
            f"Orthomosaic:\n{ortho_path}"
        )

        return ortho_path

    # =========================================================
    # DOCKER
    # =========================================================

    def ensure_docker_running(self):

        if DockerManager.docker_running():

            return

        print(
            "Starting Docker Desktop..."
        )

        DockerManager.start_docker()

        DockerManager.wait_for_docker()

    # =========================================================
    # FIND ORTHOMOSAIC
    # =========================================================

    @staticmethod
    def _find_orthomosaic(config):

        project_path = Path(
            config.project_path
        )

        candidates = [

            project_path /
            "odm_orthophoto" /
            "odm_orthophoto.tif",

            project_path /
            "odm_orthophoto" /
            "odm_orthophoto.original.tif"
        ]

        for path in candidates:

            if path.exists():

                return path

        raise FileNotFoundError(
            "Could not locate the ODM "
            "orthomosaic."
        )

    # =========================================================
    # FEATURE PIPELINE
    # =========================================================

    def run_feature_pipeline(
        self,
        ortho_path
    ):

        ortho_path = Path(
            ortho_path
        )

        if not ortho_path.exists():

            raise FileNotFoundError(
                f"Orthomosaic does not exist:\n"
                f"{ortho_path}"
            )

        print(
            "\n=== Feature Pipeline ==="
        )

        # -----------------------------------------------------
        # READ ORTHOMOSAIC INFORMATION
        # -----------------------------------------------------

        print(
            "\nReading orthomosaic information..."
        )

        metadata = self._read_raster_metadata(
            ortho_path
        )

        pixel_width = metadata[
            "pixel_width"
        ]

        pixel_height = metadata[
            "pixel_height"
        ]

        width = metadata[
            "width"
        ]

        height = metadata[
            "height"
        ]

        band_count = metadata[
            "count"
        ]

        total_area_m2 = (
            width *
            height *
            pixel_width *
            pixel_height
        )

        print(
            "\nOrthomosaic Information"
        )

        print(
            "-------------------------"
        )

        print(
            f"Resolution          : "
            f"{pixel_width:.3f} m/pixel"
        )

        print(
            f"Total Area          : "
            f"{total_area_m2:,.2f} m²"
        )

        print(
            f"Bands               : "
            f"{band_count}"
        )

        # -----------------------------------------------------
        # VERIFY SPECTRAL BANDS
        # -----------------------------------------------------

        if band_count < 5:

            raise ValueError(
                "\nThis feature pipeline requires "
                "at least 5 spectral bands:\n\n"
                "Band 0 -> Blue\n"
                "Band 1 -> Green\n"
                "Band 2 -> Red\n"
                "Band 3 -> Red Edge\n"
                "Band 4 -> NIR\n\n"
                f"The TIFF only contains "
                f"{band_count} bands."
            )

        print(
            "\nSpectral band configuration:"
        )

        print(
            "  Band 1 -> Blue"
        )

        print(
            "  Band 2 -> Green"
        )

        print(
            "  Band 3 -> Red"
        )

        print(
            "  Band 4 -> Red Edge"
        )

        print(
            "  Band 5 -> NIR"
        )

        # -----------------------------------------------------
        # SUPERPIXEL OPTIONS
        # -----------------------------------------------------

        superpixel_options = (
            UserInterface.get_superpixel_options()
        )

        region_area = float(
            superpixel_options[
                "region_area"
            ]
        )

        compactness = float(
            superpixel_options[
                "compactness"
            ]
        )

        sigma = float(
            superpixel_options[
                "sigma"
            ]
        )

        tile_size = int(
            superpixel_options[
                "tile_size"
            ]
        )

        print(
            f"\nDesired Region Size : "
            f"{region_area:.2f} m²"
        )

        print(
            f"Tile Size           : "
            f"{tile_size} × {tile_size} pixels"
        )

        # -----------------------------------------------------
        # APPROXIMATE TOTAL REGIONS
        # -----------------------------------------------------

        estimated_regions = max(
            1,
            int(
                round(
                    total_area_m2 /
                    region_area
                )
            )
        )

        print(
            f"Estimated Regions   : "
            f"{estimated_regions:,}"
        )

        # -----------------------------------------------------
        # PIXEL AREA
        # -----------------------------------------------------

        pixel_area_m2 = (
            pixel_width *
            pixel_height
        )

        # -----------------------------------------------------
        # RASTER LOADER
        # -----------------------------------------------------

        loader = RasterLoader(
            ortho_path
        )

        # -----------------------------------------------------
        # RESULTS
        # -----------------------------------------------------

        all_regions = {}

        tile_number = 0

        # -----------------------------------------------------
        # PROCESS TILES
        # -----------------------------------------------------

        with rasterio.open(
            ortho_path
        ) as src:

            total_tiles_x = (
                int(
                    np.ceil(
                        width /
                        tile_size
                    )
                )
            )

            total_tiles_y = (
                int(
                    np.ceil(
                        height /
                        tile_size
                    )
                )
            )

            total_tiles = (
                total_tiles_x *
                total_tiles_y
            )

            print(
                f"\nTotal tiles to process: "
                f"{total_tiles}"
            )

            for row in range(
                0,
                height,
                tile_size
            ):

                for col in range(
                    0,
                    width,
                    tile_size
                ):

                    tile_number += 1

                    tile_width = min(
                        tile_size,
                        width - col
                    )

                    tile_height = min(
                        tile_size,
                        height - row
                    )

                    print(
                        "\n========================================"
                    )

                    print(
                        f"Processing tile "
                        f"{tile_number}/{total_tiles}..."
                    )

                    print(
                        f"Position: "
                        f"({col}, {row})"
                    )

                    print(
                        f"Size: "
                        f"{tile_width} × "
                        f"{tile_height} pixels"
                    )

                    # -------------------------------------------------
                    # TILE WINDOW
                    # -------------------------------------------------

                    window = Window(
                        col,
                        row,
                        tile_width,
                        tile_height
                    )

                    # -------------------------------------------------
                    # TILE AREA
                    # -------------------------------------------------

                    tile_area_m2 = (
                        tile_width *
                        tile_height *
                        pixel_area_m2
                    )

                    target_segments = max(
                        1,
                        int(
                            round(
                                tile_area_m2 /
                                region_area
                            )
                        )
                    )

                    print(
                        f"Tile Area          : "
                        f"{tile_area_m2:,.2f} m²"
                    )

                    print(
                        f"Target Region Area : "
                        f"{region_area:.2f} m²"
                    )

                    print(
                        f"Target Superpixels : "
                        f"{target_segments:,}"
                    )

                    # -------------------------------------------------
                    # LOAD TILE
                    # -------------------------------------------------

                    tile = loader.load_window(
                        window
                    )

                    # -------------------------------------------------
                    # BAND DIAGNOSTICS
                    # -------------------------------------------------

                    self._print_band_diagnostics(
                        tile
                    )



                    # -------------------------------------------------
                    # SLIC
                    # -------------------------------------------------

                    print(
                        "\nGenerating superpixels..."
                    )

                    segmenter = (
                        SuperpixelSegmenter(
                            num_segments=
                            target_segments,
                            compactness=
                            compactness,
                            sigma=sigma
                        )
                    )

                    labels = segmenter.run(
                        tile
                    )

                    if labels is None:

                        print(
                            "Superpixel segmentation "
                            "returned no labels. "
                            "Skipping tile."
                        )

                        continue

                    # -------------------------------------------------
                    # VEGETATION INDICES
                    # -------------------------------------------------

                    print(
                        "Calculating vegetation indices..."
                    )

                    vegetation = (
                        VegetationIndices(
                            tile
                        )
                    )

                    ndvi = (
                        vegetation.ndvi()
                    )

                    gndvi = (
                        vegetation.gndvi()
                    )

                    ndre = (
                        vegetation.ndre()
                    )

                    ci_red_edge = (
                        vegetation.ci_red_edge()
                    )

                    # -------------------------------------------------
                    # DIAGNOSTICS
                    # -------------------------------------------------

                    self._print_feature_diagnostic(
                        "NDVI",
                        ndvi
                    )

                    self._print_feature_diagnostic(
                        "GNDVI",
                        gndvi
                    )

                    self._print_feature_diagnostic(
                        "NDRE",
                        ndre
                    )

                    self._print_feature_diagnostic(
                        "CI_RedEdge",
                        ci_red_edge
                    )

                    # -------------------------------------------------
                    # HSV
                    # -------------------------------------------------

                    print(
                        "Calculating HSV features..."
                    )

                    hsv = HSVFeatures(
                        tile
                    )

                    hsv_features = (
                        hsv.calculate()
                    )

                    # -------------------------------------------------
                    # REGION FEATURE EXTRACTOR
                    # -------------------------------------------------

                    extractor = (
                        RegionFeatureExtractor(
                            labels=labels,
                            pixel_area_m2=
                            pixel_area_m2,
                            tile_number=
                            tile_number
                        )
                    )

                    # -------------------------------------------------
                    # ADD VEGETATION FEATURES
                    # -------------------------------------------------

                    extractor.add_feature(
                        "NDVI",
                        ndvi
                    )

                    extractor.add_feature(
                        "GNDVI",
                        gndvi
                    )

                    extractor.add_feature(
                        "NDRE",
                        ndre
                    )

                    extractor.add_feature(
                        "CI_RedEdge",
                        ci_red_edge
                    )

                    # -------------------------------------------------
                    # ADD HSV FEATURES
                    # -------------------------------------------------

                    extractor.add_feature(
                        "Hue",
                        hsv_features[
                            "Hue"
                        ]
                    )

                    extractor.add_feature(
                        "Saturation",
                        hsv_features[
                            "Saturation"
                        ]
                    )

                    extractor.add_feature(
                        "Value",
                        hsv_features[
                            "Value"
                        ]
                    )

                    # -------------------------------------------------
                    # EXTRACT REGION STATISTICS
                    # -------------------------------------------------

                    regions = (
                        extractor.get_features()
                    )

                    print(
                        f"Extracted features for "
                        f"{len(regions):,} regions."
                    )

                    # -------------------------------------------------
                    # STORE
                    # -------------------------------------------------

                    all_regions.update(
                        regions
                    )

                    # -------------------------------------------------
                    # RELEASE TILE MEMORY
                    # -------------------------------------------------

                    del tile
                    del labels
                    del ndvi
                    del gndvi
                    del ndre
                    del ci_red_edge
                    del hsv_features

        # =====================================================
        # COMPLETE
        # =====================================================

        print(
            "\n=== Feature Pipeline Complete ==="
        )

        print(
            f"Total regions extracted: "
            f"{len(all_regions):,}"
        )

        self.results = all_regions

        # -----------------------------------------------------
        # SAMPLE RESULTS
        # -----------------------------------------------------

        self._print_sample_regions(
            all_regions
        )

        return all_regions

    # =========================================================
    # RASTER METADATA
    # =========================================================

    @staticmethod
    def _read_raster_metadata(
        ortho_path
    ):

        with rasterio.open(
            ortho_path
        ) as src:

            return {
                "width": src.width,
                "height": src.height,
                "count": src.count,

                "pixel_width": abs(
                    src.transform.a
                ),

                "pixel_height": abs(
                    src.transform.e
                ),

                "dtype": src.dtypes,

                "nodata": src.nodata,

                "crs": src.crs,

                "transform": src.transform
            }

    # =========================================================
    # BAND DIAGNOSTICS
    # =========================================================

    @staticmethod
    def _print_band_diagnostics(
        bands
    ):

        print(
            "\n RAW BAND CHECK"
        )

        print(
            f"Shape: {bands.shape}"
        )

        names = [
            "Blue",
            "Green",
            "Red",
            "Red Edge",
            "NIR"
        ]

        for i in range(
            bands.shape[0]
        ):

            band = bands[i]

            finite = np.isfinite(
                band
            )

            if not np.any(
                finite
            ):

                print(
                    f"Band {i} "
                    f"({names[i] if i < len(names) else 'Unknown'}): "
                    f"NO FINITE VALUES"
                )

                continue

            values = band[
                finite
            ]

            print(
                f"Band {i} "
                f"({names[i] if i < len(names) else 'Unknown'}): "
                f"min={np.min(values):.4f}, "
                f"max={np.max(values):.4f}, "
                f"mean={np.mean(values):.4f}, "
                f"nonzero="
                f"{np.count_nonzero(values):,}"
            )

    # =========================================================
    # FEATURE DIAGNOSTICS
    # =========================================================

    @staticmethod
    def _print_feature_diagnostic(
        name,
        feature
    ):

        finite = np.isfinite(
            feature
        )

        finite_count = int(
            np.count_nonzero(
                finite
            )
        )

        nan_count = int(
            np.count_nonzero(
                ~finite
            )
        )

        print(
            f"{name} CHECK"
        )

        if finite_count == 0:

            print(
                f"{name} contains "
                f"NO finite values."
            )

            return

        values = feature[
            finite
        ]

        print(
            f"{name} min:  "
            f"{np.min(values)}"
        )

        print(
            f"{name} max:  "
            f"{np.max(values)}"
        )

        print(
            f"{name} mean: "
            f"{np.mean(values)}"
        )

        print(
            f"{name} finite: "
            f"{finite_count:,}"
        )

        print(
            f"{name} NaN: "
            f"{nan_count:,}"
        )

    # =========================================================
    # SAMPLE RESULTS
    # =========================================================

    @staticmethod
    def _print_sample_regions(
        regions,
        count=5
    ):

        if not regions:

            print(
                "\nNo regions were extracted."
            )

            return

        print(
            "\n=== Sample Region Features ==="
        )

        sample_items = list(
            regions.items()
        )[:count]

        for region_id, features in (
            sample_items
        ):

            print(
                f"\nRegion {region_id}"
            )

            for name, value in (
                features.items()
            ):

                if isinstance(
                    value,
                    float
                ):

                    if np.isnan(
                        value
                    ):

                        print(
                            f"  {name}: NaN"
                        )

                    else:

                        print(
                            f"  {name}: "
                            f"{value:.6f}"
                        )

                else:

                    print(
                        f"  {name}: "
                        f"{value}"
                    )