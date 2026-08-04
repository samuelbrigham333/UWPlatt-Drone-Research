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
        print("\n === Feature Pipeline ===")

        #LOAD ORTHOMOSIAC

        print("Loading orthomosaic...")

        loader = RasterLoader(ortho_path)
        bands = loader.load()

        #GENERATE SUPERPIXELS

        superpixel_options = UserInterface.get_superpixel_options()

        print("Generating superpixels...")

        segmenter = SuperpixelSegmenter(
            ortho_path,
            **superpixel_options
        )

        segmenter.run()

        labels = segmenter.get_labels()

        print(
            f"Generated {segmenter.get_number_of_regions()} superpixels."
        )

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

    
    # Docker


    def ensure_docker_running(self):

        if self.docker.docker_running():

            return

        self.docker.start_docker()

        print("Waiting for Docker...")

        while not self.docker.docker_running():

            time.sleep(10)