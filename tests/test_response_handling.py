import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import detect
from test_detect import COMMANDS, IMAGE, SUCCESS, FAILURE, invoke


class ResponseHandlingTests(unittest.TestCase):
    def test_null_data_is_diagnosable_for_every_renderer_without_retry(self):
        for argv in COMMANDS.values():
            for data in (None, [], "invalid"):
                with self.subTest(command=argv[0], data=data):
                    response = {"success": True, "data": data}
                    code, output, error, api = invoke(argv, response)
                    self.assertEqual(code, 1, error)
                    self.assertEqual(json.loads(output), response)
                    self.assertIn("原始响应", error)
                    self.assertNotIn("Traceback", error)
                    api.assert_called_once()
                    code, output, error, _ = invoke(argv + ["--json"], response)
                    self.assertEqual(code, 0, error)
                    self.assertEqual(json.loads(output), response)

    def test_malformed_arrays_and_nested_items_fail_before_rendering(self):
        samples = {
            "d001": [{"list": None}, {"list": [False]}, {"list": [{"similarity": "NaN"}]}],
            "i001": [{"data": None}], "c001": [{"list": None}],
            "p001": [{"list": None}], "p002": [{"list": None}, {"risk_feature_list": None}],
            "p007": [{"data": None}], "p004": [{"word_arr": None}], "t002": [{"words": [3]}],
            "t001": [{"text_trademarks": None}, {"text_trademarks": [{"region_risk_scores": None}]}],
            "l001": [{"detection_results": [{"top_graphic_trademarks": None}]},
                     {"detection_results": [{"top_graphic_trademarks": [{"graphic_trademarks": [None]}]}]}],
        }
        for command, cases in samples.items():
            for data in cases:
                response = {"success": True, "data": data}
                code, output, error, _ = invoke(COMMANDS[command], response)
                self.assertEqual(code, 1, error)
                self.assertEqual(json.loads(output), response)

    def test_risk_labels_follow_item_radar_and_tro_flags(self):
        for value in (True, 1, "1"):
            response = {"success": True, "data": {"list": [{"similarity": 0.2, "tro_holder": value}]}}
            code, output, error, _ = invoke(COMMANDS["d001"] + ["--no-radar"], response)
            self.assertEqual(code, 0, error)
            self.assertIn("1. 🔴高风险", output)
        for radar in ("high_risk", 1, "1", "low_risk", None):
            response = {"success": True, "data": {"detection_results": [{"top_graphic_trademarks": [
                {"graphic_trademarks": [{"similarity": 0.2, "sub_radar_result": radar}]}]}]}}
            for disabled in (False, True):
                code, output, error, _ = invoke(COMMANDS["l001"] + (["--no-radar"] if disabled else []), response)
                self.assertEqual(code, 0, error)
                self.assertEqual("1. 🔴高" in output, not disabled and radar in ("high_risk", 1, "1"))

    def test_paid_feature_results_and_evidence_links_survive_empty_policy_list(self):
        for policies in ([], [{"content_url": "https://example.com/policy"}]):
            for feature in ({"type": "example", "score": 65, "desc": "Example result"},
                            {"id": 12, "words": "Example feature", "hit": 1}):
                response = {"success": True, "data": {"list": policies, "risk_feature_list": [feature]}}
                code, output, error, _ = invoke(COMMANDS["p002"], response)
                self.assertEqual(code, 0, error)
                self.assertIn(json.dumps(feature, ensure_ascii=False), output)
                if policies:
                    self.assertIn("https://example.com/policy", output)
        response = {"success": True, "data": {"list": [{"pd_img_oss_url": "https://example.com/evidence.png"}]}}
        code, output, error, _ = invoke(COMMANDS["p001"], response)
        self.assertEqual(code, 0, error)
        self.assertIn("https://example.com/evidence.png", output)

    def test_current_and_legacy_trademark_fields_render_consistently(self):
        for legacy in (False, True):
            term = {"highest_mode_score": 4, "status": "Active"}
            term["trademark" if legacy else "trademark_name"] = "Example"
            for name in ("famous", "active_holder", "amazon_brand", "common_sense"):
                term[name if legacy else "is_" + name] = True
            term["region_score" if legacy else "region_risk_scores"] = [
                {"region": "US", "score" if legacy else "risk_score": 4}]
            response = {"success": True, "data": {"trademark_list" if legacy else "text_trademarks": [term]}}
            code, output, error, _ = invoke(COMMANDS["t001"], response)
            self.assertEqual(code, 0, error)
            for text in ("Example", "著名商标", "活跃维权人", "Amazon品牌", "常用词", "US:4"):
                self.assertIn(text, output)
        for field in ("suggestionNum", "suggestion_num"):
            code, output, error, _ = invoke(COMMANDS["p004"], {"success": True, "data": {field: 24}})
            self.assertEqual(code, 0, error)
            self.assertIn("联想词总数: 24", output)

    def test_expected_term_failure_continues_but_system_failure_stops(self):
        response = {"success": True, "data": {"text_trademarks": [
            {"trademark_name": "Alpha", "highest_mode_score": 4},
            {"trademark_name": "Beta", "highest_mode_score": 3}]}}
        for error_code, calls in ((4003009, 3), (4003010, 3), (30007, 2), (4000011, 2)):
            code, output, error, api = invoke(COMMANDS["t001"] + ["--text", "Description", "--auto-safe-words"],
                responses=[response, {"success": False, "code": error_code}, {"success": True, "data": {"words": ["alternative"]}}])
            self.assertEqual(code, 1, error)
            self.assertEqual(api.call_count, calls)
            self.assertEqual("alternative" in output, calls == 3)
            if calls == 3:
                self.assertIn("Alpha", error)
                self.assertEqual(error.count("T002 调用完成"), 1)

    def test_auto_followup_requires_text_only_when_it_will_run(self):
        for text in ("", "   "):
            with mock.patch.object(detect, "check_token", side_effect=AssertionError("No auth before validation")):
                code, _, error, api = invoke(COMMANDS["t001"] + ["--text", text, "--auto-safe-words"])
            self.assertEqual(code, 2, error)
            api.assert_not_called()
        code, _, error, api = invoke(COMMANDS["t001"] + ["--auto-safe-words", "--json"])
        self.assertEqual(code, 0, error)
        api.assert_called_once()
        code, output, error, api = invoke(COMMANDS["t001"] + ["--auto-safe-words", "--json", "--dry-run"])
        self.assertEqual(code, 0, error)
        self.assertNotIn("follow_up", json.loads(output))
        api.assert_not_called()

    def test_platform_normalization_and_duplicate_detection(self):
        code, output, error, _ = invoke(COMMANDS["p002"] + ["--platform-sites", '{" Amazon ":["US"],"tikTok":["SG"]}', "--dry-run"])
        self.assertEqual(code, 0, error)
        self.assertEqual(json.loads(output)["payload"]["platform_sites"], {"amazon": ["us"], "tiktok": ["sg"]})
        code, _, error, api = invoke(COMMANDS["p002"] + ["--platform-sites", '{"Amazon":["US"],"amazon":["UK"]}'])
        self.assertEqual(code, 2, error)
        api.assert_not_called()

    def test_mock_file_errors_name_the_option_file_and_remedy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "response.json"
            for content, message in ((b"{oops", "JSON 格式"), ('{"text":"中文"}'.encode("gbk"), "UTF-8")):
                path.write_bytes(content)
                code, _, error, api = invoke(COMMANDS["t001"] + ["--mock-response", str(path)], token="")
                self.assertEqual(code, 1)
                self.assertIn("--mock-response", error)
                # Diagnostics use repr so backslashes and control characters are escaped.
                self.assertIn(repr(str(path)), error)
                self.assertIn(message, error)
                api.assert_not_called()
            code, _, error, _ = invoke(COMMANDS["t001"] + ["--mock-response", directory], token="")
            self.assertEqual(code, 1)
            self.assertIn("--mock-response", error)
            path.write_text(json.dumps(SUCCESS), encoding="utf-8-sig")
            code, _, error, _ = invoke(COMMANDS["t001"] + ["--mock-response", str(path)], token="")
            self.assertEqual(code, 0, error)

    def test_image_separator_and_absolute_script_work_from_another_directory(self):
        import subprocess
        import sys
        script = Path(detect.__file__).resolve()
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-S", str(script), "d001", "--dry-run", "--regions", "US", "GB", "--", IMAGE],
                                    cwd=directory, capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["payload"]["regions"], ["US", "GB"])
