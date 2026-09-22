import unittest

from lct_leaderboard.catalog import RuleCatalog
from lct_leaderboard.validator import validate_result_geojson


class ValidatorTest(unittest.TestCase):
    def test_validates_basic_submission(self):
        catalog = RuleCatalog.from_dict(
            {
                "score": {
                    "cost_weight": 0.7,
                    "cost_scale_rub": 25000000,
                    "length_weight": 0.3,
                    "length_scale_m": 100,
                },
                "pipe_catalog": [
                    {
                        "diameter_mm": 50,
                        "capacity_tph": 3.5,
                        "max_length_m": 181,
                        "new_rate_rub_per_m": 100,
                        "reconstruction_rate_rub_per_m": 200,
                    }
                ],
                "chamber_costs": [
                    {
                        "min_diameter_mm": 50,
                        "max_diameter_mm": 200,
                        "cost_rub": 3000,
                    }
                ],
                "unconnected_penalty": {"fixed_rub": 1000, "per_tph_rub": 10},
            }
        )
        result = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[1000, 1000], [1010, 1000]],
                    },
                    "properties": {
                        "id": "hn_1",
                        "object_type": "heat_network",
                        "variant_id": "v1",
                        "start_node_id": "a",
                        "end_node_id": "b",
                        "flow_tph": 3,
                        "diameter": 50,
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [10, 0]},
                    "properties": {
                        "id": "ch_1",
                        "object_type": "heat_chamber",
                        "variant_id": "v1",
                        "diameter": 50,
                    },
                },
                {
                    "type": "Feature",
                    "geometry": None,
                    "properties": {
                        "id": "v1_summary",
                        "object_type": "variant_summary",
                        "variant_id": "v1",
                        "calculated_cost": 4000,
                        "new_network_length": 10,
                        "length": 10,
                        "score": 0.31,
                        "unconnected_oks_ids": [],
                    },
                },
            ],
        }

        report = validate_result_geojson(result, catalog)

        self.assertTrue(report.accepted)
        self.assertEqual(report.metrics.calculated_cost, 4000)
        self.assertEqual(report.metrics.new_network_length, 10)

    def test_rejects_capacity_violation(self):
        catalog = RuleCatalog.from_dict(
            {
                "pipe_catalog": [
                    {
                        "diameter_mm": 50,
                        "capacity_tph": 3.5,
                        "max_length_m": 181,
                        "new_rate_rub_per_m": 100,
                        "reconstruction_rate_rub_per_m": 200,
                    }
                ],
                "chamber_costs": [],
            }
        )
        result = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[1000, 1000], [1001, 1000]],
                    },
                    "properties": {
                        "id": "hn_1",
                        "object_type": "heat_network",
                        "variant_id": "v1",
                        "start_node_id": "a",
                        "end_node_id": "b",
                        "flow_tph": 4,
                        "diameter": 50,
                    },
                },
                {
                    "type": "Feature",
                    "geometry": None,
                    "properties": {
                        "id": "v1_summary",
                        "object_type": "variant_summary",
                        "variant_id": "v1",
                        "calculated_cost": 100,
                        "new_network_length": 1,
                        "length": 1,
                        "score": 0.1,
                        "unconnected_oks_ids": [],
                    },
                },
            ],
        }

        report = validate_result_geojson(result, catalog)

        self.assertFalse(report.accepted)
        self.assertTrue(
            any(issue.code == "CAPACITY_VIOLATION" for issue in report.issues)
        )


if __name__ == "__main__":
    unittest.main()
