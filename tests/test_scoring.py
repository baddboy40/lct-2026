import unittest

from lct_leaderboard.scoring import DatasetScore, build_leaderboard


class ScoringTest(unittest.TestCase):
    def test_leaderboard_uses_tiebreakers_within_threshold(self):
        entries = build_leaderboard(
            [
                DatasetScore("slow", "d1", 0.901, 100, 100, 20, True),
                DatasetScore("fast", "d1", 0.900, 110, 110, 10, True),
            ],
            ["d1"],
        )

        self.assertEqual(entries[0].team_id, "fast")

    def test_leaderboard_sorts_by_score_outside_threshold(self):
        entries = build_leaderboard(
            [
                DatasetScore("better", "d1", 0.910, 120, 120, 20, True),
                DatasetScore("fast", "d1", 0.900, 100, 100, 10, True),
            ],
            ["d1"],
        )

        self.assertEqual(entries[0].team_id, "better")


if __name__ == "__main__":
    unittest.main()
