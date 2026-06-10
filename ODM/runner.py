import subprocess


class ODMRunner:

    def __init__(self, command):

        self.command = command

    def run(self):

        print("\nRunning ODM...\n")

        result = subprocess.run(self.command)

        if result.returncode != 0:
            raise RuntimeError("ODM processing failed.")
