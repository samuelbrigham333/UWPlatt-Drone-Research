"""
Tile Generator

Generates rasterio Window objects for tiles processing of
large orthomosaics
"""

from rasterio.windows import Window

class TileGenerator:

    def __init__(
            self,
            width,
            height,
            tile_size = 2048,
    ):

        self.width = width
        self.height = height
        self.tile_size = tile_size

    def __iter__(self):
        """
        Yield raster windows one tile at a time
        """

        for row in range(0, self.height, self.tile_size):

            for col in range(0, self.width, self.tile_size):

                tile_width = min(
                    self.tile_size,
                    self.width - col
                )

                tile_height = min(
                    self.tile_size,
                    self.height - row
                )

                yield Window(
                    col_off = col,
                    row_off = row,
                    width = tile_width,
                    height = tile_height
                )

        def number_of_tiles(self):
            """
            Return the total number of tiles.
            """

            rows = (self.height + self.tile_size - 1) // self.tile_size
            cols = (self.width + self.tile_size - 1) // self.tile_size

            return rows * cols
