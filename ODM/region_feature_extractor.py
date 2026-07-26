"""
Region Feature Extraction

Uses superpixel labels to summarize future rasters
for EACH superpixel region.

"""

import numpy as np

class RegionFeatureExtractor:

    def __init__(self, labels, indices):

        self.labels = labels
        self.indices = indices

        #stores future final feature vectors
        self.region_features = {}

    def extract_features(self):
        """
        Extract features for every superpixel
        """

        self.region_features.clear()

        region_ids = np.unique(self.labels)

        for region_id in region_ids:
            self.region_features[region_id] = self._extract_region(region_id)

            return self.region_features

    def _extract_region(self, region_id):
        mask = self.labels == region_id

        features = {}

        features["area"] = int(np.count_nonzero(mask))

        for name, raster in self.indices.items():

            values = raster[mask]

            values = values[np.isfinite(values)]

            if values.size == 0:
                continue

            features[f"{name}_mean"] = float(np.mean(values))
            features[f"{name}_std"] = float(np.std(values))
            features[f"{name}_max"] = float(np.max(values))
            features[f"{name}_min"] = float(np.min(values))

            return features

    def get_features(self):
        return self.region_features