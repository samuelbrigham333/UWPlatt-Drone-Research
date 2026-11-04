from orthomosaic_preview import OrthomosaicPreviewService

raster_path = r"G:\Output\RGBTesting004_rgb\odm_orthophoto\odm_orthophoto.original_rgb.tif"

rgb = OrthomosaicPreviewService.read_rgb(raster_path)

print("\n--- Preview Test Results ---")
print("Shape:", rgb.shape)
print("Data type:", rgb.dtype)
print("Minimum:", rgb.min())
print("Maximum:", rgb.max())