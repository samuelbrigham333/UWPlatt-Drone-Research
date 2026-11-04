import unittest

from ODM.command_builder import ODMCommandBuilder


class OrthophotoResolutionTests(unittest.TestCase):
    def build(self, options):
        return ODMCommandBuilder(
            r"C:\images",
            r"C:\output",
            "project",
            {
                "split": 2,
                "split_overlap": 150,
                "pc_quality": "high",
                "feature_quality": "high",
                "max_concurrency": 1,
                **options,
            },
        ).build_command()

    def test_best_gsd_target_is_used_when_no_resolution_is_provided(self):
        command = self.build({})
        index = command.index("--orthophoto-resolution")
        self.assertEqual(command[index + 1], "1.0")

    def test_manual_resolution_is_preserved(self):
        command = self.build({"orthophoto_resolution": 8})
        index = command.index("--orthophoto-resolution")
        self.assertEqual(command[index + 1], "8.0")

    def test_gsd_target_is_used_for_blank_resolution(self):
        command = self.build({"orthophoto_resolution": ""})
        index = command.index("--orthophoto-resolution")
        self.assertEqual(command[index + 1], "1.0")


if __name__ == "__main__":
    unittest.main()
