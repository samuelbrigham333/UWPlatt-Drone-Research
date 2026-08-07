"""
Region Feature Extraction

Summarize feature rasters for each superpixel region.
Features are added one at a time to minimalize memory usage.
"""

import numpy as np

class RegionFeatureExtractor:

    def __init__(self, labels):

        self.labels = labels
        self.region_features = {}

        # Cache unique region IDs
        self.region_ids = np.unique(labels)

        for region_id in self.region_ids:
            self.region_features[region_id] = {
                "area": int(np.count_nonzero(labels == region_id)),
            }

    # Public Interface

    def add_feature(self, feature_name, raster):

        for region_id in self.region_ids:

            stats = self._extract_region(
                region_id,
                raster,
            )

            self.region_features[region_id].update({
                f"{feature_name}_mean": stats["mean"],
                f"{feature_name}_std": stats["std"],
                f"{feature_name}_min": stats["min"],
                f"{feature_name}_max": stats["max"],
            })

    def get_features(self):
        return self.region_features

    def print_region_summary(self, region_id):

        if region_id not in self.region_features:
            raise ValueError(f"Region {region_id} does not exist.")

        region = self.region_features[region_id]

        print("=" * 60)
        print(f"Region {region_id} Summary")
        print("=" * 60)

        print(f"\nArea: {region['area']:,} pixels\n")

        groups = {}

        for key, value in region.items():

            if key == "area":
                continue

            feature, stat = key.rsplit("_", 1)
            groups.setdefault(feature, {})[stat] = value

        for feature in sorted(groups):

            print(feature)
            print("-" * len(feature))

            stats = groups[feature]

            for stat in ("mean", "std", "min", "max"):

                if stat in stats:
                    print(f"  {stat.capitalize():<4}: {stats[stat]:.4f}")

            print()

    # Private Methods

    def _extract_region(self, region_id, raster):

        mask = self.labels == region_id

        values = raster[mask]

        values = values[np.isfinite(values)]

        if values.size == 0:

            return {
                "mean": np.nan,
                "std": np.nan,
                "min": np.nan,
                "max": np.nan,
            }

        return {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
        }