from pathlib import Path

from frontend_bridge import generate_preview


def test_generate_preview():

    # Input orthomosaic
    raster_path = Path(
        r"G:\Output\DJI_202605141609_004_MLDataHalfGrazed_SAMPLE3_rgb"
        r"\odm_orthophoto\odm_orthophoto.original.tif"
    )

    # Where the preview should be saved
    output_path = Path(
        r"G:\Output\orthomosaic_preview.png"
    )

    # Generate preview
    result = generate_preview(
        raster_path=raster_path,
        output_path=output_path
    )

    # Retrieve returned preview path
    preview_file = Path(result['preview_path'])

    print("Preview saved to:", preview_file)

    # Verify that the file exists
    if preview_file.exists():
        print("SUCCESS: Preview file exists!")
    else:
        print("ERROR: Preview file was not found!")


if __name__ == "__main__":
    test_generate_preview()