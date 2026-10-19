"""
Handles ODM processing.

Responsibilities:
1. Verify Docker is running. (if docker is not running, begin running)
2. Collect ODM config
3. Validate source images
4. Build and execute ODM commands
5. Create an RGB-Only image directory (for rgb orthomosaic creation)
6. Locate and return BOTH orthomosaics (will produce a multispectral ortho and a RGB ortho)
"""

from pathlib import Path

from ODM.command_builder import ODMCommandBuilder
from ODM.docker_manager import DockerManager
from ODM.runner import ODMRunner
from ODM.ui import UserInterface
from ODM.validate_images import validate_images

class ODMProcessingService:
    def __init__(self, docker_manager=None, runner_class=ODMRunner):
        # Dependencies can be replaced during testing.
        self.docker_manager = docker_manager or DockerManager()
        self.runner_class = runner_class

    def process_images(self):
        """Run ODM for multispectral and RGB images."""

        print("\n=== ODM Processing ===")
        self._ensure_docker_running()

        config = UserInterface.get_odm_configuration()

        image_path = Path(config["image_path"])
        output_path = Path(config["output_path"])
        project_name = config["project_name"]
        options = config["pipeline_options"]

        # Validate the source images before starting ODM.
        print("\n=== Image Validation ===")
        print(f"Validating images in:\n{image_path}")
        validate_images(image_path)
        print("Metadata validation passed.")

        # Run the main ODM project.
        ortho_path = self._run_odm_project(
            image_path=image_path,
            output_path=output_path,
            project_name=project_name,
            options=options,
        )

        # Create a view containing only RGB images.
        rgb_directory = self._create_rgb_view(
            image_path,
            output_path,
            project_name,
        )

        # Run a second ODM project using only RGB images.
        rgb_project_name = f"{project_name}_rgb"

        self._run_odm_project(
            image_path=image_path,
            output_path=output_path,
            project_name=rgb_project_name,
            options=options,
            image_directory=rgb_directory,
        )

        rgb_ortho_path = self._find_orthomosaic(output_path / rgb_project_name)

        print("\n=== ODM Complete ===")
        print(f"Orthomosaic --> {ortho_path}")
        print(f"RGB Orthomosaic --> {rgb_ortho_path}")

        return ortho_path, rgb_ortho_path

    def _ensure_docker_running(self):
        """Start Docker Desktop if necessary and wait for readiness."""

        print("\n=== Docker Check ===")

        if self.docker_manager.docker_running():
            print("Docker is already running.")
            return

        print("Docker Desktop is not running.")
        self.docker_manager.start_docker()

        docker_ready = self.docker_manager.wait_for_docker(timeout=120)

        if not docker_ready:
            raise RuntimeError(
                "Docker Desktop was started, but the Docker daemon "
                "did not become ready within 120 seconds."
            )

        print("Docker Desktop is ready.")

    def _run_odm_project(
        self,
        image_path,
        output_path,
        project_name,
        options,
        image_directory=None,
    ):
        """Build and execute one ODM project."""

        command_builder = ODMCommandBuilder(
            image_path,
            output_path,
            project_name,
            options,
            image_directory=image_directory,
        )

        command = command_builder.build_command()

        print(f"\n=== ODM Command: {project_name} ===")
        print(
            " ".join(
                f'"{argument}"' if " " in str(argument) else str(argument)
                for argument in command
            )
        )

        print(f"\n=== Running ODM: {project_name} ===")
        runner = self.runner_class(command)
        runner.run()

        project_path = output_path / project_name
        return self._find_orthomosaic(project_path)

    @staticmethod
    def _find_orthomosaic(project_path):
        """Locate the generated orthomosaic in an ODM project."""

        project_path = Path(project_path)

        candidates = [
            project_path / "odm_orthophoto" / "odm_orthophoto.tif",
            project_path / "odm_orthophoto" / "odm_orthophoto.original.tif",
            project_path / "odm_orthophoto" / "odm_orthophoto.original.jpg",
            project_path / "odm_orthophoto" / "odm_orthophoto.rgb.tif",
        ]

        for candidate in candidates:
            if candidate.is_file():
                return candidate

        # Fallback: search recursively for an orthophoto.
        for pattern in ("*.tif", "*.jpg"):
            files = list(project_path.rglob(pattern))

            for file_path in files:
                if "orthophoto" in file_path.name.lower():
                    return file_path

            if files:
                return files[0]

        raise FileNotFoundError(
            "ODM completed, but an orthomosaic could not be found.\n"
            f"Project path:\n{project_path}"
        )

    @staticmethod
    def _get_rgb_images(image_path):
        """Return the RGB source images matching the existing convention."""

        rgb_images = list(Path(image_path).glob("*_D.JPG"))

        if not rgb_images:
            raise FileNotFoundError(f"No RGB images found in {image_path}")

        return rgb_images

    def _create_rgb_view(self, image_path, output_path, project_name):
        """Create a directory of hard links to RGB source images."""

        rgb_images = self._get_rgb_images(image_path)

        rgb_directory = Path(output_path) / ".rgb_temp" / project_name / "images"
        rgb_directory.mkdir(parents=True, exist_ok=True)

        for image in rgb_images:
            target = rgb_directory / image.name

            if not target.exists():
                target.hardlink_to(image)

        return rgb_directory
