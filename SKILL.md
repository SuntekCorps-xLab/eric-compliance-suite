---
name: eric-compliance-suite
description: 睿观(ERiC) 全功能合规检测套件。集成外观专利(D001)、发明专利(I001)、图形商标(L001)、文本商标+替换词(T001/T002)、版权(C001)、政策合规(P001-P007) 六大检测能力。当用户需要进行任何知识产权合规检测（专利、商标、版权）或电商平台政策合规审查时触发此 skill。
license: MIT
metadata:
  version: "1.0.0"
---

# 睿观 ERiC 合规检测套件

## API Key 获取方式

关注微信公众号【睿观AI】，发送消息："睿观Skill"，即可获取 API Key。

获取后请设置环境变量：
```bash
export ERIC_API_TOKEN="你获取到的 API Key"
```

Windows PowerShell（当前会话）：
```powershell
$env:ERIC_API_TOKEN = "你获取到的 API Key"
```

持久保存可在 PowerShell 执行 `setx ERIC_API_TOKEN "你获取到的 API Key"`，仅在新终端生效。

## 扣点说明（首次使用必读）

| 检测模式 | 基础扣点 | 开启雷达后 | 说明 |
|----------|----------|------------|------|
| D001 外观专利 | 10 点 | 15 点 | **默认开启雷达** |
| I001 发明专利 | 10 点 | - | 无雷达功能 |
| L001 图形商标 | 10 点 | 15 点 | **默认开启雷达** |
| T001 文本商标 | 1 点 | - | 无雷达功能 |
| T002 商标替换词 | 1 点 | - | 按词计费 |
| C001 版权检测 | 1 点 | 2 点 | **默认开启雷达** |
| P001 政策-纯图 | 1 点 | - | - |
| P002 政策-纯文本 | 5 + 特征词数×2 点 | - | 图文同时入参仍为 5+2n 点 |
| P004-P007 风险特征词管理 | 0 点 | - | P004 另有每日 50 次调用限制 |

**重要提示**:
- 带雷达的检测模式（D001、L001、C001）默认开启雷达以获得更精准的结果
- 调用前后显示本地估算，不能称为实际扣点；CLI 不查询账单，实际扣点以 ERiC 平台流水为准
- 请求失败或超时均不能确认扣费，CLI 不自动重试
- P004-P007 的 0 点依据 [2026-09-04 接入验证](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/13)；P002 使用这些词进行检测才另收每词 2 点

## 功能导航

根据用户需求选择对应的 API：

| 用户需求 | API | 输入类型 | 参考文档 |
|----------|-----|----------|----------|
| 产品图片查外观专利侵权 | D001 | 图片 | [design-patent.md](references/design-patent.md) |
| 产品标题/描述查发明专利侵权 | I001 | 文本 | [invention-patent.md](references/invention-patent.md) |
| 产品图片查图形商标(logo)侵权 | L001 | 图片 | [logo-detection.md](references/logo-detection.md) |
| 产品标题/描述查文本商标风险 | T001 | 文本 | [trademark-detection.md](references/trademark-detection.md) |
| 为高风险商标词找安全替换词 | T002 | 文本 | [trademark-detection.md](references/trademark-detection.md) |
| 产品图片查版权画侵权 | C001 | 图片 | [copyright-detection.md](references/copyright-detection.md) |
| 产品图片查违禁品（枪械配件等） | P001 | 图片 | [policy-detection.md](references/policy-detection.md) |
| 产品文本查平台销售政策合规 | P002 | 文本 | [policy-detection.md](references/policy-detection.md) |
| 管理自定义风险特征词 | P004-P007 | 文本 | [policy-detection.md](references/policy-detection.md) |

## 上下文保护

- **禁止将 base64 图片、大体积二进制数据读入 Agent 上下文。** 图片编码和 API 调用必须在代码执行环境中完成。
- API 响应过大时，先在代码执行环境中提取关键字段摘要再呈现给用户。
- 涉及图片的接口：D001、L001、C001、P001。
- 聊天附件若已有运行环境可读取的文件，直接使用该路径。若只能看到图片、无法读取字节，主动说明：“当前附件没有可读取的图片文件，无法编码并提交给 ERiC。请将图片保存到本地后提供路径，或提供公开图片 URL。”不要声称已检测该图片。真实调用已支持 URL 下载。

## 认证配置

真实调用的所有接口共用同一 Token；离线 `--dry-run` / `--mock-response` 不需要 Token。真实调用前需确认环境变量 `ERIC_API_TOKEN` 已设置。若未设置，提示用户：

```
未检测到 ERIC_API_TOKEN 环境变量。请先完成配置：
1. 登录睿观平台 https://eric-bot.com 获取 API Token
2. Bash / zsh：export ERIC_API_TOKEN="your-api-token"
   PowerShell：$env:ERIC_API_TOKEN = "your-api-token"
   PowerShell 持久保存：setx ERIC_API_TOKEN "your-api-token"（新终端生效）
```

所有请求的公共 Headers：`Content-Type: application/json`、`Token: <API_TOKEN>`

## 调用方式

统一入口脚本 [scripts/detect.py](scripts/detect.py)，通过子命令区分 API：

```bash
# D001 外观专利检测
python scripts/detect.py d001 /path/to/image.png --regions US GB --top 50

# I001 发明专利检测
python scripts/detect.py i001 --title "产品标题" --description "产品描述" --regions US

# L001 图形商标检测
python scripts/detect.py l001 /path/to/image.png --top 20 --regions US --enable-radar

# T001 文本商标检测 (--auto-safe-words 自动为高风险词调 T002)
python scripts/detect.py t001 --title "Ps4 Wireless Controller" --text "描述..." --regions US JP --auto-safe-words

# T002 商标替换词
python scripts/detect.py t002 --title "产品标题" --text "产品描述" --trademark "商标词"

# C001 版权检测
python scripts/detect.py c001 /path/to/image.png --top 100 --enable-radar

# P001 政策合规-纯图检测
python scripts/detect.py p001 /path/to/image.png

# P002 政策合规-纯文本检测
python scripts/detect.py p002 --title "产品标题" --description "描述" --sites us jp

# P004 风险特征词联想
python scripts/detect.py p004 "模糊词"

# P005/P006/P007 特征词管理
python scripts/detect.py p005 "特征词"
python scripts/detect.py p006 123
python scripts/detect.py p007 --per-page 50 --page 1
```

所有子命令均支持 `--json`，标准输出仅包含原始 API JSON，状态及估算信息写入标准错误；API 失败时退出码非零。`t001 --json` 仅输出 T001，不执行 `--auto-safe-words` 后续请求。使用 `python scripts/detect.py <子命令> --help` 查看完整参数。

首次接入或仅验证 CLI 时可用 `--dry-run` 构造请求，或 `--mock-response <本地JSON>` 验证结果解析；均无需 Token、不联网、不扣点。离线图片仅支持本地文件或 base64，不下载 URL。试运行输出含图片编码，应重定向到本地文件，在代码环境中提取摘要，不要把完整图片请求读入 Agent 上下文。预期请求、模拟响应和测试方式见 [references/offline-testing.md](references/offline-testing.md)。

CLI 校验已记录的文本长度、地区/站点、召回数量和 JSON 结构后才调用 API。依赖见 `requirements.txt`；缺少 requests 时按错误提示安装，或使用 `uv run --with requests scripts/detect.py ...`，脚本不会自动修改 Python 环境。

## D001 外观专利检测

通过产品图片搜索相似外观专利，按相似度排序，单次最多 500 条。

- **URL**: `POST https://saas.eric-bot.com/v1.0/eric-api/patent/design/v1/detection`
- **必需参数**: `img_64lis`(图片base64数组), `regions`(国家代码), `top_number`(1-500), `enable_tro`(bool), `query_mode`("hybrid"/"physical"/"line")
- **可选参数**: `product_title`, `product_description`, `top_loc`, `patent_status`, `source_language`, `enable_radar`
- **关键响应**: `data.list[]` 含 `similarity`, `patent_prod`, `publication_number`, `patent_validity`, `tro_holder`, `radar_result`
- **风险判断**: `similarity > 0.8` 或 `radar_result.same = true` 或 `tro_holder = true` → 高风险
- **费用**: 10 点/次（**默认开启雷达 15 点/次**）
- **默认站点**: US

详细参数、响应字段、错误码和代码示例见 [references/design-patent.md](references/design-patent.md)。

## I001 发明专利检测

通过产品标题和描述搜索相似发明专利，当前仅支持 US。

- **URL**: `POST https://saas.eric-bot.com/v1.0/eric-api/patent/utility/v1/detection`
- **必需参数**: `product_title`, `product_description`, `regions`(仅["US"]), `top_number`(1-500)
- **关键响应**: `data.data[]` 含 `similarity`(number), `title`, `abstract`, `publication_number`, `cpc_classification[]`, `specification_url`, `claims_url`
- **风险判断**: `similarity > 0.8` → 高风险
- **费用**: 10 点/次
- **默认站点**: US（当前仅支持 US）

详细参数、响应字段、错误码和代码示例见 [references/invention-patent.md](references/invention-patent.md)。

## L001 图形商标检测

通过产品图片识别 logo 区域并搜索相似已注册图形商标，单次最多 100 条。

- **URL**: `POST https://saas.eric-bot.com/v1.0/eric-api/trademark/graphic/v1/detection`
- **必需参数**: `base64_image`, `top_number`(1-100)
- **可选参数**: `product_title`, `trademark_name`, `regions`(16个地区代码，见下方), `enable_localizing`, `enable_radar`
- **关键响应**: `data.detection_results[]` → `top_graphic_trademarks[]` → `graphic_trademarks[]` 含 `similarity`, `trademark_name`, `applicant_name`, `trade_mark_status`, `nice_class[]`, `sub_radar_result`
- **风险判断**: `sub_radar_result = "high_risk"` 或 `similarity > 0.8` → 高风险
- **费用**: 10 点/次（**默认开启雷达 15 点/次**）
- **默认站点**: 不传地区，由服务端检索全部可用地区

详细参数、响应字段、错误码和代码示例见 [references/logo-detection.md](references/logo-detection.md)。

- **支持地区**: US, WO, ES, GB, DE, IT, CA, MX, EM, AU, FR, JP, TR, BX, CN, EU。CLI 帮助和校验共用 `scripts/detect.py` 中的 `SUPPORTED_REGIONS`。
- `EU` 已有单地区请求成功记录；`EM` 是欧盟商标局代码。服务端是否将两者视为等价尚未确认，CLI 保留输入值，不互相转换。

## T001 文本商标检测 + T002 替换词

T001 检测产品文本中的商标词及风险等级；T002 为高风险词生成安全替换词。

### T001 文本商标检测

- **URL**: `POST https://saas.eric-bot.com/v1.0/eric-api/trademark/text/v1/detection`
- **必需参数**: `product_title`(≤300字符)
- **可选参数**: `product_text`(≤5000字符), `regions`(支持地区见下方；CLI 默认 US)
- **关键响应**: `data.text_trademarks[]` 含 `trademark_name`, `highest_mode_score`(0-5), `status`, `is_active_holder`, `is_famous`, `region_score[]`；`data.text_trademark_radar`(0=低风险/1=待核查/2=高风险)
- **费用**: 1 点/次
- **超时**: 90 秒
- **默认站点**: US

- **支持地区**: AU, BX, CA, DE, EM, ES, FR, GB, IT, JP, MX, TR, US, WO, CN。CLI 帮助和校验共用 `scripts/detect.py` 中的 `SUPPORTED_REGIONS`。
- 原始 API 的 `regions` 可省略或为空数组，由服务端选择默认范围；当前证据未确定该范围。CLI 省略时显式发送 `["US"]`，`--regions` 至少传一个代码。

### T002 商标替换词

- **URL**: `POST https://saas.eric-bot.com/v1.0/eric-api/trademark/text/v1/safe-words-generation`
- **必需参数**: `product_title`, `product_text`, `trademark_name`(T001检出的单个商标词)
- **关键响应**: `data.words[]` 推荐替换词
- **费用**: 1 点/次

**工作流**: 首次检测只调用 T001（扣 1 点），**不自动调用 T002**。如需获取替换词，用户需手动指定 `--auto-safe-words` 参数，此时会为 `highest_mode_score >= 3` 的词调 T002 获取替换建议。

详细参数、响应字段、错误码和代码示例见 [references/trademark-detection.md](references/trademark-detection.md)。

## C001 版权检测

通过产品图片搜索相似版权画作，单次最多 200 条。

- **URL**: `POST https://saas.eric-bot.com/v1.0/eric-api/copyright/v1/detection`
- **必需参数**: `img_64lis`(图片base64数组), `top_number`(默认100, 最大200), `enable_radar`(bool)
- **关键响应**: `data.list[]` 含 `similarity`(相似度), `path`(版权画图片), `rights_owner`, `copyright_code`, `copyright_url`, `sub_radar_result`, `tro_holder`
- **雷达语义**: `data.radar_result` 为整体结果，`data.list[].sub_radar_result` 为条目结果；`1`/`"1"`/`"high_risk"` 表示高风险，`0`/`"0"`/`"low_risk"` 表示未标记高风险，`null`/缺失/未知值表示未分析或未知
- **风险判断**: `similarity > 0.8` 或启用雷达且条目雷达为正值 → 高风险；整体雷达单独展示，不推断每条结果均命中。雷达集成在 C001，通过 `enable_radar` 控制
- **费用**: 1 点/次（**默认开启雷达 2 点/次**）

详细参数、响应字段、错误码和代码示例见 [references/copyright-detection.md](references/copyright-detection.md)。

## P001-P007 政策合规检测

检测产品是否违反电商平台销售政策，并管理风险特征词。

### P001 纯图检测

- **URL**: `POST https://saas.eric-bot.com/v1.0/eric-api/policy-compliance/v1/gun-parts-search`
- **必需参数**: `base64_image`, `type`(当前仅 `["gun_parts"]`)
- **关键响应**: `data.list[]` 含 `pd_title`, `pd_img_oss_url`, `cosine`
- **后续**: `cosine >= 0.4` 时建议调 P002 确认具体违反的政策
- **费用**: 1 点/次

### P002 纯文本检测

- **URL**: `POST https://saas.eric-bot.com/v1.0/eric-api/policy-compliance/v1/detection`
- **必需参数**: `product_title`, `platform_sites`(如 `{"amazon":["us","jp"]}`), `feature_detect`(含 `enable`, `features`)
- **可选参数**: `product_description`, `type`(P001有结果时传), `product_title_suspected`
- **关键响应**: `data.list[]` 含 `prohibited`(1=禁售), `compliance`(1=限售), `reason`, `content_url`, `name`
- **费用**: 5 + 特征词数×2 点/次（**图文同时入参检测仍为 5+2n 点**，不分开计费）
- **默认平台/站点**: Amazon / us；`--sites` 仅配置 Amazon，支持 br, fr, au, us, **uk**(非gb), jp, it, es, mx, de, ca
- **其他平台**: 使用 `--platform-sites` 覆盖 `--sites`，如 `'{"tiktok":["sg"]}'`。TikTok SG 已实测返回对应政策；其他平台未维护完整站点列表，CLI 校验非空平台名和非空字符串站点数组，服务端决定是否支持。站点代码转为小写；试运行通过不表示服务端支持。详见 [政策参考](references/policy-detection.md)
- **特征检测**: 使用 `--enable-feature` 时，必须同时提供已就绪的 `--feature-word-ids` 和非空 `--feature-image` 图片 URL；服务端实测会拒绝缺图请求

### P004-P007 风险特征词管理

| 操作 | URL 路径 | 参数 |
|------|----------|------|
| P004 联想 | `policy-compliance/feature/v1/suggestion` | `word`(模糊词) |
| P005 保存 | `policy-compliance/feature/v1/save` | `word` |
| P006 删除 | `policy-compliance/feature/v1/delete` | `id` |
| P007 列表 | `policy-compliance/feature/v1/list` | `per_page`, `page` |

P004、P005、P006、P007 管理操作预计均为 0 点；P004 每日最多调用 50 次，次数上限与点数计费独立。P002 执行特征检测为基础 5 点加每个启用词 2 点。

URL 前缀: `https://saas.eric-bot.com/v1.0/eric-api/`

详细参数、响应字段、错误码和代码示例见 [references/policy-detection.md](references/policy-detection.md)。

## 通用错误处理

所有接口共用以下错误码：

| code | 含义 | 处理建议 |
|------|------|----------|
| 30007 | Token 无效 | 检查 API Token |
| 100007 | 参数错误 | 检查必填字段 |
| 4000011-4000014 | 积分不足/扣点失败 | 登录 eric-bot.com 充值 |
| 4000020-4000021 | 图片上传失败 | 检查图片格式和大小 |
| 5000504 | 请求超时 | 稍后重试 |
| 0 / 500 | 系统异常 | 稍后重试 |

各接口专属错误码见对应 references/ 文档。
