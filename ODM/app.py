"""
Application controller for the drone processing pipeline.

Coordinates the complete application workflow.

Workflow
--------
1. User chooses workflow.
2. Optionally run OpenDroneMap.
3. Load orthomosaic.
4. Calculate feature rasters.
5. Generate superpixels.
6. Extract region features.
"""

import time

import numpy as np

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

    # =====================================================
    # Main Application
    # =====================================================

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

    # =====================================================
    # ODM Processing
    # =====================================================

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

        #
        # We now ask where the orthophoto is.
        # Eventually this can be automated.
        #

        return UserInterface.get_orthomosaic_path()

    # =====================================================
    # Feature Extraction Pipeline
    # =====================================================

    def run_feature_pipeline(self, ortho_path):
        print("\n === Feature Pipeline ===")

        #LOAD ORTHOMOSIAC

        print("Loading orthomosaic...")







        loader = RasterLoader(ortho_path)

        bands = loader.load()

        metadata = loader.get_metadata()


        total_area = self._calculate_total_area(metadata)

        superpixel_options = UserInterface.get_superpixel_options()

        num_segments = self._calculate_num_segments(total_area, superpixel_options["region_area"])

        generator = TileGenerator(
            width=metadata["width"],
            height=metadata["height"],
            tile_size=superpixel_options["tile_size"]
        )

        print("\nOrthomosaic Information")
        print("-------------------------")

        print(f"Resolution              : {metadata['pixel_width']:.3f} m/pixel")
        print(f"Total Area              : {total_area:,.2f} m²")
        print(f"Desired Region Size     : {superpixel_options['region_area']:.2f} m²")
        print(f"Estimated Region        : {num_segments:,}")


        print("Generating superpixels...")

        rgb = np.moveaxis(bands[:3], 0, -1)
        rgb -= rgb.min()
        if rgb.max() > 0:
            rgb /= rgb.max()

        segmenter = SuperpixelSegmenter(
            num_segments = num_segments,
            compactness = superpixel_options["compactness"],
            sigma = superpixel_options["sigma"]
        )

        labels = segmenter.run(rgb)
        print(f"Generated {len(np.unique(labels))} superpixels.")

        #optional debug feature
        segmenter.visualize()

        extractor = RegionFeatureExtractor(labels)

        #VEGETATION FEATURES
        print("Calculating vegetation indices...")

        vegetation = VegetationIndices(bands)

        ndvi = vegetation.ndvi()
        extractor.add_feature("NDVI", ndvi)
        del ndvi

        gndvi = vegetation.gndvi()
        extractor.add_feature("GNDVI", gndvi)
        del gndvi

        ndre = vegetation.ndre()
        extractor.add_feature("NDRE", ndre)
        del ndre

        ci = vegetation.ci_red_edge()
        extractor.add_feature("CI_RedEdge", ci)
        del ci

        evenson = vegetation.evenson()
        extractor.add_feature("EVENSON", evenson)
        del evenson

        #HSV FEATURES

        print("Calculating HSV features...")

        hsv = HSVFeatures(bands)

        hsv_features = hsv.calculate()

        extractor.add_feature("Hue", hsv_features["Hue"])
        extractor.add_feature("Saturation", hsv_features["Saturation"])
        extractor.add_feature("Value", hsv_features["Value"])

        del hsv_features

        #FINISHED

        region_features = extractor.get_features()

        print(
            f"Extracted features for {len(region_features)} regions."
        )

        #debug output
        if region_features:
            first_region = next(iter(region_features))

            print(f"\nExample Region: {first_region}")

            for key, value in region_features[first_region].items():
                print(f"{key}: {value}")

            print("\nFeature pipeline complete.")

            return region_features



    def _calculate_total_area(self, metadata):
        pixel_area = (
            metadata["pixel_width"] *
            metadata["pixel_height"]
        )

        return(
            metadata["width"] *
            metadata["height"] *
            pixel_area
        )

    def _calculate_num_segments(
            self,
            total_area,
            desired_region_area
    ):
        return max(
            1,
            round(total_area / desired_region_area)
        )

    # Docker


    def ensure_docker_running(self):

        if self.docker.docker_running():

            return

        self.docker.start_docker()

        print("Waiting for Docker...")

        while not self.docker.docker_running():

            time.sleep(10)

