from pathlib import Path

import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

multispectral_path = Path(
    r"g:\Output\RGBTesting004\odm_orthophoto\odm_orthophoto.original.tif"
)  # path to multispectral ortho
rgb_path = Path(
    r"G:\Output\RGBTesting004_rgb\odm_orthophoto\odm_orthophoto.original.tif"
)  # path to rgb ortho

aligned_rgb_path = rgb_path.with_name(f"{rgb_path.stem}_aligned.tif")

with rasterio.open(multispectral_path) as reference:
    reference_profile = reference.profile.copy()

    target_crs = reference.crs
    target_transform = reference.transform
    target_width = reference.width
    target_height = reference.height

with rasterio.open(rgb_path) as source:
    if source.count <= 3:  # band check
        raise ValueError("RGB orthomosaic must habe at least 3 bands")

    # copy grid from multispectral orthomosaic
    profile = source.profile.copy()
    profile.update(
        driver="GTiff",
        width=target_width,
        height=target_height,
        count=3,
        crs=target_crs,
        transform=target_transform,
        nodata=0,
        dtype="uint8",
    )

    # throw grid onto rgb orthomosaic
    with rasterio.open(aligned_rgb_path, "w", **profile) as destination:
        for band in range(1, 4):
            reproject(
                source=rasterio.band(source, band),
                destination=rasterio.band(destination, band),
                src_transform=source.transform,
                src_crs=source.crs,
                src_nodata=source.nodata,
                dst_transform=target_transform,
                dst_crs=target_crs,
                dst_nodata=0,
                resampling=Resampling.bilinear,
            )

print(f"Aligned RGB orthomosaic created: {aligned_rgb_path}")

with rasterio.open(multispectral_path) as ms, rasterio.open(aligned_rgb_path) as rgb:
    print(f"Dimensions match: {ms.shape == rgb.shape}")
    print(f"Tranforms match: {ms.transform == rgb.transform}")
    print(f"CRS matches: {ms.crs == rgb.crs}")
