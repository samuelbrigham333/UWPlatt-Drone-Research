"""
Application controller for the drone processing pipeline
Coordinates the complete workflow of the application
including
1. Collecting user input
2. Validating image metadate
3. Running the OpenDroneMap processing pipeline
4. Performing feature extraction on the resulting orthomosaic
5. Summarizing extracted features for future analysis

Class serves as the central coordinator between the user interface,
ODM processing, raster loading, adn feature extraction modules
"""

import time

from ODM.command_builder import ODMCommandBuilder
from ODM.docker_manager import DockerManager
from ODM.hsv_features import HSVFeatures
from ODM.runner import ODMRunner
from ODM.ui import UserInterface

from ODM.raster.raster_loader import RasterLoader
from ODM.raster.vegetation_indices import VegetationIndices
from ODM.feature_inspector import FeatureInspector

from ODM.validate_images import validate_images

class ODMApplication:

    def __init__(self):
        self.docker = DockerManager()

    def execute(self):
        choice = UserInterface.get_start_option()

        if choice == "1":
            ortho_path = self.run_odm_pipeline()

        elif choice == "2":

            ortho_path = UserInterface.get_ortho_options()

        else:
            print("Goodbye")
            return

        self.run_feature_extraction(ortho_path)


    def run_odm_pipeline(self):

        self.ensure_docker_running()

        image_path = UserInterface.get_project_path()

        validate_images(image_path)

        output_path = UserInterface.get_output_path()

        project_name = UserInterface.get_project_name(output_path)

        options = UserInterface.get_pipeline_options()

        project_folder = output_path / project_name

        project_folder.mkdir(
            parents = True,
            exist_ok=True
        )

        print ("\nODM Project Created")
        print(project_folder)

        builder = ODMCommandBuilder(
            image_path=image_path,
            output_path=output_path,
            project_name=project_name,
            options=options
        )

        command = builder.build_command()

        runner = ODMRunner(command)

        runner.run()

        print("\nODM Processing Complete.")

        return UserInterface.get_ortho_options()

    def ensure_docker_running(self):

        if self.docker.docker_running():

            return

        self.docker.start_docker()

        print("Waiting for Docker...")

        while not self.docker.docker_running():

            time.sleep(10)

    def run_feature_extraction(self, ortho_path):

        loader = RasterLoader(ortho_path)
        bands = loader.load()

        vegetation = VegetationIndices(bands)
        vegetation_features = vegetation.calculate_all()

        hsv = HSVFeatures(bands)
        hsv_features = hsv.calculate()

        all_features = {
            **vegetation_features,
            **hsv_features
        }

        inspector = FeatureInspector(all_features)
        results = inspector.summarize()

        print("\n === Feature Extraction Results ===")
        print(results)



