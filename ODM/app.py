"""
Application controller for the drone processing pipeline.

Coordinates the complete application workflow.

Workflow
--------
1. User chooses workflow.
2. Optionally run OpenDroneMap.
3. Read orthomosaic metadata.
4. Generate tiles.
5. Process each tile independently.
6. Generate superpixels for each tile.
7. Calculate feature rasters for each tile.
8. Extract region features.
"""

import time

from ODM.TileGenerator import TileGenerator
from ODM.command_builder import ODMCommandBuilder
from ODM.docker_manager import DockerManager
from ODM.runner import ODMRunner
from ODM.ui import UserInterface

from ODM.validate_images import validate_images

from ODM.raster.raster_loader import RasterLoader
from ODM.raster.vegetation_indices import VegetationIndices

from ODM.hsv_features import HSVFeatures

from ODM.superpixel_segmenter import SuperpixelSegmenter
from ODM.region_feature_extractor import RegionFeatureExtractor


class ODMApplication:

    def __init__(self):

        self.docker = DockerManager()

    # MAIN APPLICATION

    def execute(self):

        choice = UserInterface.get_start_option()

        if choice == "1":

            ortho_path = self.run_odm_pipeline()

        elif choice == "2":

            ortho_path = UserInterface.get_orthomosaic_path()

        else:

            print("\nGoodbye.")
            return

        self.run_feature_pipeline(ortho_path)

    # ODM PROCESSING

    def run_odm_pipeline(self):

        self.ensure_docker_running()

        config = UserInterface.get_odm_configuration()

        validate_images(config["image_path"])

        project_folder = (
            config["output_path"] /
            config["project_name"]
        )

        project_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        print("\nODM Project")
        print(project_folder)

        builder = ODMCommandBuilder(

            image_path=config["image_path"],

            output_path=config["output_path"],

            project_name=config["project_name"],

            options=config["pipeline_options"]

        )

        command = builder.build_command()

        runner = ODMRunner(command)

        runner.run()

        print("\nODM Processing Complete.")

        return UserInterface.get_orthomosaic_path()

    # FEATURE PIPELINE

    def run_feature_pipeline(self, ortho_path):

        print("\n=== Feature Pipeline ===")

        # READ METADATA ONLY

        print("\nReading orthomosaic information...")

        loader = RasterLoader(ortho_path)

        metadata = loader.get_metadata()

        total_area = self._calculate_total_area(metadata)

        print("\nOrthomosaic Information")
        print("-------------------------")

        print(
            f"Resolution          : "
            f"{metadata['pixel_width']:.3f} m/pixel"
        )

        print(
            f"Total Area          : "
            f"{total_area:,.2f} m²"
        )

        # GET SUPERPIXEL OPTIONS

        superpixel_options = (
            UserInterface.get_superpixel_options()
        )

        num_segments = self._calculate_num_segments(
            total_area,
            superpixel_options["region_area"]
        )

        print(
            f"Desired Region Size : "
            f"{superpixel_options['region_area']:.2f} m²"
        )

        print(
            f"Estimated Regions   : "
            f"{num_segments:,}"
        )

        print(
            f"Tile Size           : "
            f"{superpixel_options['tile_size']} × "
            f"{superpixel_options['tile_size']} pixels"
        )

        # CREATE TILE GENERATOR

        generator = TileGenerator(
            width=metadata["width"],
            height=metadata["height"],
            tile_size=superpixel_options["tile_size"]
        )

        # CREATE SUPERPIXEL SEGMENTER

        segmenter = SuperpixelSegmenter(
            image_path=ortho_path,
            num_segments=num_segments,
            compactness=superpixel_options["compactness"],
            sigma=superpixel_options["sigma"]
        )

        # PROCESS TILES

        all_region_features = {}

        tile_number = 0

        for tile in generator.generate():

            tile_number += 1

            print(
                f"\nProcessing tile {tile_number}..."
            )

            print(
                f"Position: "
                f"({tile['x']}, {tile['y']})"
            )

            print(
                f"Size: "
                f"{tile['width']} × {tile['height']}"
            )

            # GENERATE SUPERPIXELS

            print("Generating superpixels...")

            labels = segmenter.run(tile)

            region_count = len(set(labels.flatten()))

            print(
                f"Generated {region_count} "
                f"superpixels in tile."
            )

            # LOAD ONLY THIS TILE'S BANDS

            bands = loader.load_window(
                tile["x"],
                tile["y"],
                tile["width"],
                tile["height"]
            )

            # REGION FEATURE EXTRACTION

            extractor = RegionFeatureExtractor(labels)

            # VEGETATION FEATURES

            print("Calculating vegetation indices...")

            vegetation = VegetationIndices(bands)

            ndvi = vegetation.ndvi()
            extractor.add_feature(
                "NDVI",
                ndvi
            )
            del ndvi

            gndvi = vegetation.gndvi()
            extractor.add_feature(
                "GNDVI",
                gndvi
            )
            del gndvi

            ndre = vegetation.ndre()
            extractor.add_feature(
                "NDRE",
                ndre
            )
            del ndre

            ci = vegetation.ci_red_edge()
            extractor.add_feature(
                "CI_RedEdge",
                ci
            )
            del ci

            evenson = vegetation.evenson()
            extractor.add_feature(
                "EVENSON",
                evenson
            )
            del evenson

            # HSV FEATURES

            print("Calculating HSV features...")

            hsv = HSVFeatures(bands)

            hsv_features = hsv.calculate()

            extractor.add_feature(
                "Hue",
                hsv_features["Hue"]
            )

            extractor.add_feature(
                "Saturation",
                hsv_features["Saturation"]
            )

            extractor.add_feature(
                "Value",
                hsv_features["Value"]
            )

            del hsv_features
            del hsv

            # SAVE TILE RESULTS

            tile_features = extractor.get_features()

            print(
                f"Extracted features for "
                f"{len(tile_features)} regions."
            )

            # ADD TILE RESULTS TO MASTER RESULTS

            all_region_features.update(
                tile_features
            )

            # RELEASE TILE MEMORY

            del bands
            del labels
            del extractor

        # PIPELINE COMPLETE

        print("\n=== Feature Pipeline Complete ===")

        print(
            f"Total regions extracted: "
            f"{len(all_region_features):,}"
        )

        return all_region_features

    # AREA CALCULATION

    def _calculate_total_area(self, metadata):

        pixel_area = (
            metadata["pixel_width"] *
            metadata["pixel_height"]
        )

        return (
            metadata["width"] *
            metadata["height"] *
            pixel_area
        )

    # SUPERPIXEL CALCULATION

    def _calculate_num_segments(
        self,
        total_area,
        desired_region_area
    ):

        return max(
            1,
            round(
                total_area /
                desired_region_area
            )
        )

    # DOCKER

    def ensure_docker_running(self):

        if self.docker.docker_running():

            return

        self.docker.start_docker()

        print("Waiting for Docker...")

        while not self.docker.docker_running():

            time.sleep(10)

