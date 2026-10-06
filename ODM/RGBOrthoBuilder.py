from pathlib import Path
import shutil

class RGBOrthoBuilder:

    def __init__(self, image_path, rgb_path):
        self.image_path = Path(image_path)
        self.rgb_path = Path(rgb_path)
        self.rgb_images_path = self.rgb_path / "images"

    def filter_rgb_images(self):
        rgb_images = [
            image for image in self.image_path.iterdir()
            if image.is_file() and image.suffix.lower() in {".jpg", ".jpeg"}

        ]

        return rgb_images


    def create_rgb_folder(self):
        #creates location for filtered out rgb images
        self.rgb_images_path.mkdir(parents=True, exist_ok=True)

    def copy_rgb_images(self):
        rgb_images = self.filter_rgb_images

        for image in rgb_images:
            destination = self.rgb_images_path / image.name
            shutil.copy2(image, destination)

    def build_rgb_dataset(self):
        self.create_rgb_folder
        self.copy_rgb_images