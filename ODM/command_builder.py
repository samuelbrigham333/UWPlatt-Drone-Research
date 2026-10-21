from pathlib import Path


class ODMCommandBuilder:
    def __init__(
        self,
        image_path,
        output_path,
        project_name,
        options,
        image_directory=None,
    ):
        self.image_path = Path(image_path).expanduser().resolve()
        self.image_directory = (
            Path(image_directory).expanduser().resolve()
            if image_directory is not None else None
        )
        self.output_path = Path(output_path).expanduser().resolve()
        self.project_name = project_name
        self.options = options

    def build_command(self):
        images = self.image_directory or self.image_path

        return [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{self.output_path}:/datasets",
            "-v",
            f"{images}:/datasets/{self.project_name}/images",
            "opendronemap/odm:3.6.1",
            "--project-path",
            "/datasets",
            self.project_name,
            "--split",
            str(self.options["split"]),
            "--split-overlap",
            str(self.options["split_overlap"]),
        ]