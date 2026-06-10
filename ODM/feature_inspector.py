import numpy as np

class FeatureInspector:
    def __init__(self, indices):
        self.indices = indices

    def summarize(self):

        print("\n === Feature Summarization ===")

        features = {}

        for name, raster in self.indices.items():

            valid = raster[np.isfinite(raster)]

            if valid.size == 0:
                continue

            features[f"{name}_mean"] = float(np.mean(valid))
            features[f"{name}_std"] = float(np.std(valid))
            features[f"{name}_min"] = float(np.min(valid))
            features[f"{name}_max"] = float(np.max(valid))

            print(f"{name}")
            print(f" Mean : {features[f'{name}_mean']:.4f}")
            print(f" Std  : {features[f'{name}_std']:.4f}")
            print(f" Min  : {features[f'{name}_min']:.4f}")
            print(f" Max  : {features[f'{name}_max']:.4f}")
            print()

        return features   #should hopefully print out the values for ndvi and ndre that you have set up currently