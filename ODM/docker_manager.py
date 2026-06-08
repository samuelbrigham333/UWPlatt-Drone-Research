import subprocess


class DockerManager:

#checks if docker is running and accessible
    def docker_running(self):

        try:

            #tests the docker daemon
            result = subprocess.run(

                #execution command
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            #Returns true if the command succeeded
            return result.returncode == 0

        except FileNotFoundError:

            return False

#starts docker
    def start_docker(self):

        print("Starting Docker Desktop...")

        subprocess.Popen(
            r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
        )