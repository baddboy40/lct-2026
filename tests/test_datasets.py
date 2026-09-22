import unittest

from lct_leaderboard.datasets import manifest_to_datasets


class DatasetsTest(unittest.TestCase):
    def test_manifest_to_datasets(self):
        manifest = {
            "dataset_version": "v1",
            "records": [
                {
                    "scene_id": "s1",
                    "parent_scene_id": "p1",
                    "split": "test",
                    "city": "Москва",
                    "research_bucket": "fifty_fifty",
                    "input": "data/s1.geojson",
                    "input_hash": "abc",
                    "feature_count": 10,
                    "restriction_count": 7,
                    "oks_count": 3,
                }
            ],
        }

        rows = manifest_to_datasets(manifest)

        self.assertEqual(rows[0]["id"], "s1")
        self.assertEqual(rows[0]["version"], "v1")
        self.assertFalse(rows[0]["is_public"])


if __name__ == "__main__":
    unittest.main()
