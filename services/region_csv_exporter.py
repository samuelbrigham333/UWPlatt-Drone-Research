"""
Exports superpixel region statistics to CSV files
"""

import csv
from pathlib import Path

import numpy as np


class RegionCSVExporter:
    def export(self, regions, output_path):
        if not regions:
            print("\nNo region data to save.")
            return
        output_path = Path(output_path)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fieldnames = {"region_id"}

        for features in regions.values():
            fieldnames.update(features.keys())

        fieldnames = sorted(fieldnames)

        if "region_id" in fieldnames:
            fieldnames.remove("region_id")
            fieldnames.insert(0, "region_id")

        with open(
            output_path,
            "w",
            newline="",
            encoding="utf-8",
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            for region_id, features in regions.items():
                row = {"region_id": region_id}

                for name, value in features.items():
                    if isinstance(value, np.generic):
                        value = value.item()

                    row[name] = value

                writer.writerow(row)

        print("\n=== CSV Output ===")
        print(f"Region feature CSV --> {output_path}")
        print(f"Rows written --> {len(regions):,}")
