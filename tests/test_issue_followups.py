import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import importlib.util

spec = importlib.util.spec_from_file_location("post_issue_followups", Path(__file__).resolve().parents[1] / ".github/scripts/post_issue_followups.py")
followups = importlib.util.module_from_spec(spec)
spec.loader.exec_module(followups)
MARKER = "<!-- eric-cli-followup-test-batch -->"


class FollowupTests(unittest.TestCase):
    def test_new_issue_numbers_and_separate_batches_are_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            markers = []
            for name in ("first", "second"):
                path = Path(directory) / (name + ".json")
                path.write_text(json.dumps({"repository": followups.REPOSITORY, "comments": [{"issue": 99999, "body": "Reviewed"}]}))
                comments, marker = followups.load_followups(path)
                self.assertEqual(comments[0]["issue"], 99999)
                markers.append(marker)
            self.assertNotEqual(*markers)
            existing = {"user": {"login": "github-actions[bot]"}, "body": "Old\n\n" + markers[0]}
            request = mock.Mock(side_effect=[[existing], {"html_url": "https://example.com/new"}])
            followups.publish_comment(99999, "Reviewed", request, markers[1])
            self.assertEqual(request.call_args.args[0], "POST")

    def test_issue_is_closed_only_after_its_reviewed_reply_succeeds(self):
        comment = {"issue": 40, "body": "Documented behavior", "close_reason": "not_planned"}
        request = mock.Mock(side_effect=[[], {"html_url": "https://example.com/reply"}, {"state": "open"}, {}])
        followups.publish_followup(comment, MARKER, request)
        self.assertEqual(request.call_args_list[1].args[0:2], ("POST", "issues/40/comments"))
        self.assertEqual(request.call_args.args, ("PATCH", "issues/40", {"state": "closed", "state_reason": "not_planned"}))
        request = mock.Mock(side_effect=OSError("cannot publish"))
        with self.assertRaises(OSError):
            followups.publish_followup(comment, MARKER, request)
        self.assertEqual(request.call_count, 1)

    def test_batch_ids_and_close_reasons_cannot_inject_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            for patch in ({"batch_id": "-->bad"}, {"comments": [{"issue": True, "body": "x"}]},
                          {"comments": [{"issue": 18, "body": "x", "close_reason": "reopen"}]}, {"repository": "untrusted/elsewhere"}):
                data = {"repository": followups.REPOSITORY, "comments": [{"issue": 18, "body": "Reviewed"}]}
                data.update(patch)
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    followups.load_followups(path)

    def test_identical_bot_comment_is_not_posted_twice(self):
        existing = {"id": 123, "user": {"login": "github-actions[bot]"},
                    "body": "Verified fix\n\n" + MARKER, "html_url": "https://example.com/123"}
        request = mock.Mock(return_value=[existing])
        self.assertEqual(followups.publish_comment(1, "Verified fix", request, MARKER), ("unchanged", existing["html_url"]))
        request.assert_called_once_with("GET", "issues/1/comments?per_page=100&page=1")

    def test_changed_bot_comment_is_updated_without_duplicate(self):
        existing = {"id": 123, "user": {"login": "github-actions[bot]"},
                    "body": "Old text\n\n" + MARKER}
        request = mock.Mock(side_effect=[[existing], {"html_url": "https://example.com/123"}])
        self.assertEqual(followups.publish_comment(1, "New text", request, MARKER)[0], "updated")
        self.assertEqual(request.call_args.args[:2], ("PATCH", "issues/comments/123"))

    def test_human_comment_is_preserved_and_pagination_is_followed(self):
        human = {"id": 1, "user": {"login": "reporter"}, "body": MARKER}
        request = mock.Mock(side_effect=[[human] * 100, [], {"html_url": "https://example.com/new"}])
        self.assertEqual(followups.publish_comment(2, "Fix details", request, MARKER)[0], "created")
        self.assertEqual(request.call_args_list[1].args, ("GET", "issues/2/comments?per_page=100&page=2"))
        self.assertEqual(request.call_args.args, ("POST", "issues/2/comments", {"body": "Fix details\n\n" + MARKER}))

    def test_validation_rejects_duplicate_or_out_of_scope_issues(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "comments.json"
            for comments in ([{"issue": 0, "body": "text"}], [{"issue": 1, "body": "text"}] * 2):
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
