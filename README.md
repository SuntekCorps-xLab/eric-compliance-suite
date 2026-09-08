# ERiC Compliance Suite

[![License: MIT](https://img.shields.io/badge/License-MIT-5b5cf6.svg)](LICENSE)
[![Python 3](https://img.shields.io/badge/Python-3.8%2B-3776ab.svg)](https://www.python.org/)
[![Powered by ERiC](https://img.shields.io/badge/Powered%20by-ERiC-5b5cf6.svg)](https://eric-bot.com)

[English](#english) | [简体中文](#简体中文)

## English

**ERiC Compliance Suite** is an all-in-one Agent Skill powered by the [ERiC](https://eric-bot.com) API. It brings patent, trademark, copyright, and marketplace policy screening into AI agent workflows. A single skill provides 12 commands and can also be used directly through the included Python CLI.

### Capabilities

| Capability | API | Input | Purpose |
| --- | --- | --- | --- |
| Design patent screening | D001 | Image | Find similar design patents and identify similarity, TRO, and radar risks |
| Utility patent screening | I001 | Title and description | Find similar US utility patents |
| Graphic trademark screening | L001 | Image | Locate logos and find similar graphic trademarks |
| Text trademark screening | T001 | Title and description | Identify trademark risks in product copy |
| Safer wording suggestions | T002 | Text and trademark term | Suggest alternatives for risky trademark terms |
| Copyright screening | C001 | Image | Find similar copyrighted artwork and rights-holder risks |
| Policy image screening | P001 | Image | Find images similar to gun parts, the category currently supported by this command |
| Policy text screening | P002 | Title and description | Check marketplace prohibited- and restricted-product policies |
| Custom risk terms | P004–P007 | Text | Suggest, save, delete, and list custom risk terms |

See [`references/`](references/) for bundled API reference material. Some reference files may lag the production API; direct API integrations should validate parameters, fields, and pricing against the [official ERiC API documentation](https://open.eric-bot.com/docs). The behavior of this repository's bundled skill and CLI is defined by [`SKILL.md`](SKILL.md) and [`scripts/detect.py`](scripts/detect.py).

### Prerequisites

Use Python 3.8+ (a maintained Python 3.12+ installation is recommended) and Git. If Python is not installed on Windows, use the [official Python installer](https://www.python.org/downloads/windows/) or run this in PowerShell:

```powershell
winget install --exact --id Python.Python.3.12
```

Open a **new terminal**, then run `py --version` and `py -c "import sys; print(sys.executable)"`. If `python` or `python3` opens Microsoft Store or exits without running the script, use `py` and check Windows **Manage app execution aliases** and PATH; see [Python's Windows troubleshooting guide](https://docs.python.org/3/using/windows.html#troubleshooting).

On macOS/Linux, check `python3 --version`; install Python from [python.org](https://www.python.org/downloads/) or your OS package manager if needed. Older macOS system Python builds using LibreSSL may emit [urllib3's `NotOpenSSLWarning`](https://urllib3.readthedocs.io/en/stable/v2-migration-guide.html); use a maintained Python build linked to OpenSSL instead of suppressing the warning.

### Quick start

#### 1. Get an API token

Get an API token from [ERiC](https://eric-bot.com), or follow the “睿观AI” WeChat official account and send `睿观Skill`. Then set it as an environment variable:

Bash / zsh:

```bash
export ERIC_API_TOKEN="your-api-token"
```

Windows PowerShell:

```powershell
$env:ERIC_API_TOKEN = "your-api-token"
```

To persist it for future terminals, run `setx ERIC_API_TOKEN "your-api-token"` in PowerShell, then open a new terminal. `setx` does not update the current session. Verify presence without printing the token: `Test-Path Env:ERIC_API_TOKEN`.

Never hard-code the token, commit it to Git, or paste it into a public agent conversation.

#### 2. Install as an Agent Skill

Clone the repository into your agent's skills directory.

Claude Code:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/SuntekCorps-xLab/eric-compliance-suite.git \
  ~/.claude/skills/eric-compliance-suite
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
git clone https://github.com/SuntekCorps-xLab/eric-compliance-suite.git "$HOME\.claude\skills\eric-compliance-suite"
```

Codex:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/SuntekCorps-xLab/eric-compliance-suite.git \
  ~/.codex/skills/eric-compliance-suite
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.codex\skills" | Out-Null
git clone https://github.com/SuntekCorps-xLab/eric-compliance-suite.git "$HOME\.codex\skills\eric-compliance-suite"
```

For other tools that support Agent Skills or Markdown-based instructions, import the whole repository or use [`SKILL.md`](SKILL.md) as system instructions. The agent must also have filesystem access, command or code execution, and outbound HTTPS access; importing the instructions alone does not provide a runtime.

Run CLI commands from the cloned repository root. If the agent does not discover the new skill immediately, restart the agent session or follow the platform's skill reload procedure.

After installation, ask the agent in natural language:

```text
Check this product image for design patent risks in the United States.
Screen this product title for trademark risks and suggest safer wording.
Check whether this product description violates Amazon US marketplace policies.
```

The agent selects the appropriate ERiC API and shows the estimated point cost before running a check.

#### 3. Use the CLI directly

The CLI requires Python 3.8+ and `requests`:

```bash
cd /path/to/eric-compliance-suite
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/detect.py --help
```

Windows PowerShell (no activation script required):

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/detect.py --help
```

For [uv](https://docs.astral.sh/uv/guides/scripts/) environments, use `uv run --with requests scripts/detect.py --help`, or install the manifest with `uv pip install -r requirements.txt` in your virtual environment. The CLI does not install packages automatically. Help, dry runs and local mocks need only the Python standard library.

In the examples below, replace `python3` with `.venv/bin/python`, `.\.venv\Scripts\python.exe`, or `uv run --with requests` as appropriate. PowerShell examples should be entered on one line; Bash's `\` line continuation does not apply.

The available subcommands are `d001`, `i001`, `l001`, `t001`, `t002`, `c001`, `p001`, `p002`, `p004`, `p005`, `p006`, and `p007`.

Examples:

```bash
# D001: design patent screening; accepts a local path, URL, or base64 image
python3 scripts/detect.py d001 product.jpg --regions US --top 50

# I001: utility patent screening
python3 scripts/detect.py i001 \
  --title "Portable folding lamp" \
  --description "A rechargeable lamp with a foldable arm"

# L001: graphic trademark screening
python3 scripts/detect.py l001 product.jpg --regions US GB --top 20

# T001 + T002: text trademark screening with safer wording suggestions
python3 scripts/detect.py t001 \
  --title "Wireless game controller" \
  --text "Product description" \
  --regions US \
  --auto-safe-words

# C001: copyright screening
python3 scripts/detect.py c001 artwork.jpg --top 100

# P001: policy image screening
python3 scripts/detect.py p001 product.jpg

# P002: Amazon US and UK policy text screening
python3 scripts/detect.py p002 \
  --title "Product title" \
  --description "Product description" \
  --sites us uk
```

`--sites` selects Amazon sites only. For TikTok Singapore, use `--platform-sites` instead:

```bash
python3 scripts/detect.py p002 --title "Wireless earbuds with charging case" \
  --platform-sites '{"tiktok":["sg"]}' --dry-run
```

TikTok SG has been [verified against the live API](reports/2026-09-07-issue-17-verification.md). Other platforms do not inherit Amazon's site list; the CLI validates their input structure and the API decides support. A successful dry run does not verify server support. See [the policy reference](references/policy-detection.md).

Every subcommand supports `--json` for the complete API response on stdout; progress and point estimates go to stderr. Failed API responses exit nonzero. `t001 --json` returns only the T001 response and does not run `--auto-safe-words` follow-ups. To view all options for a command:

```bash
python3 scripts/detect.py d001 --help
```

### Try it without spending points

All 12 commands support `--dry-run` and `--mock-response`. Neither mode needs a token or makes network requests. Use a local image or base64; image URLs are rejected in offline mode. The bundled image and responses are synthetic test data.

```bash
python3 scripts/detect.py d001 tests/fixtures/sample.png --regions US --top 50 --dry-run
python3 scripts/detect.py c001 tests/fixtures/sample.png --mock-response tests/fixtures/c001-radar.json
python3 scripts/detect.py p001 tests/fixtures/sample.png --mock-response tests/fixtures/p001-no-match.json --json
```

A dry run validates inputs and prints JSON containing the target URL, request payload (including encoded images), redacted authentication header, estimated live cost and `points_consumed: 0`. A mock exercises the normal response renderer. These modes verify local wiring; they do not verify token validity or server-side acceptance. See [the offline integration contract](references/offline-testing.md) for expected JSON, mock failures and regression checks.

Targeted live checks, actual point deductions, and the boundary between live and offline coverage are recorded in the [2026-09-05 verification report](reports/2026-09-05-live-verification.md).

### Point usage

ERiC API calls may consume points from your account. The CLI prints locally calculated estimates before and after a check; it does not query the account ledger. The final debit shown by the ERiC platform is authoritative.

| Check | Base cost | With radar | Notes |
| --- | ---: | ---: | --- |
| D001 design patent | 10 | 15 | Radar is enabled by default |
| I001 utility patent | 10 standard | — | Promotional pricing may apply; currently supports US only |
| L001 graphic trademark | 10 | 15 | Radar is enabled by default |
| T001 text trademark | 1 | — | T002 calls are charged separately |
| T002 safer wording | 1 | — | One call per trademark term |
| C001 copyright | 1 | 2 | Radar is enabled by default |
| P001 policy image | 1 | — | Currently screens gun-parts imagery |
| P002 policy text | 5 + 2 per custom term | — | 5 base points plus 2 for each enabled custom term |
| P004–P007 custom risk terms | 0 | — | Management operations; P004 has a separate daily limit of 50 calls |

P002 feature detection requires both `--feature-word-ids` (ready saved terms) and a nonempty `--feature-image` URL together with `--enable-feature`.

P004–P007 had zero observed point cost in the [2026-09-04 integration checks](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/13). This is separate from P002 feature detection, which costs 2 points per selected term. Failed requests and timeouts do not confirm a debit; the CLI does not retry automatically.

D001, L001, and C001 enable radar analysis by default **in the bundled CLI and Agent Skill**. Raw API defaults may differ, and direct API callers must set `enable_radar` explicitly. Use `--no-radar` to disable radar in the CLI. With `t001 --auto-safe-words`, the estimate is 1 point for T001 plus 1 point for each T002 call made for a high-risk term. Pricing may change; the ERiC platform is the source of truth.

### Supported input

The bundled CLI accepts the following inputs for D001, L001, C001, and P001, then converts the image to the base64 format required by the raw API:

- A local image path
- An `http://` or `https://` image URL
- A base64-encoded image string

Images must have a supported PNG/JPEG/GIF/WebP/BMP header and be at most 20 MiB. This is a header check, not a full image decoder. URL downloads require a public HTTP(S) image endpoint; redirects and nonpublic destinations are rejected. Downloads connect directly to the validated address, use no proxy environment settings, and send no ERiC credentials. For `--dry-run` / `--mock-response`, use a local file such as `tests/fixtures/sample.png`; these modes never download URLs. See [offline examples](references/offline-testing.md).

Put positional images before multi-value flags (`d001 image.png --regions US GB`), or use `--` before the image. Installed agents must resolve the script relative to the loaded Skill directory, or call it by absolute path.

A chat attachment is usable only if the agent runtime exposes a readable local file. Seeing the image in chat alone does not provide bytes for the CLI. If no file is available, save the image locally and provide its path, or share a public image URL; URL download is already supported for live calls.

Text commands accept product titles, descriptions, and the relevant market or site options. I001 currently supports the United States only. See the corresponding reference document for the market coverage of other APIs.

### Project structure

```text
eric-compliance-suite/
├── SKILL.md                         # Agent instructions, routing, and API summary
├── scripts/
│   ├── detect.py                    # Unified CLI with 12 subcommands
│   └── image_inputs.py              # Image validation and bounded public downloads
├── LICENSE                         # MIT license
├── reports/                        # Reviewed verification summaries and replies
├── .github/                        # CI workflows and maintainer-only scripts
├── requirements.txt                # Live HTTP dependency
├── tests/                          # Offline regression tests and fixtures
└── references/
    ├── design-patent.md             # D001
    ├── invention-patent.md          # I001
    ├── logo-detection.md            # L001
    ├── trademark-detection.md       # T001 / T002
    ├── copyright-detection.md       # C001
    ├── policy-detection.md          # P001 / P002 / P004–P007
    └── offline-testing.md           # Dry-run / mock integration
```

### Security and responsible use

- Product images and text are sent to the ERiC API for screening. Make sure you are authorized to process and upload the data.
- Do not load base64 images or large API responses directly into an agent context. This skill instructs the agent to process them in the code execution environment.
- Retry timed-out requests carefully because a completed server-side request may already have consumed points.
- Confirm the applicable ERiC privacy and data-processing terms before submitting confidential, regulated, or personal data; retention, residency, and deletion terms are not defined in this repository.
- Coverage and update frequency vary by data source. A low-risk result is not permission to use protected material and does not guarantee marketplace approval.
- Results are provided for risk-screening assistance and are not legal advice. Qualified professionals should review material findings.

### Resources

- [ERiC website](https://eric-bot.com)
- [ERiC API documentation](https://open.eric-bot.com/docs)
- [Complete skill instructions](SKILL.md)
- [API references](references/)

### License

[MIT](LICENSE)

---

## 简体中文

**ERiC Compliance Suite** 是基于 [睿观（ERiC）](https://eric-bot.com) API 构建的一站式 Agent Skill，将专利、商标、版权和电商平台政策检测接入 AI Agent 工作流。一个 Skill 即可使用 12 个命令，也可以通过随附的 Python CLI 独立调用。

### 功能

| 能力 | API | 输入 | 用途 |
| --- | --- | --- | --- |
| 外观专利检测 | D001 | 图片 | 搜索相似外观专利并识别高相似度、TRO 与雷达风险 |
| 发明专利检测 | I001 | 标题、描述 | 搜索相似美国发明专利 |
| 图形商标检测 | L001 | 图片 | 定位 Logo 并搜索相似图形商标 |
| 文本商标检测 | T001 | 标题、描述 | 识别商品文案中的商标风险 |
| 商标替换词 | T002 | 文本、商标词 | 为风险商标词生成替换建议 |
| 版权检测 | C001 | 图片 | 搜索相似版权画作并识别权利人风险 |
| 政策图片检测 | P001 | 图片 | 搜索与枪械配件相似的图片，这是当前命令支持的检测类别 |
| 政策文本检测 | P002 | 标题、描述 | 检查电商平台禁售与限售政策 |
| 风险特征词管理 | P004–P007 | 文本 | 联想、保存、删除和查询自定义风险特征词 |

仓库内的 API 参考资料位于 [`references/`](references/)。部分参考文件可能滞后于生产 API；直接集成 API 时，应以 [ERiC 官方 API 文档](https://open.eric-bot.com/docs)核对参数、字段和计费。当前仓库随附 Skill 与 CLI 的行为分别以 [`SKILL.md`](SKILL.md) 和 [`scripts/detect.py`](scripts/detect.py) 为准。

### 环境准备

需要 Python 3.8+（推荐使用仍在维护的 Python 3.12+）及 Git。Windows 尚未安装 Python 时，可使用 [Python 官方安装程序](https://www.python.org/downloads/windows/)，或在 PowerShell 中运行：

```powershell
winget install --exact --id Python.Python.3.12
```

安装后打开**新终端**，运行 `py --version` 和 `py -c "import sys; print(sys.executable)"`。若 `python` / `python3` 跳转 Microsoft Store 或未执行脚本就退出，先改用 `py`，并检查 Windows“管理应用执行别名”和 PATH；参见 [Python 官方 Windows 排障文档](https://docs.python.org/3/using/windows.html#troubleshooting)。

macOS/Linux 先检查 `python3 --version`，缺少 Python 时从 [python.org](https://www.python.org/downloads/) 或系统包管理器安装。旧版 macOS 系统 Python 使用 LibreSSL 时可能出现 [urllib3 的 `NotOpenSSLWarning`](https://urllib3.readthedocs.io/en/stable/v2-migration-guide.html)；请换用仍在维护且使用 OpenSSL 的 Python。

### 快速开始

#### 1. 获取 API Token

登录 [ERiC](https://eric-bot.com) 获取 API Token，或关注微信公众号“睿观AI”并发送“睿观Skill”。然后设置环境变量：

Bash / zsh：

```bash
export ERIC_API_TOKEN="your-api-token"
```

Windows PowerShell（当前会话立即生效）：

```powershell
$env:ERIC_API_TOKEN = "your-api-token"
```

如需持久保存，在 PowerShell 中运行 `setx ERIC_API_TOKEN "your-api-token"` 后打开新终端；`setx` 不会更新当前会话。使用 `Test-Path Env:ERIC_API_TOKEN` 检查是否已设置，无需输出 Token。

请勿把 Token 写入代码、提交到 Git，或粘贴到公开的 Agent 对话中。

#### 2. 安装为 Agent Skill

将仓库克隆到 Agent 的 Skills 目录。

Claude Code：

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/SuntekCorps-xLab/eric-compliance-suite.git \
  ~/.claude/skills/eric-compliance-suite
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
git clone https://github.com/SuntekCorps-xLab/eric-compliance-suite.git "$HOME\.claude\skills\eric-compliance-suite"
```

Codex：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/SuntekCorps-xLab/eric-compliance-suite.git \
  ~/.codex/skills/eric-compliance-suite
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.codex\skills" | Out-Null
git clone https://github.com/SuntekCorps-xLab/eric-compliance-suite.git "$HOME\.codex\skills\eric-compliance-suite"
```

其他支持 Agent Skills 或 Markdown 指令的工具，可以导入整个仓库，或将 [`SKILL.md`](SKILL.md) 作为系统指令使用。Agent 还必须具备文件访问、命令或代码执行以及出站 HTTPS 访问能力；仅导入指令不会自动提供运行环境。

CLI 命令需要在克隆后的仓库根目录中执行。如果 Agent 没有立即发现新 Skill，请重新启动 Agent 会话，或按照所用平台的方式重新加载 Skills。

安装后，可以直接使用自然语言发起任务：

```text
检查这张产品图是否存在外观专利风险，市场选择美国。
检测这个商品标题里的商标风险，并为高风险词提供替换建议。
检查这段商品描述是否违反 Amazon US 的销售政策。
```

Agent 会根据任务选择对应的 ERiC API，并在调用前提示预计扣点。

#### 3. 直接使用 CLI

CLI 需要 Python 3.8+ 和 `requests`：

```bash
cd /path/to/eric-compliance-suite
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/detect.py --help
```

Windows PowerShell（无需运行激活脚本）：

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/detect.py --help
```

[uv](https://docs.astral.sh/uv/guides/scripts/) 环境可使用 `uv run --with requests scripts/detect.py --help`，也可在虚拟环境中执行 `uv pip install -r requirements.txt`。CLI 不会自动安装依赖；帮助、试运行及本地模拟仅需 Python 标准库。

下方示例的 `python3` 请按环境替换为 `.venv/bin/python`、`.\.venv\Scripts\python.exe` 或 `uv run --with requests`。PowerShell 请将示例输入为一行，不能使用 Bash 的 `\` 续行。

可用子命令包括 `d001`、`i001`、`l001`、`t001`、`t002`、`c001`、`p001`、`p002`、`p004`、`p005`、`p006` 和 `p007`。

常用示例：

```bash
# D001：外观专利检测；图片支持本地路径、URL 或 base64
python3 scripts/detect.py d001 product.jpg --regions US --top 50

# I001：发明专利检测
python3 scripts/detect.py i001 \
  --title "Portable folding lamp" \
  --description "A rechargeable lamp with a foldable arm"

# L001：图形商标检测
python3 scripts/detect.py l001 product.jpg --regions US GB --top 20

# T001 + T002：文本商标检测并获取高风险词替换建议
python3 scripts/detect.py t001 \
  --title "Wireless game controller" \
  --text "Product description" \
  --regions US \
  --auto-safe-words

# C001：版权检测
python3 scripts/detect.py c001 artwork.jpg --top 100

# P001：政策图片检测
python3 scripts/detect.py p001 product.jpg

# P002：Amazon US 和 UK 政策文本检测
python3 scripts/detect.py p002 \
  --title "Product title" \
  --description "Product description" \
  --sites us uk
```

`--sites` 仅选择 Amazon 站点。检测 TikTok 新加坡站请改用 `--platform-sites`：

```bash
python3 scripts/detect.py p002 --title "Wireless earbuds with charging case" \
  --platform-sites '{"tiktok":["sg"]}' --dry-run
```

TikTok SG 已通过[真实 API 验证](reports/2026-09-07-issue-17-verification.md)。其他平台不套用 Amazon 站点列表；CLI 校验输入结构，由 API 决定是否支持。试运行成功不代表服务端支持，详见[政策参考](references/policy-detection.md)。

所有子命令都支持 `--json`，标准输出仅含完整 API 响应，进度和扣点估值写入标准错误；API 失败时退出码非零。`t001 --json` 仅输出 T001 响应，不执行 `--auto-safe-words` 后续调用。运行以下命令查看某个接口的全部参数：

```bash
python3 scripts/detect.py d001 --help
```

### 零扣点试用

全部 12 个子命令均支持 `--dry-run` 和 `--mock-response`，无需 Token、不发起网络请求。图片请使用本地路径或 base64；离线模式拒绝下载图片 URL。附带图片和响应均为合成测试数据。

```bash
python3 scripts/detect.py d001 tests/fixtures/sample.png --regions US --top 50 --dry-run
python3 scripts/detect.py c001 tests/fixtures/sample.png --mock-response tests/fixtures/c001-radar.json
python3 scripts/detect.py p001 tests/fixtures/sample.png --mock-response tests/fixtures/p001-no-match.json --json
```

试运行会校验参数，并以 JSON 输出目标 URL、请求体（含图片编码）、脱敏认证头、真实调用时的预估点数及 `points_consumed: 0`。模拟模式使用正常结果展示逻辑。这些模式验证本地接入流程，不验证 Token 有效性或服务端是否接受请求。预期 JSON、模拟错误及回归检查见[离线接入说明](references/offline-testing.md)。

针对性实测、实际扣点和实测/离线覆盖边界见 [2026-09-05 验证报告](reports/2026-09-05-live-verification.md)。

### 扣点说明

ERiC API 调用可能消耗账户点数。CLI 会在检测前后显示本地计算的扣点估值，但不会查询账户点数流水；最终应以 ERiC 平台显示的实际扣点为准。

| 检测 | 基础扣点 | 开启雷达 | 备注 |
| --- | ---: | ---: | --- |
| D001 外观专利 | 10 | 15 | 默认开启雷达 |
| I001 发明专利 | 常规 10 | — | 可能有活动价格；当前仅支持 US |
| L001 图形商标 | 10 | 15 | 默认开启雷达 |
| T001 文本商标 | 1 | — | T002 调用单独计费 |
| T002 商标替换词 | 1 | — | 每个商标词调用一次 |
| C001 版权 | 1 | 2 | 默认开启雷达 |
| P001 政策图片 | 1 | — | 当前检测枪械配件图片 |
| P002 政策文本 | 5 + 每个特征词 2 点 | — | 5 点基础费用 + 每个启用特征词 2 点 |
| P004–P007 风险特征词 | 0 | — | 管理操作；P004 另有每日 50 次调用限制 |

P002 开启 `--enable-feature` 时，必须同时传入 `--feature-word-ids`（已就绪的特征词）及非空 `--feature-image` 图片 URL。

P004–P007 的 0 点规则依据 [2026-09-04 接入验证](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/13)；P002 执行特征词检测才按每个选中词额外收取 2 点。请求失败或超时不能确认是否扣费，CLI 不自动重试。

D001、L001 和 C001 在**随附的 CLI 与 Agent Skill 中**默认启用雷达分析。原始 API 的默认值可能不同，直接调用 API 时应显式设置 `enable_radar`；在 CLI 中可使用 `--no-radar` 关闭。使用 `t001 --auto-safe-words` 时，估值为 T001 的 1 点，加上每个高风险词触发一次 T002 所需的 1 点。计费规则可能随服务调整，请以 ERiC 平台显示为准。

### 支持的输入

随附的 CLI 为 D001、L001、C001 和 P001 接受以下输入，并将图片转换为原始 API 所需的 base64 格式：

- 本地图片路径
- `http://` 或 `https://` 图片 URL
- base64 图片字符串

图片需具有 PNG/JPEG/GIF/WebP/BMP 文件头，大小不超过 20 MiB；文件头检查不等同于完整图片解码。URL 下载仅允许公网 HTTP(S) 图片直链，拒绝重定向及非公网目标，直接连接已校验的地址，不使用代理环境变量、不携带 ERiC 凭据。`--dry-run` / `--mock-response` 请使用 `tests/fixtures/sample.png` 等本地文件；离线模式始终不下载 URL，见[离线示例](references/offline-testing.md)。

图片位置参数放在多值选项之前，例如 `d001 image.png --regions US GB`，或用 `--` 分隔。安装后的 Agent 应按已加载 Skill 的目录解析脚本路径，或使用绝对路径。

聊天附件只有在 Agent 运行环境提供可读取的本地文件时才能使用；仅在聊天中看见图片，不代表 CLI 能读取图片字节。若没有文件，请先保存图片并提供本地路径，或提供公开图片 URL；真实调用已支持 URL 下载。

文本接口接受产品标题、描述以及相应的市场或站点参数。I001 当前仅支持美国；其他接口的地区范围请查看对应参考文档。

### 项目结构

```text
eric-compliance-suite/
├── SKILL.md                         # Agent 指令、路由规则与接口摘要
├── scripts/
│   ├── detect.py                    # 12 个子命令的统一 CLI 入口
│   └── image_inputs.py              # 图片校验与受限公网下载
├── LICENSE                         # MIT 许可证
├── reports/                        # 审核后的验证摘要与 issue 回复
├── .github/                        # CI 工作流和维护者专用脚本
├── requirements.txt                # 真实 API 调用依赖
├── tests/                          # 本地回归测试与样例
└── references/
    ├── design-patent.md             # D001
    ├── invention-patent.md          # I001
    ├── logo-detection.md            # L001
    ├── trademark-detection.md       # T001 / T002
    ├── copyright-detection.md       # C001
    ├── policy-detection.md          # P001 / P002 / P004–P007
    └── offline-testing.md           # 试运行与模拟接入
```

### 安全与使用须知

- 产品图片和文本会发送至 ERiC API 完成检测，请确保你有权处理和上传这些数据。
- 不要将 base64 图片或大型 API 响应直接加载到 Agent 上下文；本 Skill 已要求 Agent 在代码执行环境中处理这些内容。
- 调用超时后谨慎重试：服务端已完成的请求可能已经产生点数消耗。
- 提交机密、受监管或个人数据前，请确认适用的 ERiC 隐私和数据处理条款；本仓库未定义数据保留、存储地域及删除机制。
- 数据库覆盖范围和更新频率因数据源而异。低风险结果不代表已获得使用受保护内容的许可，也不保证通过电商平台审核。
- 检测结果用于辅助识别风险，不构成法律意见；重要结果应由合格的专业人员复核。

### 相关资源

- [ERiC 官网](https://eric-bot.com)
- [ERiC API 文档](https://open.eric-bot.com/docs)
- [完整 Skill 指令](SKILL.md)
- [API 参考文档](references/)

### 许可证

[MIT](LICENSE)
