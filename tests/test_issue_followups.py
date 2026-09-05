import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import post_issue_followups as followups


class FollowupTests(unittest.TestCase):
    def test_identical_bot_comment_is_not_posted_twice(self):
        existing = {"id": 123, "user": {"login": "github-actions[bot]"},
                    "body": "Verified fix\n\n" + followups.MARKER, "html_url": "https://example.com/123"}
        request = mock.Mock(return_value=[existing])
        self.assertEqual(followups.publish_comment(1, "Verified fix", request), ("unchanged", existing["html_url"]))
        request.assert_called_once_with("GET", "issues/1/comments?per_page=100&page=1")

    def test_changed_bot_comment_is_updated_without_duplicate(self):
        existing = {"id": 123, "user": {"login": "github-actions[bot]"},
                    "body": "Old text\n\n" + followups.MARKER}
        request = mock.Mock(side_effect=[[existing], {"html_url": "https://example.com/123"}])
        self.assertEqual(followups.publish_comment(1, "New text", request)[0], "updated")
        self.assertEqual(request.call_args.args[:2], ("PATCH", "issues/comments/123"))

    def test_human_comment_is_preserved_and_pagination_is_followed(self):
        human = {"id": 1, "user": {"login": "reporter"}, "body": followups.MARKER}
        request = mock.Mock(side_effect=[[human] * 100, [], {"html_url": "https://example.com/new"}])
        self.assertEqual(followups.publish_comment(2, "Fix details", request)[0], "created")
        self.assertEqual(request.call_args_list[1].args, ("GET", "issues/2/comments?per_page=100&page=2"))
        self.assertEqual(request.call_args.args, ("POST", "issues/2/comments", {"body": "Fix details\n\n" + followups.MARKER}))

    def test_validation_rejects_duplicate_or_out_of_scope_issues(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "comments.json"
            for comments in ([{"issue": 17, "body": "text"}], [{"issue": 1, "body": "text"}] * 2):
                path.write_text(json.dumps({"repository": followups.REPOSITORY, "comments": comments}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    followups.load_followups(path)

    def test_default_mode_validates_without_network_or_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "comments.json"
            path.write_text(json.dumps({"repository": followups.REPOSITORY, "comments": [{"issue": 1, "body": "Fix details"}]}), encoding="utf-8")
            with mock.patch.object(followups, "github_request") as request, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(followups.main([str(path)]), 0)
                request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
