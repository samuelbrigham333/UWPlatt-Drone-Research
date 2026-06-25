#not currently being used in the pipeline wait for removal

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