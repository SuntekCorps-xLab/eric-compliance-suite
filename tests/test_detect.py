import base64
import builtins
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts import detect


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
IMAGE = str(FIXTURES / "sample.png")
COMMANDS = {
    "d001": ["d001", IMAGE],
    "i001": ["i001", "--title", "Lamp", "--description", "Folding lamp"],
    "l001": ["l001", IMAGE],
    "t001": ["t001", "--title", "Lamp"],
    "t002": ["t002", "--title", "Lamp", "--text", "Folding lamp", "--trademark", "Example"],
    "c001": ["c001", IMAGE],
    "p001": ["p001", IMAGE],
    "p002": ["p002", "--title", "Lamp"],
    "p004": ["p004", "knife"],
    "p005": ["p005", "knife"],
    "p006": ["p006", "123"],
    "p007": ["p007"],
}
PATHS = {
    "d001": "patent/design/v1/detection", "i001": "patent/utility/v1/detection",
    "l001": "trademark/graphic/v1/detection", "t001": "trademark/text/v1/detection",
    "t002": "trademark/text/v1/safe-words-generation", "c001": "copyright/v1/detection",
    "p001": "policy-compliance/v1/gun-parts-search", "p002": "policy-compliance/v1/detection",
    "p004": "policy-compliance/feature/v1/suggestion", "p005": "policy-compliance/feature/v1/save",
    "p006": "policy-compliance/feature/v1/delete", "p007": "policy-compliance/feature/v1/list",
}
SUCCESS = {"success": True, "code": 200, "data": {}, "request_id": "test-success"}
FAILURE = json.loads((FIXTURES / "api-error.json").read_text(encoding="utf-8"))


def invoke(argv, response=None, responses=None, token="test-secret"):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        with mock.patch.dict(os.environ, {"ERIC_API_TOKEN": token}):
            with mock.patch.object(detect, "api_call", return_value=copy.deepcopy(response or SUCCESS),
                                   side_effect=copy.deepcopy(responses)) as api:
                with mock.patch.object(detect, "ensure_requests", side_effect=AssertionError("Unexpected network access")):
                    try:
                        code = detect.main(argv)
                    except SystemExit as exc:
                        code = exc.code
    return code, stdout.getvalue(), stderr.getvalue(), api


class RequestLifecycleTests(unittest.TestCase):
    def test_every_command_dry_run_matches_live_payload_and_auth_wiring(self):
        costs = dict(zip(COMMANDS, (15, 10, 15, 1, 1, 2, 1, 5, 0, 0, 0, 0)))
        for command, argv in COMMANDS.items():
            with self.subTest(command=command):
                code, output, error, api = invoke(argv + ["--dry-run"], token="")
                self.assertEqual(code, 0, error)
                api.assert_not_called()
                preview = json.loads(output)
                self.assertEqual(preview["url"], detect.BASE + "/" + PATHS[command])
                self.assertEqual(preview["method"], "POST")
                self.assertEqual(preview["estimated_points"], costs[command])
                self.assertEqual(preview["points_consumed"], 0)
                self.assertFalse(preview["token_configured"])
                code, _, error, api = invoke(argv + ["--json"])
                self.assertEqual(code, 0, error)
                self.assertEqual(api.call_args.args[:3], ("test-secret", PATHS[command], preview["payload"]))
                if command in ("d001", "l001", "c001", "p001"):
                    payload = preview["payload"]
                    encoded = payload.get("base64_image") or payload["img_64lis"][0]
                    self.assertEqual(base64.b64decode(encoded), Path(IMAGE).read_bytes())

    def test_dry_run_never_exposes_configured_token(self):
        code, output, error, api = invoke(COMMANDS["t001"] + ["--dry-run"], token="do-not-print-me")
        self.assertEqual(code, 0)
        self.assertNotIn("do-not-print-me", output + error)
        self.assertTrue(json.loads(output)["token_configured"])
        self.assertEqual(json.loads(output)["headers"]["Token"], "<redacted>")
        api.assert_not_called()

    def test_every_command_json_is_one_raw_response_on_success_and_failure(self):
        for argv in COMMANDS.values():
            for response, expected in ((SUCCESS, 0), (FAILURE, 1)):
                with self.subTest(command=argv[0], success=response["success"]):
                    code, output, error, api = invoke(argv + ["--json"], response)
                    self.assertEqual(code, expected, error)
                    self.assertEqual(json.loads(output), response)
                    api.assert_called_once()
                    self.assertNotIn("本次检测实际扣点", error)
                    self.assertEqual("调用完成" in error, expected == 0)
                    if expected:
                        self.assertIn("扣点未确认", error)

    def test_all_renderers_handle_success_and_no_match(self):
        for argv in COMMANDS.values():
            with self.subTest(command=argv[0]):
                code, _, error, api = invoke(argv)
                self.assertEqual(code, 0, error)
                self.assertEqual(error.count("调用完成"), 1)
                api.assert_called_once()

    def test_p001_no_match_still_reports_successful_estimate(self):
        for items in ([], ["No similar products found"]):
            code, output, error, _ = invoke(COMMANDS["p001"], {"success": True, "data": {"list": items}})
            self.assertEqual(code, 0)
            self.assertIn("未找到相似违规产品", output)
            self.assertIn("调用完成，预计扣点: 1 点", error)
            self.assertEqual(error.count("调用完成"), 1)

    def test_mock_mode_works_without_token_for_all_commands(self):
        for argv in COMMANDS.values():
            with self.subTest(command=argv[0]):
                code, output, error, api = invoke(argv + ["--mock-response", str(FIXTURES / "p001-no-match.json"), "--json"], token="")
                self.assertEqual(code, 0, error)
                self.assertTrue(json.loads(output)["success"])
                self.assertIn("消耗 0 点", error)
                api.assert_not_called()

    def test_mock_error_exits_nonzero_with_json(self):
        code, output, error, api = invoke(COMMANDS["t001"] + ["--mock-response", str(FIXTURES / "api-error.json"), "--json"], token="")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output), FAILURE)
        self.assertNotIn("调用完成", error)
        api.assert_not_called()

    def test_auto_safe_words_counts_only_successful_followups(self):
        trademark = {"success": True, "data": {"text_trademarks": [
            {"trademark_name": "One", "highest_mode_score": 4},
            {"trademark_name": "Two", "highest_mode_score": 3},
        ]}}
        code, _, error, api = invoke(COMMANDS["t001"] + ["--auto-safe-words"], responses=[trademark, SUCCESS, FAILURE])
        self.assertEqual(code, 1)
        self.assertEqual(api.call_count, 3)
        self.assertEqual(error.count("T002 调用完成"), 1)
        self.assertIn("扣点未确认", error)

    def test_mock_followups_never_fall_back_to_live_requests(self):
        trademark = {"success": True, "data": {"text_trademarks": [{"trademark_name": "One", "highest_mode_score": 4}]}}
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "responses.json"
            for response, expected in ((trademark, 1), ([trademark, SUCCESS], 0)):
                fixture.write_text(json.dumps(response), encoding="utf-8")
                code, _, error, api = invoke(COMMANDS["t001"] + ["--auto-safe-words", "--mock-response", str(fixture)], token="")
                self.assertEqual(code, expected, error)
                api.assert_not_called()

    def test_radar_cost_and_feature_cost(self):
        for command, points in (("d001", 10), ("l001", 10), ("c001", 1)):
            code, output, _, _ = invoke(COMMANDS[command] + ["--no-radar", "--dry-run"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["estimated_points"], points)
            self.assertFalse(json.loads(output)["payload"]["enable_radar"])
        code, output, error, _ = invoke(COMMANDS["p002"] + ["--enable-feature", "--feature-word-ids", "[12, 34]", "--feature-image", "https://example.com/lamp.jpg", "--dry-run"])
        self.assertEqual(code, 0, error)
        self.assertEqual(json.loads(output)["estimated_points"], 9)


class ValidationTests(unittest.TestCase):
    def test_feature_detection_requires_image_before_network(self):
        argv = COMMANDS["p002"] + ["--enable-feature", "--feature-word-ids", "[12]"]
        for image_args in ([], ["--feature-image", "   "]):
            code, output, error, api = invoke(argv + image_args, token="")
            self.assertEqual(code, 2, error)
            self.assertEqual(output, "")
            self.assertIn("--feature-image", error)
            api.assert_not_called()
        code, output, error, api = invoke(argv + ["--feature-image", "https://example.com/lamp.jpg", "--dry-run"], token="")
        self.assertEqual(code, 0, error)
        features = json.loads(output)["payload"]["feature_detect"]["features"]
        self.assertEqual(features, {"feature_word_ids": [12], "image": "https://example.com/lamp.jpg"})
        api.assert_not_called()

    def test_invalid_inputs_fail_before_any_api_call(self):
        invalid = [
            ["t001", "--title", "x" * 301], ["t001", "--title", "   "],
            COMMANDS["t001"] + ["--text", "x" * 5001],
            COMMANDS["i001"] + ["--title", "x" * 501],
            COMMANDS["i001"] + ["--description", "x" * 30001],
            COMMANDS["t002"] + ["--text", "x" * 5001],
            COMMANDS["p002"] + ["--description", "x" * 5001],
            COMMANDS["d001"] + ["--regions", "ZZ"],
            COMMANDS["i001"] + ["--regions", "GB"],
            COMMANDS["t001"] + ["--regions", "NL"],
            COMMANDS["l001"] + ["--regions", "ZZ"],
            COMMANDS["d001"] + ["--patent-status", "2"],
            COMMANDS["d001"] + ["--enable-radar", "--no-radar"],
            COMMANDS["p002"] + ["--sites", "gb"],
            COMMANDS["p002"] + ["--platform-sites", "{"],
            COMMANDS["p002"] + ["--platform-sites", "[]"],
            COMMANDS["p002"] + ["--platform-sites", "{}"],
            COMMANDS["p002"] + ["--platform-sites", '{"amazon":"us"}'],
            COMMANDS["p002"] + ["--platform-sites", '{"amazon":[]}'],
            COMMANDS["p002"] + ["--platform-sites", '{"amazon":["gb"]}'],
            COMMANDS["p002"] + ["--feature-word-ids", "{}"],
            COMMANDS["p002"] + ["--enable-feature", "--feature-word-ids", "[true]"],
            COMMANDS["p002"] + ["--enable-feature", "--feature-word-ids", "[0]"],
            COMMANDS["p002"] + ["--enable-feature", "--feature-word-ids", "[12,12]"],
            COMMANDS["p002"] + ["--feature-word-ids", "[12]"],
            COMMANDS["p002"] + ["--enable-feature"],
            COMMANDS["p002"] + ["--feature-image", "https://example.com/image.png"],
            COMMANDS["p002"] + ["--suspected", "gun part"],
            ["p004", ""], ["p005", " "], ["p006", "0"],
            ["p007", "--page", "0"], ["p007", "--per-page", "-1"],
        ]
        for command, limit in (("d001", 500), ("i001", 500), ("l001", 100), ("c001", 200)):
            invalid.extend(COMMANDS[command] + ["--top", value] for value in ("0", str(limit + 1), "many"))
        for argv in invalid:
            with self.subTest(argv=argv[:3]):
                code, output, error, api = invoke(argv, token="")
                self.assertEqual(code, 2, error)
                self.assertEqual(output, "")
                self.assertNotIn("未设置 ERIC_API_TOKEN", error)
                api.assert_not_called()

    def test_exact_boundaries_are_accepted(self):
        for command, field, limit in (("t001", "title", 300), ("t001", "text", 5000),
                                      ("i001", "title", 500), ("i001", "description", 30000),
                                      ("p002", "description", 5000)):
            code, _, error, _ = invoke(COMMANDS[command] + ["--" + field, "x" * limit, "--dry-run"])
            self.assertEqual(code, 0, error)
        for command, limit in (("d001", 500), ("i001", 500), ("l001", 100), ("c001", 200)):
            for value in (1, limit):
                code, _, error, _ = invoke(COMMANDS[command] + ["--top", str(value), "--dry-run"])
                self.assertEqual(code, 0, error)

    def test_current_regions_and_case_normalization(self):
        for command, region in (("t001", "CN"), ("l001", "EU"), ("l001", "EM")):
            code, output, error, _ = invoke(COMMANDS[command] + ["--regions", region.lower(), "--dry-run"])
            self.assertEqual(code, 0, error)
            self.assertEqual(json.loads(output)["payload"]["regions"], [region])
        for option, value in (("--sites", "UK"), ("--platform-sites", '{"amazon":["UK"]}')):
            code, output, error, _ = invoke(COMMANDS["p002"] + [option, value, "--dry-run"])
            self.assertEqual(code, 0, error)
            self.assertEqual(json.loads(output)["payload"]["platform_sites"], {"amazon": ["uk"]})

    def test_image_sources_and_offline_url_rejection(self):
        for image in ("missing-image.jpg", "", "A" * 64 + "!", "https://example.com/product.png"):
            code, _, error, api = invoke(["p001", image, "--dry-run"])
            self.assertEqual(code, 1, error)
            api.assert_not_called()
        encoded = base64.b64encode(Path(IMAGE).read_bytes()).decode()
        code, output, error, _ = invoke(["p001", encoded, "--dry-run"])
        self.assertEqual(code, 0, error)
        self.assertEqual(json.loads(output)["payload"]["base64_image"], encoded)

    def test_missing_token_has_powershell_recovery_and_empty_stdout(self):
        code, output, error, api = invoke(COMMANDS["t001"], token="")
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn('$env:ERIC_API_TOKEN = "your-api-token"', error)
        api.assert_not_called()

    def test_missing_requests_does_not_try_installing_packages(self):
        original_import = builtins.__import__
        def without_requests(name, *args, **kwargs):
            if name == "requests":
                raise ImportError("requests unavailable")
            return original_import(name, *args, **kwargs)
        with mock.patch("builtins.__import__", side_effect=without_requests), mock.patch("subprocess.run") as run:
            with self.assertRaises(detect.CLIError) as caught:
                detect.ensure_requests()
            self.assertIn("uv run --with requests", str(caught.exception))
            self.assertIn("requirements.txt", str(caught.exception))
            run.assert_not_called()


class ResponseContractTests(unittest.TestCase):
    def test_copyright_numeric_string_null_and_unknown_radar(self):
        for value, high in ((1, True), ("1", True), ("high_risk", True),
                            (0, False), ("0", False), ("low_risk", False), (None, False), ("unknown", False)):
            with self.subTest(radar=value):
                response = {"success": True, "data": {"radar_result": value, "list": [
                    {"similarity": 0.2, "copyright_code": "TEST-001", "sub_radar_result": value}
                ]}}
                code, output, error, _ = invoke(COMMANDS["c001"], response)
                self.assertEqual(code, 0, error)
                self.assertEqual("1. 🔴高风险" in output, high)
                self.assertEqual("整体雷达风险: 🔴高风险" in output, high)
                self.assertIn("TEST-001", output)
        response["data"]["list"][0]["sub_radar_result"] = 1
        code, output, _, _ = invoke(COMMANDS["c001"] + ["--no-radar"], response)
        self.assertEqual(code, 0)
        self.assertNotIn("🔴高风险", output)

    def test_copyright_fixture_uses_current_schema(self):
        code, output, error, api = invoke(COMMANDS["c001"] + ["--mock-response", str(FIXTURES / "c001-radar.json")])
        self.assertEqual(code, 0, error)
        self.assertIn("1. 🔴高风险", output)
        self.assertIn("2. 🟢低风险", output)
        self.assertIn("未分析/未知", output)
        api.assert_not_called()

    def test_null_design_radar_regression(self):
        code, output, error, _ = invoke(COMMANDS["d001"], {"success": True, "data": {"list": [{"similarity": "0.2", "radar_result": None}]}})
        self.assertEqual(code, 0, error)
        self.assertIn("低风险", output)

    def test_api_transport_auth_and_http_error_envelope(self):
        requests = mock.Mock()
        requests.RequestException = RuntimeError
        requests.post.return_value.json.return_value = SUCCESS
        with mock.patch.object(detect, "ensure_requests", return_value=requests):
            result = detect.api_call("secret", PATHS["t001"], {"product_title": "Lamp"}, 90)
        self.assertEqual(result, SUCCESS)
        self.assertEqual(requests.post.call_args.kwargs["headers"], {"Token": "secret", "Content-Type": "application/json"})
        self.assertEqual(requests.post.call_args.kwargs["timeout"], 90)
        requests.post.return_value.json.return_value = FAILURE
        requests.post.return_value.raise_for_status.side_effect = RuntimeError("HTTP 400")
        with mock.patch.object(detect, "ensure_requests", return_value=requests):
            self.assertEqual(detect.api_call("secret", PATHS["t001"], {}), FAILURE)

    def test_transport_failures_are_actionable_and_never_retried(self):
        requests = mock.Mock()
        requests.RequestException = RuntimeError
        for error in (RuntimeError("timeout"), ValueError("invalid JSON")):
            requests.post.reset_mock()
            requests.post.side_effect = error
            with mock.patch.object(detect, "ensure_requests", return_value=requests):
                with self.assertRaises(detect.CLIError) as caught:
                    detect.api_call("secret", PATHS["t001"], {})
            self.assertIn("未自动重试", str(caught.exception))
            self.assertIn("扣点未确认", str(caught.exception))
            requests.post.assert_called_once()

    def test_region_documentation_matches_shared_cli_contract(self):
        docs = {"d001": "design-patent.md", "i001": "invention-patent.md",
                "l001": "logo-detection.md", "t001": "trademark-detection.md"}
        for command, filename in docs.items():
            text = (ROOT / "references" / filename).read_text(encoding="utf-8")
            row = next(line for line in text.splitlines() if line.startswith("| `regions`"))
            self.assertEqual(set(re.findall(r"\b[A-Z]{2}\b", row)), set(detect.SUPPORTED_REGIONS[command]))
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for command, heading in (("t001", "## T001"), ("l001", "## L001")):
            section = skill.split(heading, 1)[1].split("\n## ", 1)[0]
            row = next(line for line in section.splitlines() if "**支持地区**" in line)
            self.assertEqual(set(re.findall(r"\b[A-Z]{2}\b", row)), set(detect.SUPPORTED_REGIONS[command]))

    def test_readme_p002_examples_parse_without_api_access(self):
        import shlex
        readme = (ROOT / "README.md").read_text(encoding="utf-8").replace("\\\n", "")
        examples = [line for line in readme.splitlines() if line.startswith("python3 scripts/detect.py p002 ")]
        self.assertGreaterEqual(len(examples), 2)
        for line in examples:
            code, _, error, api = invoke(shlex.split(line)[2:] + ["--dry-run"])
            self.assertEqual(code, 0, error)
            api.assert_not_called()

    def test_cli_offline_modes_do_not_require_site_packages(self):
        env = {**os.environ, "ERIC_API_TOKEN": "", "PYTHONIOENCODING": "utf-8"}
        for mode in (["--dry-run"], ["--mock-response", str(FIXTURES / "p001-no-match.json"), "--json"]):
            result = subprocess.run([sys.executable, "-S", str(ROOT / "scripts" / "detect.py"), "p001", IMAGE] + mode,
                                    capture_output=True, text=True, encoding="utf-8", env=env, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            json.loads(result.stdout)


if __name__ == "__main__":
    unittest.main()
