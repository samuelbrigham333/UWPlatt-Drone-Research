
"""Build one ODM Docker command for Main.py and the Tauri frontend.

CPU processing uses ODM 3.6.2.
NVIDIA processing uses ODM 3.6.2-gpu.

Automatic GPU detection is the default. Orthophoto resolution can be
selected by the frontend or supplied by the CLI.
"""

import math
import os
import platform
import re
from pathlib import Path

try:
    from .docker_manager import DockerManager
except ImportError:
    from docker_manager import DockerManager


CPU_IMAGE = "opendronemap/odm:3.6.2"
GPU_IMAGE = "opendronemap/odm:3.6.2-gpu"

# Request high orthophoto detail while allowing ODM to respect GSD.
BEST_GSD_ORTHOPHOTO_RESOLUTION = 1.0


class ODMCommandBuilder:
    def __init__(
        self,
        image_path,
        output_path,
        project_name,
        options,
        image_directory=None
    ):
        self.image_path = Path(image_path).expanduser().resolve()
        self.image_directory = (
            Path(image_directory).expanduser().resolve()
            if image_directory is not None
            else None
        )
        self.output_path = Path(output_path).expanduser().resolve()
        self.project_name = str(project_name)
        self.options = options

    def build_command(self):
        options = self.options

        # ==========================================================
        # VALIDATE PROJECT NAME
        # ==========================================================
        if not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}",
            self.project_name
        ):
            raise ValueError("Invalid ODM project name.")

        # ==========================================================
        # PROCESSING SETTINGS
        # ==========================================================
        split = int(options["split"])
        overlap = float(options["split_overlap"])

        quality = str(options.get("pc_quality", "medium"))
        feature_quality = str(
            options.get("feature_quality", "high")
        )

        # Preserve the orthophoto-resolution feature from main.
        # When not specified, request the best GSD-limited detail.
        raw_resolution = options.get(
            "orthophoto_resolution",
            BEST_GSD_ORTHOPHOTO_RESOLUTION
        )

        if (
            raw_resolution is None
            or str(raw_resolution).strip() == ""
        ):
            resolution = BEST_GSD_ORTHOPHOTO_RESOLUTION
        else:
            try:
                resolution = float(raw_resolution)
            except (TypeError, ValueError):
                raise ValueError(
                    "Orthophoto resolution must be a positive "
                    "number or blank."
                )

        # Validate numeric processing settings.
        if (
            split < 1
            or not math.isfinite(overlap)
            or overlap < 0
            or not math.isfinite(resolution)
            or resolution <= 0
        ):
            raise ValueError(
                "Invalid ODM split, overlap, or resolution setting."
            )

        if quality not in (
            "lowest", "low", "medium", "high", "ultra"
        ):
            raise ValueError("Invalid point cloud quality.")

        if feature_quality not in (
            "low", "medium", "high", "ultra"
        ):
            raise ValueError("Invalid feature quality.")

        # ==========================================================
        # DETECT GPU / CPU
        # ==========================================================
        docker = DockerManager()

        gpu_mode = str(
            options.get("gpu_mode", "auto")
        ).strip().lower()

        if gpu_mode not in ("auto", "cpu", "nvidia"):
            raise ValueError(
                "GPU mode must be 'auto', 'cpu', or 'nvidia'."
            )

        # This application's NVIDIA integration targets Windows.
        if (
            gpu_mode == "nvidia"
            and platform.system() != "Windows"
        ):
            raise ValueError(
                "NVIDIA CUDA mode is supported on Windows "
                "only by this application."
            )

        if gpu_mode == "auto":
            if (
                platform.system() == "Windows"
                and docker.nvidia_gpu_available()
            ):
                gpu_mode = "nvidia"
            else:
                gpu_mode = "cpu"

        docker_image = (
            GPU_IMAGE
            if gpu_mode == "nvidia"
            else CPU_IMAGE
        )

        # ==========================================================
        # CONCURRENCY
        # ==========================================================
        # Preserve user settings and the existing environment override.
        requested_concurrency = os.environ.get(
            "ODM_MAX_CONCURRENCY",
            options.get("max_concurrency", 1)
        )

        recommended = docker.suggested_max_concurrency()

        if (
            str(requested_concurrency).strip().lower()
            == "auto"
        ):
            concurrency = recommended
        else:
            concurrency = int(requested_concurrency)

        if not 1 <= concurrency <= 64:
            raise ValueError(
                "Max concurrency must be between 1 and 64."
            )

        # Warn rather than silently changing the user's selection.
        if concurrency > recommended:
            print(
                f"[WARNING] Concurrency {concurrency} may "
                f"exhaust Docker RAM; the conservative "
                f"preset is {recommended}.",
                flush=True
            )

        # ==========================================================
        # VALIDATE IMAGE FOLDER
        # ==========================================================
        image_folder = (
            self.image_directory or self.image_path
        )

        if not image_folder.is_dir():
            raise FileNotFoundError(
                f"Input image folder not found: {image_folder}"
            )

        # ==========================================================
        # BUILD DOCKER COMMAND
        # ==========================================================
        command = ["docker", "run", "--rm"]

        # Keep the container naming used by Tauri Stop Processing.
        container_name = os.environ.get(
            "ODM_UI_CONTAINER_NAME", ""
        )

        if container_name:
            if not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}",
                container_name
            ):
                raise ValueError(
                    "Invalid Docker container name."
                )

            command.extend([
                "--name", container_name
            ])

        # Enable NVIDIA passthrough only in NVIDIA mode.
        if gpu_mode == "nvidia":
            command.extend(["--gpus", "all"])

        # ==========================================================
        # ODM ARGUMENTS
        # ==========================================================
        # Preserve the existing mounts and project structure.
        # The processing service can supply a prepared image_directory.
        command.extend([
            "-v",
            f"{self.output_path}:/datasets",

            "-v",
            f"{image_folder}:/datasets/{self.project_name}/images",

            docker_image,

            "--project-path", "/datasets",
            self.project_name,

            "--split", str(split),
            "--split-overlap", str(overlap),

            "--pc-quality", quality,
            "--feature-quality", feature_quality,

            # Frontend-selected or default orthophoto resolution.
            "--orthophoto-resolution", str(resolution),

            # Preserve lossless orthophoto compression.
            "--orthophoto-compression", "DEFLATE",

            "--max-concurrency", str(concurrency),
        ])

        # SIFT feature extraction can use NVIDIA acceleration.
        if gpu_mode == "nvidia":
            command.extend([
                "--feature-type", "sift"
            ])

        # Optional surface / terrain models.
        if options.get("dsm", False):
            command.append("--dsm")

        if options.get("dtm", False):
            command.append("--dtm")

        # ==========================================================
        # DISPLAY ACTIVE PROCESSING SETTINGS
        # ==========================================================
        print(
            f"ODM Docker image: {docker_image}",
            flush=True
        )

        print(
            f"GPU mode: {gpu_mode} | "
            f"Max concurrency: {concurrency}",
            flush=True
        )

        if gpu_mode == "nvidia":
            print(
                "NVIDIA selected: check ODM logs for "
                "'Using GPU for extracting SIFT features'.",
                flush=True
            )

        print(
            f"Quality preserved: "
            f"features={feature_quality}, "
            f"point cloud={quality}, "
            f"orthophoto target={resolution} cm/pixel, "
            f"split={split}, "
            f"overlap={overlap}m",
            flush=True
        )

        return command
