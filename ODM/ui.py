import sys
from pathlib import Path


class UserInterface:


    @staticmethod
    def get_start_option():
        print("\n=== Drone Processing ===")
        print("1. ODM Processing")
        print("2. Analyze Existing Orthophoto")
        print("3. Exit Program")

        while True:

            choice = input("\nSelection --> ").strip()

            if choice in ["1", "2", "3"]:
                return choice

            print("Please enter valid option")

    @staticmethod
    def get_project_path():

        print("\n=== Input/Output Options ===")

        path = input("Enter image/project path --> ").strip()
        project_path = Path(path).expanduser().resolve()

        if not project_path.exists():
            raise ValueError("Input path does not exist.")

        return project_path


    @staticmethod
    def get_output_path():

        path = input("Enter output folder path --> ").strip()
        output_path = Path(path).expanduser().resolve()

        output_path.mkdir(parents=True, exist_ok=True)

        if not output_path.exists():
            raise ValueError("Output path does not exist")


        return output_path


    @staticmethod
    def get_project_name(output_path):

        while True:

            name = input("Enter output project name --> ").strip()

            if not name:
                print("Project name cannot be empty.\n")
                continue

            project_folder = output_path / name

            if project_folder.exists():
                print("Project already exists. Choose another name.\n")
                continue

            return name


    @staticmethod
    def get_pipeline_options():

        print("\n=== ODM Pipeline Options ===")

        while True:
            try:
                split = int(input("Split Size --> "))
                overlap = int(input("Overlap Size --> "))

                if split <= 0 or overlap < 0:
                    raise ValueError

                break

            except ValueError:
                print("Split must be > 0 and overlap must be >= 0")

        while True:
            pc_quality = input("PC Quality (low/medium/high) --> ").strip().lower()

            if pc_quality in ["low", "medium", "high"]:
                break

            print("Invalid option. Choose: low, medium, high")

        return {
            "split": split,
            "split_overlap": overlap,
            "pc_quality": pc_quality
        }

    @staticmethod
    def get_ortho_options():

        print("\n=== Next Steps ===")

        close = input(
            "Would you like to continue to feature extraction? (yes/no) "
        ).strip().lower()

        if close == "no":
            print("Ending session")
            sys.exit()

        print("Moving on...")

        while True:

            ortho = input(
                "\nPlease enter orthomosaic file path --> "
            ).strip()

            ortho_path = Path(ortho).expanduser().resolve()

            if not ortho_path.exists():
                print("File does not exist.\n")
                continue

            if ortho_path.suffix.lower() not in [".tif", ".tiff"]:
                print("Must be a TIFF file.\n")
                continue

            return ortho_path
