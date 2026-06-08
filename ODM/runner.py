import subprocess


class ODMRunner:

    def __init__(self, command):

        self.command = command

    def run(self):

        print("\nRunning ODM...\n")

        print(" ".join(self.command))

        print()

        result = subprocess.run(self.command)

        if result.returncode != 0:

            raise RuntimeError("ODM processing failed")

        print("\nODM processing complete.")