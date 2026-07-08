"""
Image validation module

Provides functionality for validating image metadata
Occurs BEFORE processing with ODM.
Each image is inspected to verify that EXIF metadata can be successfully read

This was implemented as a way to deal with corrupted drone images that were breaking the pipeline
"""

import exifread

def validate_images(folder):

    valid_ext = {".jpg", ".jpeg", ".tif", ".tiff"}

    bad_files = []

    for img in folder.iterdir():

        if img.suffix.lower() not in valid_ext:
            continue

        try:

            with open(img, "rb") as f:

                exifread.process_file(
                    f,
                    details=True,
                    extract_thumbnail=False
                )

        except Exception as e:

            print(f"\nBAD FILE: {img.name}")
            print(e)

            bad_files.append(img.name)

    if bad_files:

        print("\nBad images found:")

        for name in bad_files:
            print(name)

        raise RuntimeError(
            f"{len(bad_files)} images have invalid EXIF metadata"
        )

    print("Metadata validation passed.")