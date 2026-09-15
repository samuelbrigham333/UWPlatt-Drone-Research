"""
ODM command construction module.

Builds the Docker command used to execute the ODM
processing pipeline all based on user-provided input and processing options
"""

class ODMCommandBuilder:

    def __init__(self,
                 image_path,
                 output_path,
                 project_name,
                 options
                 ):
        self.image_path = image_path
        self.output_path = output_path
        self.project_name = project_name
        self.options = options

    def build_command(self):
        return[
            "docker",
            "run",

            "--rm",

            #ODM outputs
            "-v",
            f"{self.output_path}:/datasets",

            #OG Images
            "-v",
            f"{self.image_path}:/datasets/{self.project_name}/images",

            "opendronemap/odm:3.6.1",

            "--project-path",
            "/datasets",

            self.project_name,

            "--split",
            str(self.options["split"]),

            "--split-overlap",
            str(self.options["split_overlap"])
        ]

