"""Small cross-platform Docker helpers for the ODM command-line and Tauri apps.

This module does not alter ODM processing settings or install anything.
"""

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path


class DockerManager:
    def docker_running(self):
        """Return whether the local Docker daemon answers requests."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
            return result.returncode == 0
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return False

    def start_docker(self):
        """Start Docker Desktop if needed (Windows and macOS)."""
        if self.docker_running():
            print("Docker is already running.", flush=True)
            return

        system = platform.system()
        print("Starting Docker Desktop...", flush=True)

        if system == "Windows":
            if shutil.which("docker") is None:
                raise RuntimeError("Docker CLI is missing. Install Docker Desktop first.")

            try:
                subprocess.run(
                    ["docker", "desktop", "start", "--detach"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    timeout=30,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
                # Some Docker Desktop versions do not provide the `desktop start` CLI.
                desktop_exe = Path(r"C:\Program Files\Docker\Docker\Docker Desktop.exe")
                if not desktop_exe.is_file():
                    raise RuntimeError(
                        "Could not start Docker Desktop. Open Docker Desktop and retry."
                    ) from None
                subprocess.Popen(
                    [str(desktop_exe)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        elif system == "Darwin":
            subprocess.run(["open", "-a", "Docker"], check=True, timeout=30)
        else:
            raise RuntimeError(f"Unsupported operating system: {system}")

    def wait_for_docker(self, timeout=120):
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            if self.docker_running():
                print("Docker is ready.", flush=True)
                return True
            time.sleep(2)
        return False

    def nvidia_gpu_available(self):
        """Detect NVIDIA on Windows, including when nvidia-smi is not in PATH.

        This only checks the host driver. ODMRunner verifies Docker GPU access.
        Apple Silicon / Intel Macs continue to use the native CPU image.
        """
        if platform.system() != "Windows":
            return False
        if platform.machine().lower() not in ("amd64", "x86_64"):
            return False

        candidates = [shutil.which("nvidia-smi")]
        for variable in ("ProgramW6432", "ProgramFiles"):
            directory = os.environ.get(variable)
            if directory:
                candidates.append(str(Path(directory) / "NVIDIA Corporation" / "NVSMI" / "nvidia-smi.exe"))

        for executable in dict.fromkeys(item for item in candidates if item):
            try:
                result = subprocess.run(
                    [executable, "-L"], capture_output=True, text=True,
                    timeout=8, check=False,
                )
                if result.returncode == 0 and "GPU" in result.stdout:
                    return True
            except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
                continue
        return False

    def docker_memory_gib(self):
        """Read the memory available to Docker (not total host memory)."""
        try:
            result = subprocess.run(
                ["docker", "info", "--format", "{{.MemTotal}}"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                return None
            return int(result.stdout.strip()) / (1024 ** 3)
        except (FileNotFoundError, OSError, ValueError, subprocess.TimeoutExpired):
            return None

    def suggested_max_concurrency(self):
        """A conservative opt-in speed preset for high-quality, large ODM jobs.

        Images can be very large, so do NOT assume concurrency scales with CPU cores.
        Users may still override this with their existing max_concurrency setting.
        """
        ram = self.docker_memory_gib()
        if ram is None or ram < 28:
            return 1
        if ram < 44:
            return 2
        if ram < 64:
            return 3
        return 4
