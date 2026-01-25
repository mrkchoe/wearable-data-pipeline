import random
import unittest

from scripts.generate_events import build_event


class TestGenerateEvents(unittest.TestCase):
    def test_identity_fields_are_omitted_or_non_empty(self) -> None:
        rng = random.Random(42)
        for idx in range(100):
            event = build_event("page_view", rng, f"2024-01-01T00:00:{idx:02d}Z")

            has_user_id = "user_id" in event
            has_anonymous_id = "anonymous_id" in event
            self.assertTrue(has_user_id or has_anonymous_id)

            if has_user_id:
                self.assertIsInstance(event["user_id"], str)
                self.assertTrue(event["user_id"].strip())

            if has_anonymous_id:
                self.assertIsInstance(event["anonymous_id"], str)
                self.assertTrue(event["anonymous_id"].strip())

            self.assertNotEqual(event.get("user_id"), "")
            self.assertNotEqual(event.get("anonymous_id"), "")


if __name__ == "__main__":
    unittest.main()
