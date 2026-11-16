from rasterio.enums import Resampling

from orthomosaic_preview import OrthomosaicPreviewService


raster_path = (
    r"G:\Output\DJI_202605141609_004_MLDataHalfGrazed_SAMPLE3_rgb"
    r"\odm_orthophoto\odm_orthophoto.original.tif"
)

output_path = r"G:\Output\orthomosaic_preview_lanczos.png"


saved_path = OrthomosaicPreviewService.generate_preview(
    raster_path=raster_path,
    output_path=output_path,
    rgb_bands=(1, 2, 3),
    max_dimension=6000,
    resampling=Resampling.lanczos,
)

print("Preview saved to:", saved_path)