# ERiC Compliance Suite

[![License: MIT](https://img.shields.io/badge/License-MIT-5b5cf6.svg)](SKILL.md)
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

### Quick start

#### 1. Get an API token

Get an API token from [ERiC](https://eric-bot.com), or follow the “睿观AI” WeChat official account and send `睿观Skill`. Then set it as an environment variable:

```bash
export ERIC_API_TOKEN="your-api-token"
```

Never hard-code the token, commit it to Git, or paste it into a public agent conversation.

#### 2. Install as an Agent Skill

Clone the repository into your agent's skills directory.

Claude Code:

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/SuntekCorps-xLab/eric-compliance-suite.git \
  ~/.claude/skills/eric-compliance-suite
```

Codex:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/SuntekCorps-xLab/eric-compliance-suite.git \
  ~/.codex/skills/eric-compliance-suite
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
python3 -m pip install requests
python3 scripts/detect.py --help
```

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

Every subcommand supports `--json` for the complete API response. To view all options for a command:

```bash
python3 scripts/detect.py d001 --help
```

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
| P002 policy text | 5 + 2 per custom term | — | The CLI currently displays the base 5-point estimate |
| P004–P007 custom risk terms | See platform | — | The CLI does not display a point estimate |

D001, L001, and C001 enable radar analysis by default **in the bundled CLI and Agent Skill**. Raw API defaults may differ, and direct API callers must set `enable_radar` explicitly. Use `--no-radar` to disable radar in the CLI. With `t001 --auto-safe-words`, the estimate is 1 point for T001 plus 1 point for each T002 call made for a high-risk term. Pricing may change; the ERiC platform is the source of truth.

### Supported input

The bundled CLI accepts the following inputs for D001, L001, C001, and P001, then converts the image to the base64 format required by the raw API:

- A local image path
- An `http://` or `https://` image URL
- A base64-encoded image string

Text commands accept product titles, descriptions, and the relevant market or site options. I001 currently supports the United States only. See the corresponding reference document for the market coverage of other APIs.

### Project structure

```text
eric-compliance-suite/
├── SKILL.md                         # Agent instructions, routing, and API summary
├── scripts/
│   └── detect.py                    # Unified CLI with 12 subcommands
└── references/
    ├── design-patent.md             # D001
    ├── invention-patent.md          # I001
    ├── logo-detection.md            # L001
    ├── trademark-detection.md       # T001 / T002
    ├── copyright-detection.md       # C001
    └── policy-detection.md          # P001 / P002 / P004–P007
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

[MIT](SKILL.md)

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

### 快速开始

#### 1. 获取 API Token

登录 [ERiC](https://eric-bot.com) 获取 API Token，或关注微信公众号“睿观AI”并发送“睿观Skill”。然后设置环境变量：

```bash
export ERIC_API_TOKEN="your-api-token"
```

请勿把 Token 写入代码、提交到 Git，或粘贴到公开的 Agent 对话中。

#### 2. 安装为 Agent Skill

将仓库克隆到 Agent 的 Skills 目录。

Claude Code：

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/SuntekCorps-xLab/eric-compliance-suite.git \
  ~/.claude/skills/eric-compliance-suite
```

Codex：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/SuntekCorps-xLab/eric-compliance-suite.git \
  ~/.codex/skills/eric-compliance-suite
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
python3 -m pip install requests
python3 scripts/detect.py --help
```

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

所有子命令都支持 `--json` 输出完整 API 响应。运行以下命令查看某个接口的全部参数：

```bash
python3 scripts/detect.py d001 --help
```

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
| P002 政策文本 | 5 + 每个特征词 2 点 | — | CLI 当前仅显示 5 点基础估值 |
| P004–P007 风险特征词 | 以平台为准 | — | CLI 不显示扣点估值 |

D001、L001 和 C001 在**随附的 CLI 与 Agent Skill 中**默认启用雷达分析。原始 API 的默认值可能不同，直接调用 API 时应显式设置 `enable_radar`；在 CLI 中可使用 `--no-radar` 关闭。使用 `t001 --auto-safe-words` 时，估值为 T001 的 1 点，加上每个高风险词触发一次 T002 所需的 1 点。计费规则可能随服务调整，请以 ERiC 平台显示为准。

### 支持的输入

随附的 CLI 为 D001、L001、C001 和 P001 接受以下输入，并将图片转换为原始 API 所需的 base64 格式：

- 本地图片路径
- `http://` 或 `https://` 图片 URL
- base64 图片字符串

文本接口接受产品标题、描述以及相应的市场或站点参数。I001 当前仅支持美国；其他接口的地区范围请查看对应参考文档。

### 项目结构

```text
eric-compliance-suite/
├── SKILL.md                         # Agent 指令、路由规则与接口摘要
├── scripts/
│   └── detect.py                    # 12 个子命令的统一 CLI 入口
└── references/
    ├── design-patent.md             # D001
    ├── invention-patent.md          # I001
    ├── logo-detection.md            # L001
    ├── trademark-detection.md       # T001 / T002
    ├── copyright-detection.md       # C001
    └── policy-detection.md          # P001 / P002 / P004–P007
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

[MIT](SKILL.md)
