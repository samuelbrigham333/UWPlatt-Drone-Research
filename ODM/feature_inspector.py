"""
Feature summarization module

Computes descriptive stats for each extracted feature raster
The generated stats provide a concise numerical summary of
vegetation indicies and color features
These will be used for analysis

Responsible for examining vegetation-index data and reportign statistics about it
"""

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

            #performs this for every indices 
            print(f"{name}")
            print(f" Mean : {features[f'{name}_mean']:.4f}")
            print(f" Std  : {features[f'{name}_std']:.4f}")
            print(f" Min  : {features[f'{name}_min']:.4f}")
            print(f" Max  : {features[f'{name}_max']:.4f}")
            print()

        return features

    @staticmethod
    def print_feature_diagnostic(name, feature):
        #Step 1: Determine which values are finite.
        finite = np.isfinite(feature)


        #Step 2: Count finite and non-finite values.
        #check np.count_nonzero()
        finite_count = int(np.count_nonzero(finite))
        nan_count = int(np.count_nonzero(~finite))

        #Step 3: Print the feature name.
        print(f"{name} CHECK")
        
        #Step 4: Check whether any finite values exist
        if finite_count == 0:
            print(f"{name} contains no finite values.")
            return

        #Step 5: Calculate and print min, max, mean, and counts
        values = feature[finite]
        print(f"{name} min: {np.min(values)}")
        print(f"{name} max: {np.max(values)}")
        print(f"{name} mean: {np.mean(values)}") 
        print(f"{name} finite: {finite_count:,}")
        print(f"{name} NaN: {nan_count:,}")


        


        

        

