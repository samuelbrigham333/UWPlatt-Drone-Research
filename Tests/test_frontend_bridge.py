from pathlib import Path
from frontend_bridge import generate_preview 


raster_path = (
    r"G:\Output\DJI_202605141609_004_MLDataHalfGrazed_SAMPLE3_rgb\odm_orthophoto\odm_orthophoto.original.tif"
)

output_path = r"G:\Output\frontend_bridge_preview.png"

result = generate_preview(
    raster_path=raster_path,
    output_path=output_path,
)

print("Preview saved to:", result['preview_path'])

file_path = Path(result['preview_path'])
if file_path.is_file():
    print("File exists:", file_path)
else:
    print("File does not exist:")

    