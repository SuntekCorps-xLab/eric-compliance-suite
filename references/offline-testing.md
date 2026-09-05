# Offline integration / 离线接入验证

All 12 commands accept `--dry-run` or `--mock-response FILE` after the subcommand. These modes use only the Python standard library, skip token validation, and make **no network requests**. They consume zero points, including for save/delete commands and automatic T002 follow-ups. The bundled fixtures are synthetic examples, not actual screening findings.

所有 12 个命令都支持在子命令后传 `--dry-run` 或 `--mock-response FILE`。这些模式仅使用 Python 标准库，不校验 Token，不联网、不扣点；包括保存、删除操作及自动 T002 后续调用。附带样例是合成测试数据，并非真实检测结果。

## Validate request construction

From the repository root / 在仓库根目录执行：

```bash
python3 scripts/detect.py d001 tests/fixtures/sample.png --regions US --top 50 --dry-run > request.json
```

Windows PowerShell:

```powershell
py scripts/detect.py d001 tests/fixtures/sample.png --regions US --top 50 --dry-run | Set-Content -Encoding utf8 request.json
```

Expected JSON when no token is configured (the image value below is abbreviated):

```json
{
  "dry_run": true,
  "command": "d001",
  "method": "POST",
  "url": "https://saas.eric-bot.com/v1.0/eric-api/patent/design/v1/detection",
  "headers": {
    "Content-Type": "application/json",
    "Token": "<ERIC_API_TOKEN>"
  },
  "token_configured": false,
  "payload": {
    "product_title": "",
    "product_description": "",
    "regions": ["US"],
    "img_64lis": ["<base64 of tests/fixtures/sample.png>"],
    "top_loc": null,
    "patent_status": [],
    "top_number": 50,
    "enable_tro": true,
    "source_language": "",
    "query_mode": "hybrid",
    "enable_radar": true
  },
  "estimated_points": 15,
  "points_consumed": 0
}
```

`payload` is the same JSON object that a live call would POST. The real preview includes the entire encoded image; keep it in a file rather than loading it into an agent conversation. With a configured token, `token_configured` is `true` and `headers.Token` is always `<redacted>`. No credential value is printed. Only live requests use the actual token in the `Token` header.

`estimated_points` describes the cost of a **live** request. P002 includes 2 points per enabled feature ID. For `t001 --auto-safe-words`, the dry run describes the variable per-term T002 cost under `follow_up`; it cannot know the number of terms before receiving a T001 response.

试运行复用真实请求构造逻辑，实际输出包含完整图片编码；Agent 应在代码环境中提取摘要，不把图片编码读入对话。预估费用是真实调用时的费用，当前试运行费用始终为 0；此模式只检查认证配置是否存在，不证明 Token 有效或服务端接受参数。

Image inputs must be local files or complete base64 strings in offline mode. HTTP(S) image URLs are rejected before downloading; save the image locally first. An image URL in a P002 feature payload is left as text and is never fetched. A chat attachment works only when the runtime exposes a readable file.

## Exercise response parsing

```bash
python3 scripts/detect.py c001 tests/fixtures/sample.png --mock-response tests/fixtures/c001-radar.json
python3 scripts/detect.py p001 tests/fixtures/sample.png --mock-response tests/fixtures/p001-no-match.json --json
python3 scripts/detect.py t001 --title "Example product" --mock-response tests/fixtures/api-error.json --json
```

PowerShell can use the same one-line commands with `py` in place of `python3`. The last command deliberately exits with code 1.

A mock file contains one API response object, or a nonempty array of response objects consumed in call order. Every response must contain a boolean `success`. To test `t001 --auto-safe-words`, supply the T001 response followed by a T002 response for each high-risk term. Missing responses produce an error; the CLI never falls back to the network. `--dry-run` and `--mock-response` are mutually exclusive.

Representative response / 响应示例：

```json
{
  "success": true,
  "code": 200,
  "data": {
    "radar_result": 1,
    "list": [
      {
        "similarity": 0.25,
        "copyright_code": "OFFLINE-001",
        "rights_owner": "Example rights holder",
        "sub_radar_result": 1
      }
    ]
  }
}
```

C001 displays high risk for the item above even though similarity is only 0.25, because its radar result is positive. The [full fixture](../tests/fixtures/c001-radar.json) also covers `0` and `null`. [P001's fixture](../tests/fixtures/p001-no-match.json) covers a successful response containing only an informational string.

模拟模式使用正常结果解析逻辑，并在标准错误明确提示“模拟，消耗 0 点”。响应数组用完会报错，不会改为真实调用；数组可用于测试自动 T002 后续调用。模拟失败响应的退出码为 1。

## Output and exit codes

| Mode/result | stdout | stderr | Exit code |
| --- | --- | --- | ---: |
| Successful dry run | Request preview JSON | Context, if any | 0 |
| Successful `--json` | One complete API response | Progress and estimated cost / mock notice | 0 |
| API `success: false` with `--json` | One complete error response | Failure explanation; live debit is unconfirmed | 1 |
| Missing token/dependency/file, transport error or invalid mock | Empty | Actionable error | 1 |
| Invalid CLI parameter/combination | Empty | Parameter error and usage | 2 |

Human-readable mode writes results to stdout. `t001 --json` preserves the single T001 response and does not run `--auto-safe-words` follow-ups. All billing notices are estimates; no live ledger is queried, and failed or timed-out requests are never described as confirmed debits. There are no automatic retries.

## Run regression checks

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/detect.py
```

Use `py` instead of `python3` on Windows. Tests exercise every command's request payload and JSON lifecycle, parameter boundaries, missing dependency recovery, numeric copyright radar, and P001 no-match billing. HTTP is mocked and offline modes are also exercised without site packages (`python -S`), so these checks need no token and consume no ERiC points.
