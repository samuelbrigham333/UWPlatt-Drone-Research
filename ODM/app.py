import time


from ODM.docker_manager import DockerManager
from ODM.ui import UserInterface
from ODM.command_builder import ODMCommandBuilder
from ODM.runner import ODMRunner


class ODMApplication:

    def __init__(self):

        self.docker = DockerManager()

    def execute(self):

        if not self.docker.docker_running():
            self.docker.start_docker()

            print("Waiting for Docker to initialize...")

            while not self.docker.docker_running():
                time.sleep(10)      #10 seconds; verify


        #COLLECTS USER INPUTS
        image_path = UserInterface.get_project_path()

        output_path = UserInterface.get_output_path()

        project_name = UserInterface.get_project_name(output_path)

        options = UserInterface.get_pipeline_options()


        #CREATE ODM PROJECT FOLDER
        #IMAGES ARE MOUNTED DIRECTLY FOR OPTIMIZATION

        project_folder = output_path / project_name

        project_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        print("\nODM Project Created")
        print(project_folder)

        #BUILD DOCKER COMMAND

        builder = ODMCommandBuilder(
            image_path = image_path,
            output_path = output_path,
            project_name = project_name,
            options = options
        )

        command = builder.build_command()

        #EXECUTION
        runner = ODMRunner(command)

        runner.run()





