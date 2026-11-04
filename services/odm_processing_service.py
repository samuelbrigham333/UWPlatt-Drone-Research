"""
TEMPORARY RGB-RESUME VERSION of odm_processing_service.py.

For the previously completed ODM job, this version reuses an existing
odm_orthophoto.tif instead of rerunning the multispectral stage. It then
creates the RGB-only image directory and launches the RGB ODM pass.

Replace services/odm_processing_service.py with this file for the recovery run.
Restore your original service after the recovery run if you do not want
automatic reuse of existing multispectral orthomosaics.

Responsibilities:
1. Verify Docker is running (start it when configured).
2. Collect ODM configuration.
3. Validate source images.
4. Build and execute ODM commands when required.
5. Create an RGB-only image directory.
6. Locate and return both orthomosaics.
"""

import os
from pathlib import Path
import shutil

from ODM.command_builder import ODMCommandBuilder
from ODM.docker_manager import DockerManager
from ODM.runner import ODMRunner
from ODM.ui import UserInterface
from ODM.validate_images import validate_images


class ODMProcessingService:
    def __init__(self, docker_manager=None, runner_class=ODMRunner, stage_callback=None):
        # Dependencies can be replaced during testing.
        self.docker_manager = docker_manager or DockerManager()
        self.runner_class = runner_class
        self.stage_callback = stage_callback

    def _stage(self, label):
        if self.stage_callback:
            self.stage_callback(label)

    def process_images(self, config=None, auto_start_docker=True):
        """Run ODM for multispectral and RGB images."""

        print("\n=== ODM Processing ===")
        self._stage('Checking Docker')
        self._ensure_docker_running(auto_start_docker=auto_start_docker)

        # CLI keeps interactive prompts; Tauri passes the same configuration dictionary.
        if config is None:
            config = UserInterface.get_odm_configuration()

        image_path = Path(config["image_path"])
        output_path = Path(config["output_path"])
        project_name = config["project_name"]
        options = config["pipeline_options"]

        # Validate the source images before starting ODM.
        self._stage('Validating images')
        print("\n=== Image Validation ===")
        print(f"Validating images in:\n{image_path}")
        validate_images(image_path)

        # TEMPORARY: reuse the already-completed multispectral orthomosaic.
        # This check is meant for resuming your finished ODM job, not for
        # deliberately regenerating a project after changing the settings.
        existing_ortho = (
            output_path / project_name / "odm_orthophoto" / "odm_orthophoto.tif"
        )

        if existing_ortho.is_file():
            self._stage('Reusing completed multispectral orthomosaic')
            print(f"\nSkipping completed multispectral ODM pass: {existing_ortho}")
            ortho_path = existing_ortho
        else:
            self._stage('Processing multispectral orthomosaic')
            ortho_path = self._run_odm_project(
                image_path=image_path,
                output_path=output_path,
                project_name=project_name,
                options=options,
            )

        # Create a view containing only RGB images.
        self._stage('Preparing RGB files')
        rgb_directory = self._create_rgb_view(
            image_path,
            output_path,
            project_name,
        )

        # Run a second ODM project using only RGB images.
        self._stage('Processing RGB orthomosaic')
        rgb_project_name = f"{project_name}_rgb"

        self._run_odm_project(
            image_path=image_path,
            output_path=output_path,
            project_name=rgb_project_name,
            options=options,
            image_directory=rgb_directory,
        )

        rgb_ortho_path = self._find_orthomosaic(output_path / rgb_project_name)

        self._stage('ODM passes completed')
        print("\n=== ODM Complete ===")
        print(f"Orthomosaic --> {ortho_path}")
        print(f"RGB Orthomosaic --> {rgb_ortho_path}")

        return ortho_path, rgb_ortho_path

    def _ensure_docker_running(self, auto_start_docker=True):
        """Start Docker Desktop if necessary and wait for readiness."""

        print("\n=== Docker Check ===")

        if self.docker_manager.docker_running():
            print("Docker is already running.")
            return

        print("Docker Desktop is not running.")
        if not auto_start_docker:
            raise RuntimeError(
                'Docker is not running. Start Docker Desktop or enable auto-start in Settings.'
            )
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
        print(f"Docker image: {command[command.index('--project-path') - 1]}")
        print(f"Split size: {options['split']} | Overlap: {options['split_overlap']}")

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

        rgb_images = sorted(
            p for p in Path(image_path).iterdir()
            if p.is_file() and p.name.upper().endswith('_D.JPG')
        )

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
                try:
                    # Works with older macOS Python versions as well as Windows.
                    os.link(image, target)
                except OSError:
                    # Cross-volume drive or filesystem without hard links.
                    shutil.copy2(image, target)

        return rgb_directory
