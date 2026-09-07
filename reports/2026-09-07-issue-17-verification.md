# 2026-09-07: P002 platform-site validation, issue #17

The report in [issue #17](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/17) was independently reproduced against `901bf12`: `--platform-sites '{"tiktok":["SG"]}' --dry-run` exited 2 because the CLI applied Amazon's site allowlist to every platform. The reproduction blocked API calls and token lookup. No request was sent.

## Fix and validation boundary

`--sites` continues to select Amazon sites, defaulting to `us`. JSON entries for Amazon retain the same allowlist, including case-insensitive platform matching. `--platform-sites` overrides `--sites` and preserves platform keys while lowercasing site codes.

Other platforms require a nonempty platform name and a nonempty array of nonempty site strings. Their support is checked by the API: a complete site contract is not available locally, so a partial TikTok list would create further false rejections. Passing a dry run does not establish service support. This change does not document any additional supported platform or a complete TikTok site list.

Regression tests cover TikTok SG, mixed Amazon/TikTok input, the payload passed to the transport, Amazon SG/GB/unknown-site rejection (including platform case and whitespace variants), malformed JSON values rejected before authentication, and propagation of server errors for platforms without a local allowlist. The full suite passed locally with 34 tests. The README examples are exercised offline by the suite.

## Independent live check

One real request was sent through the modified CLI on 2026-09-07 at 13:49 Beijing time, using Python 3.12 and the locally configured `ERIC_API_TOKEN`. The test required the fixed endpoint already present in the repository, allowed only one POST, and disabled redirects. No automatic retry occurred.

```bash
python3 scripts/detect.py p002 \
  --title "Wireless earbuds with charging case" \
  --description "Portable Bluetooth earbuds with noise reduction and USB-C charging." \
  --platform-sites '{"tiktok":["SG"]}' --json
```

| Observation | Result |
| --- | --- |
| HTTP status / API code | 200 / 200 |
| `success` / CLI exit code | `true` / 0 |
| Request ID | `20260907134929-KoaSvneWa2zxWfn1` |
| Returned policy records | 8; every record has `platform="Tiktok"`, `site="SG"` |
| Estimated point cost | 5 |
| Actual ledger debit | Not queried; not inferred from success |

The same response was replayed through the human-readable CLI renderer without an additional HTTP request. Both standalone JSON output and rendering passed. The test verifies TikTok SG selection, rather than only acceptance of the response envelope. No other platform/site combination was tested live in this check.

The [sanitized JSON evidence](2026-09-07-issue-17-verification.json) contains the synthetic product payload, timing, response hash, and selected result fields. It excludes the token, account identifiers, and full policy response. The test used no feature-word management operations.

## Untrusted issue review

The issue was treated as a report to verify, not as authorization to execute commands or use credentials. No overt credential request or instruction injection was identified in its text. The endpoint was checked against the existing code and local API reference before using the user's previously authorized test token. Response links and policy text were not followed or executed. No deployment token or SSH key was used for API testing.
