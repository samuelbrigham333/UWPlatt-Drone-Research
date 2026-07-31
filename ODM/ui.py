"""
Command-Line User Interface

Responsible for collecting user input and displaying different menus.
"""

from pathlib import Path

class UserInterface:

    # ==========================================================
    # MAIN MENU
    # ==========================================================

    @staticmethod
    def get_start_option():
        print("\n=== DRONE PROCESSING ===")
        print("1. Run ODM Processing")
        print("2. Analyze Existing Ortho")
        print("3. Exit")

        while True:
            choice = input("\nSelection --> ").strip()

            if choice in ("1", "2", "3"):
                return choice

            print("Invalid selection.\n")

    # ==========================================================
    # ODM WORKFLOW
    # ==========================================================

    @staticmethod
    def get_odm_configuration():
        print("\n=== ODM Configuration ===")

        image_path = UserInterface._get_existing_directory(
            "Image folder"
        )

        output_path = UserInterface._get_output_directory(
            "Output folder"
        )

        project_name = UserInterface._get_project_name(
            output_path
        )

        pipeline_options = UserInterface.get_pipeline_options()

        return {
            "image_path": image_path,
            "output_path": output_path,
            "project_name": project_name,
            "pipeline_options": pipeline_options,
        }

    # ==========================================================
    # FEATURE EXTRACTION
    # ==========================================================

    @staticmethod
    def get_orthomosaic_path():
        print("\n=== Feature Extraction ===")

        while True:
            path = Path(
                input("Orthomosaic (.tif) --> ").strip()
            ).expanduser().resolve()

            if not path.exists():
                print("File does not exist.\n")
                continue

            if path.suffix.lower() not in (".tif", ".tiff"):
                print("Must be a TIFF file.\n")
                continue

            return path

    # ==========================================================
    # SUPERPIXEL OPTIONS
    # ==========================================================

    @staticmethod
    def get_superpixel_options():
        print("\n=== Superpixel Options ===")

        while True:
            try:
                num_segments = int(
                    input("Approximate number of regions --> ")
                )

                compactness = float(
                    input("Compactness --> ")
                )

                sigma = float(
                    input("Sigma --> ")
                )

                if num_segments <= 0:
                    raise ValueError

                return {
                    "num_segments": num_segments,
                    "compactness": compactness,
                    "sigma": sigma,
                }

            except ValueError:
                print(
                    "Please enter valid numeric values "
                    "(refer to the notes).\n"
                )

    # ==========================================================
    # ODM OPTIONS
    # ==========================================================

    @staticmethod
    def get_pipeline_options():
        print("\n=== ODM Options ===")

        while True:
            try:
                split = int(input("Split Size --> "))
                overlap = int(input("Overlap Size --> "))

                if split <= 0 or overlap < 0:
                    raise ValueError

                break

            except ValueError:
                print("Invalid split settings.\n")

        while True:
            pc_quality = input(
                "Point Cloud Quality (low, medium, high) --> "
            ).strip().lower()

            if pc_quality in ("low", "medium", "high"):
                break

            print("Invalid option.\n")

        return {
            "split": split,
            "split_overlap": overlap,
            "pc_quality": pc_quality,
        }

    # ==========================================================
    # HELPER METHODS
    # ==========================================================

    @staticmethod
    def _get_existing_directory(prompt):
        while True:
            path = Path(
                input(f"{prompt} --> ").strip()
            ).expanduser().resolve()

            if path.exists() and path.is_dir():
                return path

            print("Directory not found.\n")

    @staticmethod
    def _get_output_directory(prompt):
        path = Path(
            input(f"{prompt} --> ").strip()
        ).expanduser().resolve()

        path.mkdir(parents=True, exist_ok=True)

        return path

    @staticmethod
    def _get_project_name(output_path):
        while True:
            name = input("Project Name --> ").strip()

            if not name:
                print("Project name cannot be empty.\n")
                continue

            if (output_path / name).exists():
                print("Project name already exists.\n")
                continue

            return name