"""Run ODM Docker processing and give useful errors while preserving live logs.

The existing Tauri bridge can still call ODMRunner(command).run().
"""

import os
import subprocess
from collections import deque


class ODMRunner:
    def __init__(self, command):
        self.command = command

    def _verify_gpu_access(self):
        """Check CUDA visibility inside the exact GPU image before a long job.

        Does not pull an uncached image just to check GPU accessibility.
        Use ODM_SKIP_GPU_PREFLIGHT=1 only when troubleshooting a false alarm.
        """
        if "--gpus" not in self.command or os.environ.get("ODM_SKIP_GPU_PREFLIGHT") == "1":
            return

        image = next(
            (item for item in self.command if item.startswith("opendronemap/odm:") and item.endswith("-gpu")),
            None,
        )
        if image is None:
            raise RuntimeError("NVIDIA selected, but the pinned ODM GPU image is missing.")

        # Do not pull a huge image just for the preflight. If the image is not
        # present yet, the normal ODM command will download it on first use.
        try:
            inspect = subprocess.run(
                ["docker", "image", "inspect", image],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError(f"Docker is unavailable: {error}") from error
        if inspect.returncode != 0:
            print("GPU image not cached yet; Docker will pull it on the first run.", flush=True)
            return

        print(f"Checking NVIDIA GPU access inside {image}...", flush=True)
        try:
            result = subprocess.run(
                ["docker", "run", "--rm", "--pull", "never", "--gpus", "all", "--entrypoint", "nvidia-smi", image],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=60,
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError(f"Could not verify NVIDIA GPU inside Docker: {error}") from error

        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise RuntimeError(
                "The ODM NVIDIA image was selected, but Docker could not access the GPU. "
                "Confirm Docker Desktop is running with the WSL2 Linux engine and "
                "that NVIDIA drivers / Docker GPU support work. "
                + (f"Docker error: {detail[-1200:]}" if detail else "")
            )
        print("NVIDIA GPU is accessible inside the ODM container.", flush=True)

    def run(self):
        print("\nRunning ODM...\n", flush=True)
        self._verify_gpu_access()

        # Stream logs unchanged to the terminal / Tauri, but keep a small tail
        # so 'exit code 1' can include the real OpenMVS failure reason.
        tail = deque(maxlen=250)
        saw_gpu_sift = False
        process = None
        try:
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="", flush=True)
                tail.append(line.strip().lower())
                if "using gpu for extracting sift features" in line.lower():
                    saw_gpu_sift = True
            returncode = process.wait()
        except FileNotFoundError as error:
            raise RuntimeError("Docker CLI not found. Install or start Docker Desktop.") from error
        except KeyboardInterrupt:
            if process is not None and process.poll() is None:
                process.terminate()
            raise
        finally:
            if process is not None and process.stdout is not None:
                process.stdout.close()

        if returncode == 0:
            if "--gpus" in self.command and not saw_gpu_sift:
                print(
                    "[WARNING] NVIDIA was available, but a GPU SIFT message was not seen. "
                    "The feature stage may have been skipped on resume; verify a fresh run's logs.",
                    flush=True,
                )
            print("ODM processing completed successfully.", flush=True)
            return

        recent = "\n".join(tail)
        if "no ply files available" in recent or (
            "densifying point-cloud completed: 0 points" in recent
        ):
            raise RuntimeError(
                "ODM OpenMVS produced an empty dense point cloud (no PLY files). "
                "GPU SIFT does not accelerate or repair OpenMVS densification. "
                "Check Docker RAM/swap, scene geometry/overlap, and the failed "
                "submodel. Existing submodels have NOT been deleted. "
                "Retry the same project/settings first; do not use --rerun-all."
            )
        if returncode == 137:
            raise RuntimeError(
                "ODM processing failed (exit code 137). Docker/WSL may have run out of memory. "
                "Keep concurrency low and increase Docker memory if the host has RAM available. "
                "Existing submodels were not deleted."
            )
        if returncode == 139:
            raise RuntimeError(
                "ODM processing failed (exit code 139, segmentation fault). "
                "Inspect earlier OpenMVS messages for zero valid points or invalid depth maps. "
                "GPU availability alone will not fix an empty reconstruction."
            )
        raise RuntimeError(f"ODM processing failed (exit code {returncode}).")
