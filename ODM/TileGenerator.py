"""
Tile Generator

Generates rasterio Window objects for tile-by-tile processing
of large orthomosaics.
"""

from rasterio.windows import Window


class TileGenerator:

    def __init__(
        self,
        width,
        height,
        tile_size=2048,
    ):

        self.width = width
        self.height = height
        self.tile_size = tile_size

    # ============================================================
    # GENERATE TILES
    # ============================================================

    def __iter__(self):
        """
        Yield one rasterio Window at a time.

        Each Window contains:

            col_off
            row_off
            width
            height
        """

        for row in range(
            0,
            self.height,
            self.tile_size
        ):

            for col in range(
                0,
                self.width,
                self.tile_size
            ):

                tile_width = min(
                    self.tile_size,
                    self.width - col
                )

                tile_height = min(
                    self.tile_size,
                    self.height - row
                )

                yield Window(
                    col_off=col,
                    row_off=row,
                    width=tile_width,
                    height=tile_height
                )

    # ============================================================
    # NUMBER OF TILES
    # ============================================================

    def number_of_tiles(self):
        """
        Return the total number of tiles.
        """

        rows = (
            self.height +
            self.tile_size -
            1
        ) // self.tile_size

        cols = (
            self.width +
            self.tile_size -
            1
        ) // self.tile_size

        return rows * cols