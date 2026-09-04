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

from pathlib import Path
import csv
import time

import numpy as np
import rasterio
from rasterio.windows import Window

from ODM.ui import UserInterface
from ODM.docker_manager import DockerManager
from ODM.command_builder import ODMCommandBuilder
from ODM.runner import ODMRunner
from ODM.validate_images import validate_images

from ODM.raster.raster_loader import RasterLoader
from ODM.raster.vegetation_indices import VegetationIndices

from ODM.superpixel_segmenter import SuperpixelSegmenter
from ODM.region_feature_extractor import RegionFeatureExtractor


class ODMApplication:

    def __init__(self):
        self.results = {}

    # =========================================================
    # MAIN APPLICATION
    # =========================================================

    def execute(self):

        while True:

            selection = UserInterface.get_start_option()

            # -------------------------------------------------
            # RUN ODM
            # -------------------------------------------------

            if selection == "1":

                try:

                    ortho_path = self.run_odm_pipeline()

                    self.run_feature_pipeline(
                        ortho_path
                    )

                except Exception as error:

                    print(
                        "\n========================================"
                    )

                    print(
                        "[ERROR]"
                    )

                    print(error)

                    print(
                        "========================================"
                    )

            # -------------------------------------------------
            # ANALYZE EXISTING ORTHO
            # -------------------------------------------------

            elif selection == "2":

                try:

                    ortho_path = (
                        UserInterface
                        .get_orthomosaic_path()
                    )

                    self.run_feature_pipeline(
                        ortho_path
                    )

                except Exception as error:

                    print(
                        "\n========================================"
                    )

                    print(
                        "[ERROR]"
                    )

                    print(error)

                    print(
                        "========================================"
                    )

            # -------------------------------------------------
            # EXIT
            # -------------------------------------------------

            elif selection == "3":

                print(
                    "\nExiting..."
                )

                break

    # =========================================================
    # ODM PIPELINE
    # =========================================================

    def run_odm_pipeline(self):

        print(
            "\n=== ODM Processing ==="
        )

        # =====================================================
        # DOCKER
        # =====================================================

        self.ensure_docker_running()

        # =====================================================
        # ODM CONFIGURATION
        # =====================================================

        config = (
            UserInterface
            .get_odm_configuration()
        )

        image_path = Path(
            config["image_path"]
        )

        output_path = Path(
            config["output_path"]
        )

        project_name = config[
            "project_name"
        ]

        options = config[
            "pipeline_options"
        ]

        # =====================================================
        # IMAGE VALIDATION
        # =====================================================

        print(
            "\n=== Image Validation ==="
        )

        print(
            f"Validating images in:\n"
            f"{image_path}"
        )

        validate_images(
            image_path
        )

        print(
            "Metadata validation passed."
        )

        # =====================================================
        # BUILD ODM COMMAND
        # =====================================================

        print(
            "\nBuilding ODM command..."
        )

        command_builder = ODMCommandBuilder(
            image_path,
            output_path,
            project_name,
            options
        )

        command = (
            command_builder.build_command()
        )

        # =====================================================
        # DISPLAY COMMAND
        # =====================================================

        print(
            "\n=== ODM Command ==="
        )

        print(
            " ".join(
                f'"{argument}"'
                if " " in str(argument)
                else str(argument)
                for argument in command
            )
        )

        # =====================================================
        # RUN ODM
        # =====================================================

        print(
            "\n=== Running ODM ==="
        )

        runner = ODMRunner(
            command
        )

        runner.run()

        # =====================================================
        # LOCATE PROJECT
        # =====================================================

        project_path = (
            output_path /
            project_name
        )

        # =====================================================
        # LOCATE ORTHOMOSAIC
        # =====================================================

        ortho_path = (
            self._find_orthomosaic(
                project_path
            )
        )

        print(
            "\n=== ODM Complete ==="
        )

        print(
            f"Orthomosaic --> "
            f"{ortho_path}"
        )

        return ortho_path

    # =========================================================
    # DOCKER MANAGEMENT
    # =========================================================

    def ensure_docker_running(self):

        print(
            "\n=== Docker Check ==="
        )

        docker_manager = DockerManager()

        if docker_manager.docker_running():

            print(
                "Docker is already running."
            )

            return

        print(
            "Docker Desktop is not running."
        )

        docker_manager.start_docker()

        docker_ready = (
            docker_manager.wait_for_docker(
                timeout=120
            )
        )

        if not docker_ready:

            raise RuntimeError(
                "\nDocker Desktop was started, "
                "but the Docker daemon did not "
                "become ready within 120 seconds."
            )

        print(
            "Docker Desktop is ready."
        )

    # =========================================================
    # FIND ORTHOMOSAIC
    # =========================================================

    @staticmethod
    def _find_orthomosaic(project_path):

        project_path = Path(
            project_path
        )

        candidates = [

            (
                project_path /
                "odm_orthophoto" /
                "odm_orthophoto.tif"
            ),

            (
                project_path /
                "odm_orthophoto" /
                "odm_orthophoto.original.tif"
            )
        ]

        for candidate in candidates:

            if candidate.exists():

                return candidate

        tif_files = list(
            project_path.rglob(
                "*.tif"
            )
        )

        if tif_files:

            for tif in tif_files:

                if (
                    "orthophoto"
                    in tif.name.lower()
                ):

                    return tif

            return tif_files[0]

        raise FileNotFoundError(
            "\nODM completed, but an "
            "orthomosaic could not be found.\n\n"
            f"Project path:\n"
            f"{project_path}"
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
                f"\nOrthomosaic does not exist:\n"
                f"{ortho_path}"
            )

        print(
            "\n=== Feature Extraction ==="
        )

        print(
            f"Orthomosaic (.tif) --> "
            f"{ortho_path}"
        )

        # =====================================================
        # READ ORTHOMOSAIC METADATA
        # =====================================================

        print(
            "\nReading orthomosaic information..."
        )

        metadata = (
            self._read_raster_metadata(
                ortho_path
            )
        )

        width = metadata["width"]
        height = metadata["height"]
        band_count = metadata["count"]

        pixel_width = metadata[
            "pixel_width"
        ]

        pixel_height = metadata[
            "pixel_height"
        ]

        # =====================================================
        # TOTAL AREA
        # =====================================================

        total_area_m2 = (
            width *
            height *
            pixel_width *
            pixel_height
        )

        print(
            "\n=== Orthomosaic Information ==="
        )

        print(
            f"Width       : "
            f"{width:,} pixels"
        )

        print(
            f"Height      : "
            f"{height:,} pixels"
        )

        print(
            f"Bands       : "
            f"{band_count}"
        )

        print(
            f"Resolution  : "
            f"{pixel_width:.4f} × "
            f"{pixel_height:.4f} m"
        )

        print(
            f"Total Area  : "
            f"{total_area_m2:,.2f} m²"
        )

        # =====================================================
        # BAND VALIDATION
        # =====================================================

        if band_count < 5:

            raise ValueError(
                "\nThe feature pipeline requires "
                "at least 5 bands.\n\n"
                "Expected:\n"
                "Band 1 -> Red\n"
                "Band 2 -> Green\n"
                "Band 3 -> NIR\n"
                "Band 4 -> Red Edge\n"
                "Band 5 -> Alpha\n\n"
                f"Found {band_count} bands."
            )

        print(
            "\nSpectral band configuration:"
        )

        print(
            "  Band 1 -> Red"
        )

        print(
            "  Band 2 -> Green"
        )

        print(
            "  Band 3 -> NIR"
        )

        print(
            "  Band 4 -> Red Edge"
        )

        print(
            "  Band 5 -> Alpha"
        )

        # =====================================================
        # SUPERPIXEL OPTIONS
        # =====================================================

        superpixel_options = (
            UserInterface
            .get_superpixel_options()
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

        if region_area <= 0:

            raise ValueError(
                "Region area must be greater than zero."
            )

        if tile_size <= 0:

            raise ValueError(
                "Tile size must be greater than zero."
            )

        print(
            "\n=== Superpixel Configuration ==="
        )

        print(
            f"Region Area --> "
            f"{region_area} m²"
        )

        print(
            f"Compactness --> "
            f"{compactness}"
        )

        print(
            f"Sigma --> "
            f"{sigma}"
        )

        print(
            f"Tile Size --> "
            f"{tile_size} pixels"
        )

        # =====================================================
        # ESTIMATE TOTAL REGIONS
        # =====================================================

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
            f"\nEstimated total regions --> "
            f"{estimated_regions:,}"
        )

        # =====================================================
        # PIXEL AREA
        # =====================================================

        pixel_area_m2 = (
            pixel_width *
            pixel_height
        )

        # =====================================================
        # RASTER LOADER
        # =====================================================

        loader = RasterLoader(
            ortho_path
        )

        all_regions = {}

        tile_number = 0

        # =====================================================
        # OPEN ORTHOMOSAIC
        # =====================================================

        with rasterio.open(
            ortho_path
        ) as src:

            total_tiles_x = int(
                np.ceil(
                    width /
                    tile_size
                )
            )

            total_tiles_y = int(
                np.ceil(
                    height /
                    tile_size
                )
            )

            total_tiles = (
                total_tiles_x *
                total_tiles_y
            )

            print(
                f"\nTotal tiles --> "
                f"{total_tiles:,}"
            )

            # =================================================
            # TILE LOOP
            # =================================================

            for row in range(
                0,
                src.height,
                tile_size
            ):

                for col in range(
                    0,
                    src.width,
                    tile_size
                ):

                    tile_start = time.time()

                    tile_number += 1

                    window_width = min(
                        tile_size,
                        src.width - col
                    )

                    window_height = min(
                        tile_size,
                        src.height - row
                    )

                    window = Window(
                        col_off=col,
                        row_off=row,
                        width=window_width,
                        height=window_height
                    )

                    tile_area_m2 = (
                        window_width *
                        window_height *
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
                        "\n" + "=" * 60
                    )

                    print(
                        f"TILE {tile_number} / "
                        f"{total_tiles}"
                    )

                    print(
                        f"Position: "
                        f"x={col}, y={row}"
                    )

                    print(
                        f"Dimensions: "
                        f"{window_width} × "
                        f"{window_height} pixels"
                    )

                    print(
                        f"Tile area: "
                        f"{tile_area_m2:,.2f} m²"
                    )

                    print(
                        f"Target region area: "
                        f"{region_area:.2f} m²"
                    )

                    print(
                        f"Target superpixels: "
                        f"{target_segments:,}"
                    )

                    print(
                        "=" * 60
                    )

                    # -----------------------------------------
                    # LOAD TILE
                    # -----------------------------------------

                    tile = loader.load_window(
                        window
                    )

                    # -----------------------------------------
                    # BAND DIAGNOSTICS
                    # -----------------------------------------

                    self._print_band_diagnostics(
                        tile
                    )

                    # -----------------------------------------
                    # SLIC
                    # -----------------------------------------

                    print(
                        "\n[1/3] Generating superpixels..."
                    )

                    segmenter = SuperpixelSegmenter(
                        num_segments=target_segments,
                        compactness=compactness,
                        sigma=sigma
                    )

                    labels = segmenter.run(
                        tile
                    )

                    if labels is None:

                        tile_elapsed = (
                            time.time() -
                            tile_start
                        )

                        print(
                            "\nTile "
                            f"{tile_number} skipped."
                        )

                        print(
                            f"Tile time: "
                            f"{tile_elapsed:.1f} seconds"
                        )

                        del tile
                        del segmenter

                        continue

                    valid_superpixels = np.unique(
                        labels[
                            labels >= 0
                        ]
                    ).size

                    print(
                        f"      Completed: "
                        f"{valid_superpixels:,} "
                        f"superpixels"
                    )

                    # -----------------------------------------
                    # VEGETATION INDICES
                    # -----------------------------------------

                    print(
                        "\n[2/3] Calculating "
                        "vegetation indices..."
                    )

                    vegetation = VegetationIndices(
                        tile
                    )

                    ndvi = vegetation.ndvi()

                    print(
                        "      NDVI      ✓"
                    )

                    gndvi = vegetation.gndvi()

                    print(
                        "      GNDVI     ✓"
                    )

                    ndre = vegetation.ndre()

                    print(
                        "      NDRE      ✓"
                    )

                    ci_red_edge = (
                        vegetation.ci_red_edge()
                    )

                    print(
                        "      CI-RE     ✓"
                    )

                    # -----------------------------------------
                    # FEATURE DIAGNOSTICS
                    # -----------------------------------------

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

                    # -----------------------------------------
                    # REGION FEATURE EXTRACTION
                    # -----------------------------------------

                    print(
                        "\n[3/3] Extracting "
                        "region statistics..."
                    )

                    extractor = (
                        RegionFeatureExtractor(
                            labels=labels,
                            pixel_area_m2=pixel_area_m2,
                            tile_number=tile_number
                        )
                    )

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

                    regions = (
                        extractor.get_features()
                    )

                    print(
                        f"      Regions extracted: "
                        f"{len(regions):,}"
                    )

                    # -----------------------------------------
                    # STORE RESULTS
                    # -----------------------------------------

                    all_regions.update(
                        regions
                    )

                    # -----------------------------------------
                    # RELEASE TILE MEMORY
                    # -----------------------------------------

                    del tile
                    del labels
                    del ndvi
                    del gndvi
                    del ndre
                    del ci_red_edge
                    del vegetation
                    del extractor
                    del segmenter

                    tile_elapsed = (
                        time.time() -
                        tile_start
                    )

                    completed_percent = (
                        tile_number /
                        total_tiles
                    ) * 100

                    average_tile_time = (
                        time.time() -
                        (
                            tile_start -
                            tile_elapsed
                        )
                    )

                    print(
                        "\nTile "
                        f"{tile_number} complete ✓"
                    )

                    print(
                        f"Tile time: "
                        f"{tile_elapsed:.1f} seconds"
                    )

                    print(
                        "Overall progress: "
                        f"{tile_number} / "
                        f"{total_tiles} "
                        f"({completed_percent:.1f}%)"
                    )

        # =====================================================
        # PIPELINE COMPLETE
        # =====================================================

        print(
            "\n=== Feature Pipeline Complete ==="
        )

        print(
            f"Total regions extracted --> "
            f"{len(all_regions):,}"
        )

        # =====================================================
        # SAVE CSV
        # =====================================================

        csv_path = (
            ortho_path.parent.parent /
            "region_features.csv"
        )

        self._save_regions_to_csv(
            all_regions,
            csv_path
        )

        self.results = all_regions

        self._print_sample_regions(
            all_regions
        )

        return all_regions

    # =========================================================
    # SAVE REGION FEATURES
    # =========================================================

    @staticmethod
    def _save_regions_to_csv(
        regions,
        output_path
    ):

        if not regions:

            print(
                "\nNo region data to save."
            )

            return

        output_path = Path(
            output_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        fieldnames = {
            "region_id"
        }

        for features in regions.values():

            fieldnames.update(
                features.keys()
            )

        fieldnames = sorted(
            fieldnames
        )

        if "region_id" in fieldnames:

            fieldnames.remove(
                "region_id"
            )

            fieldnames.insert(
                0,
                "region_id"
            )

        with open(
            output_path,
            "w",
            newline="",
            encoding="utf-8"
        ) as csv_file:

            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames
            )

            writer.writeheader()

            for region_id, features in (
                regions.items()
            ):

                row = {
                    "region_id": region_id
                }

                for name, value in (
                    features.items()
                ):

                    if isinstance(
                        value,
                        np.generic
                    ):

                        value = value.item()

                    row[name] = value

                writer.writerow(
                    row
                )

        print(
            "\n=== CSV Output ==="
        )

        print(
            f"Region feature CSV --> "
            f"{output_path}"
        )

        print(
            f"Rows written --> "
            f"{len(regions):,}"
        )

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
            "\nRAW BAND CHECK"
        )

        print(
            f"Shape: {bands.shape}"
        )

        names = [
            "Red",
            "Green",
            "NIR",
            "Red Edge",
            "Alpha"
        ]

        for index in range(
            bands.shape[0]
        ):

            band = bands[index]

            finite = np.isfinite(
                band
            )

            name = (
                names[index]
                if index < len(names)
                else "Unknown"
            )

            if not np.any(
                finite
            ):

                print(
                    f"Band {index + 1} "
                    f"({name}): "
                    f"NO FINITE VALUES"
                )

                continue

            values = band[
                finite
            ]

            print(
                f"Band {index + 1} "
                f"({name}): "
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
            f"{name} min: "
            f"{np.min(values)}"
        )

        print(
            f"{name} max: "
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
    # SAMPLE REGION OUTPUT
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
                    (float, np.floating)
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
                    #progress written in