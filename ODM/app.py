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

        print("\n========== Feature Pipeline ==========")

        #
        # Load orthomosaic
        #

        print("Loading orthomosaic...")

        loader = RasterLoader(ortho_path)

        bands = loader.load()

        #
        # Calculate vegetation indices
        #

        print("Calculating vegetation indices...")

        vegetation = VegetationIndices(bands)

        vegetation_features = vegetation.calculate_all()

        #
        # Calculate HSV features
        #

        print("Calculating HSV features...")

        hsv = HSVFeatures(bands)

        hsv_features = hsv.calculate()

        #
        # Merge all feature rasters
        #

        all_features = {

            **vegetation_features,

            **hsv_features

        }

        print(
            f"Generated {len(all_features)} feature rasters."
        )

        #
        # Generate superpixels
        #

        superpixel_options = UserInterface.get_superpixel_options()

        print("Generating superpixels...")

        segmenter = SuperpixelSegmenter(

            ortho_path,

            **superpixel_options

        )

        segmenter.run()

        print(
            f"Generated {segmenter.get_number_of_regions()} superpixels."
        )

        #
        # Extract region features
        #

        print("Extracting region features...")

        extractor = RegionFeatureExtractor(

            segmenter,

            all_features

        )

        region_features = extractor.extract_features()

        print(
            f"Extracted features for {len(region_features)} regions."
        )

        print("\nFeature pipeline complete.")

        return region_features

    
    # Docker


    def ensure_docker_running(self):

        if self.docker.docker_running():

            return

        self.docker.start_docker()

        print("Waiting for Docker...")

        while not self.docker.docker_running():

            time.sleep(10)