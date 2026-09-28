from pathlib import Path

from ODM.command_builder import ODMCommandBuilder
from ODM.runner import ODMRunner

#WE DO NOT WANT TO COPY ALL THE IMAGES TO ANOTHER FILE
#THIS TAKES UP AN UNGODLY AMOUNT OF STORAGE AND IS UNECCESSARY.


class RGBOrthoBuilder:

    def __init__(self, 
                 image_directory, 
                 output_directory, 
                 project_name, 
                 pipeline_options
                 ):
        
        self.image_directory = Path(image_directory)
        self.output_directory = Path(output_directory)
        self.project_name = project_name
        self.pipeline_options = pipeline_options

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.project_directory = self.output_directory / self.project_name
       #dont need self.proejct_images likely keep for now delete later
        self.project_images = self.project_directory / "images"

        

        self.project_directory.mkdir(
            parents=True,
            exist_ok=True,
        )




    def get_rgb_images(self):
        return list(self.image_directory.glob("*_D.JPG"))

    def validate_images(self):
        images = self.get_rgb_images()

        if not images:
            raise FileNotFoundError(f"No RGB images found in {self.image_directory}")

        return images

    def build(self):
            images = self.validate_images()
            print(
                f"RGB image directory --> "
                f"{self.image_directory}"
            )

            

            print(
                f"RGB project directory --> "
                f"{self.project_directory}"
            )

            print(
                f"RGB pipeline options --> "
                f"{self.pipeline_options}"
            )

            rgb_command_builder = ODMCommandBuilder(
                self.image_directory,
                self.output_directory,
                self.project_name,
                self.pipeline_options,
            )


            rgb_command = (rgb_command_builder.build_command())

            print("\nRGB COMMAND LIST:")
            print(rgb_command)

            print(
                 "\n=== RGB Ortho Command ===\n"
            )
            print(
                 " ".join(
                      str(arg) for arg in rgb_command
                 )
            )

            rgb_runner = ODMRunner(
                rgb_command
            )

            rgb_runner.run()

#taking rgb ortho and building it into superpixel generation
#pipeline now runs superpixel generation, then rgb ortho generation then superpixel overlay generation on the rgb ortho