"""Build one ODM Docker command for both Main.py and the Tauri frontend.

ODM stays pinned to 3.6.2. High-quality reconstruction and multispectral
processing settings are preserved. Auto GPU selection is opt-in via
options['gpu_mode'] == 'auto' (and is the default when the mode is omitted).
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


class ODMCommandBuilder:
    def __init__(self, image_path, output_path, project_name, options, image_directory=None):
        self.image_path = Path(image_path).expanduser().resolve()
        self.image_directory = (
            Path(image_directory).expanduser().resolve()
            if image_directory is not None else None
        )
        self.output_path = Path(output_path).expanduser().resolve()
        self.project_name = str(project_name)
        self.options = options

    def build_command(self):
        options = self.options
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", self.project_name):
            raise ValueError("Invalid ODM project name.")

        split = int(options["split"])
        overlap = float(options["split_overlap"])
        quality = str(options.get("pc_quality", "medium"))
        feature_quality = str(options.get("feature_quality", "high"))
        resolution = float(options.get("orthophoto_resolution", 5))

        if (split < 1 or not math.isfinite(overlap) or overlap < 0
                or not math.isfinite(resolution) or resolution <= 0):
            raise ValueError("Invalid ODM split, overlap, or resolution setting.")
        if quality not in ("lowest", "low", "medium", "high", "ultra"):
            raise ValueError("Invalid point cloud quality.")
        if feature_quality not in ("low", "medium", "high", "ultra"):
            raise ValueError("Invalid feature quality.")

        docker = DockerManager()
        gpu_mode = str(options.get("gpu_mode", "auto")).strip().lower()
        if gpu_mode not in ("auto", "cpu", "nvidia"):
            raise ValueError("GPU mode must be 'auto', 'cpu', or 'nvidia'.")
        if gpu_mode == "nvidia" and platform.system() != "Windows":
            raise ValueError("NVIDIA CUDA mode is supported on Windows only by this app.")
        if gpu_mode == "auto":
            gpu_mode = (
                "nvidia" if platform.system() == "Windows" and docker.nvidia_gpu_available()
                else "cpu"
            )

        docker_image = GPU_IMAGE if gpu_mode == "nvidia" else CPU_IMAGE

        # Existing UI values take precedence. A value of 'auto' requests the
        # conservative memory-based speed preset; it does NOT reduce quality.
        requested_concurrency = os.environ.get(
            "ODM_MAX_CONCURRENCY", options.get("max_concurrency", 1)
        )
        if str(requested_concurrency).strip().lower() == "auto":
            concurrency = docker.suggested_max_concurrency()
        else:
            concurrency = int(requested_concurrency)
        if not 1 <= concurrency <= 64:
            raise ValueError("Max concurrency must be between 1 and 64.")

        # Do not silently change the user's quality or concurrency preferences.
        # OpenMVS densification can need much more RAM than CUDA SIFT extraction.
        recommended = docker.suggested_max_concurrency()
        if concurrency > recommended:
            print(
                f"[WARNING] Concurrency {concurrency} may exhaust Docker RAM; "
                f"the conservative preset is {recommended}.", flush=True,
            )

        image_folder = self.image_directory or self.image_path
        if not image_folder.is_dir():
            raise FileNotFoundError(f"Input image folder not found: {image_folder}")

        command = ["docker", "run", "--rm"]

        # Preserve the container name used by Tauri's Stop Processing feature.
        container_name = os.environ.get("ODM_UI_CONTAINER_NAME", "")
        if container_name:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", container_name):
                raise ValueError("Invalid Docker container name.")
            command.extend(["--name", container_name])

        if gpu_mode == "nvidia":
            command.extend(["--gpus", "all"])

        # Keep the SAME mounts and source folder layout as the original code.
        # RGB and multispectral imagery stay together and ODM groups the bands.
        command.extend([
            "-v", f"{self.output_path}:/datasets",
            "-v", f"{image_folder}:/datasets/{self.project_name}/images",
            docker_image,
            "--project-path", "/datasets", self.project_name,
            "--split", str(split),
            "--split-overlap", str(overlap),
            "--pc-quality", quality,
            "--feature-quality", feature_quality,
            "--orthophoto-resolution", str(resolution),
            "--max-concurrency", str(concurrency),
        ])

        # Explicit SIFT is required for ODM's NVIDIA SIFT acceleration.
        if gpu_mode == "nvidia":
            command.extend(["--feature-type", "sift"])  # GPU SIFT, not GPU OpenMVS
        if options.get("dsm", False):
            command.append("--dsm")
        if options.get("dtm", False):
            command.append("--dtm")

        print(f"ODM Docker image: {docker_image}", flush=True)
        print(f"GPU mode: {gpu_mode} | Max concurrency: {concurrency}", flush=True)
        if gpu_mode == "nvidia":
            print("NVIDIA selected: watch for 'Using GPU for extracting SIFT features' in ODM logs.", flush=True)
        print(
            f"Quality preserved: features={feature_quality}, point cloud={quality}, "
            f"orthophoto={resolution} cm/pixel, split={split}, overlap={overlap}m",
            flush=True,
        )
        return command
