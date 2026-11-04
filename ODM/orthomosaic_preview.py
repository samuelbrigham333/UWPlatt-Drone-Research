from pathlib import Path
import rasterio
from PIL import Image
import numpy as np


class OrthomosaicPreviewService:

    @staticmethod
    def inspect_raster(raster_path: str | Path):
        path = Path(raster_path).resolve()

        with rasterio.open(path) as dataset:
            width = dataset.width
            height = dataset.height
            band_count = dataset.count

            return width, height, band_count

    @staticmethod
    def read_rgb(raster_path: str | Path):
        path = Path(raster_path).resolve()

        with rasterio.open(path) as dataset:
            rgba = dataset.read([1, 2, 3, 4])

            print("Shape:", rgba.shape)
            print("Data type:", rgba.dtype)
            print("Value range:", rgba.min(), rgba.max())
            print("Color interpretation:", dataset.colorinterp)
            print("Data type per band:", dataset.dtypes)

            return rgba

    @staticmethod
    def create_preview(rgba):

        #move color bands from the first dimension to the last dimension
        image_array = np.moveaxis(rgba, 0, 2)

        #Convert NumPy array to PIL Image
        preview = Image.fromarray(image_array, mode = "RGBA")

        return preview 

    
        