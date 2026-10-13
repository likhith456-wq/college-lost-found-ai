import unittest

from matching import compare_reports, rank_lost_found_matches, text_similarity


class MatchingTests(unittest.TestCase):
    def test_handles_empty_text_and_missing_photos(self):
        result = compare_reports(
            {"item_name": "", "description": "", "category": "", "location": ""},
            {"item_name": "", "description": "", "category": "", "location": ""},
        )
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["explanations"], [])

    def test_text_matching_uses_item_details_and_is_explainable(self):
        lost = {
            "item_name": "wallet",
            "category": "Daily-use items",
            "description": "Brown leather wallet with a silver badge",
            "location": "Main library",
            "created_at": "2026-10-10T12:00:00",
            "status": "Lost",
            "id": 1,
            "reporter_id": 1,
        }
        found = {
            "item_name": "wallet",
            "category": "Daily-use items",
            "description": "Brown leather wallet with silver badge",
            "location": "Main library",
            "created_at": "2026-10-11T12:00:00",
            "status": "Found",
            "id": 2,
            "reporter_id": 2,
        }
        result = compare_reports(lost, found, weights={"text": 1, "category": 1})
        self.assertGreater(result["score"], 0.5)
        self.assertIn("categories match", result["explanations"])

    def test_missing_images_and_empty_text_do_not_crash_ranker(self):
        reports = [
            {"id": 1, "status": "Lost", "item_name": "", "category": "", "description": "", "location": ""},
            {"id": 2, "status": "Found", "item_name": "", "category": "", "description": "", "location": ""},
        ]
        results = rank_lost_found_matches(reports)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["score"], 0)

    def test_same_reporter_own_pair_is_not_suggested(self):
        reports = [
            {"id": 1, "reporter_id": 7, "status": "Lost", "item_name": "keys"},
            {"id": 2, "reporter_id": 7, "status": "Found", "item_name": "keys"},
        ]
        self.assertEqual(rank_lost_found_matches(reports), [])

    def test_lost_and_found_text_is_similar(self):
        self.assertGreater(text_similarity("blue metal water bottle", "blue water bottle"), 0.5)


if __name__ == "__main__":
    unittest.main()
