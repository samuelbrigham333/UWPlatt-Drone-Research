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
    image_files = [
        img for img in folder.iterdir() if img.suffix.lower() in valid_ext
    ]

    bad_files = []
    total = len(image_files)

    for index, img in enumerate(image_files, start=1):
        try:
            with open(img, "rb") as f:
                exifread.process_file(f, details=True, extract_thumbnail=False)

        except Exception as e:
            print(f"\nBAD FILE: {img.name}")
            print(e)

            bad_files.append(img.name)

        width = 30
        filled = width * index // total
        bar = "#" * filled + "-" * (width - filled)
        print(
            f"\rLoading photos: [{bar}] {index}/{total}",
            end="",
            flush=True,
        )

    if total:
        print()

    if bad_files:
        print("\nBad images found:")

        for name in bad_files:
            print(name)

        raise RuntimeError(f"{len(bad_files)} images have invalid EXIF metadata")

    print("Metadata validation passed.")
