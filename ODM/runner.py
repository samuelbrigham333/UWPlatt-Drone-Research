"""
ODM execution module

Execute the ODM Docker command and reports whether processing completed successfully
"""

import subprocess


class ODMRunner:
    def __init__(self, command):

        self.command = command

    def run(self):

        print("\nRunning ODM...\n")

        
        result = subprocess.run(self.command)

        if result.returncode != 0:
            print(f"\nDocker exit code: {result.returncode}")

            if result.returncode == 137:
                print("Possible out-of-memory termination (SIGKILL).")
            elif result.returncode == 139:
                print("Possible native segmentation fault (SIGSEGV).")

            raise RuntimeError(
                f"ODM processing failed (exit code {result.returncode})."
            )
