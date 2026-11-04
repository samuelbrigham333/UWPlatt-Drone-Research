"""
Docker management module

Provides functionality for verifying that Docker Desktop is running
and available before executing the ODM pipeline
"""

import platform
import shutil
import subprocess
import time


class DockerManager:
    # checks if docker is running and accessible
    def docker_running(self):

        try:
            # tests the docker daemon
            result = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )

            # Returns true if the command succeeded
            return result.returncode == 0

        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    # starts docker
    def start_docker(self):

        if self.docker_running():
            print("Docker is already running.")
            return

        print("Starting Docker Desktop...")

        system = platform.system()

        if system == "Windows":
            # Start Docker Desktop using its CLI
            if shutil.which("docker") is None:
                raise RuntimeError("Docker CLI is not installed or not in PATH.")

            subprocess.run(
                ["docker", "desktop", "start", "--detach"], check=True, timeout=30
            )

        elif system == "Darwin":
            # Start Docker Desktop on macOS
            subprocess.run(["open", "-a", "Docker"], check=True)

        else:
            raise RuntimeError(f"Unsupported operating system: {system}")

    # waits for docker
    # waits for docker to finish starting
    def wait_for_docker(self, timeout=120):
        start_time = time.monotonic()

        while time.monotonic() - start_time < timeout:
            if self.docker_running():
                print("Docker is ready.")
                return True

            time.sleep(2)

        return False
