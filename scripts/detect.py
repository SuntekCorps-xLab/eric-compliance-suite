#!/usr/bin/env python3
"""睿观 ERiC 合规检测套件 - 统一入口
子命令: d001, i001, l001, t001, t002, c001, p001, p002, p004, p005, p006, p007
"""

import argparse
import base64
import binascii
import copy
import json
import os
import sys

# Windows 中文环境默认使用 GBK 编码，无法输出 emoji 字符，强制切换到 UTF-8
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure") and stream.encoding != "utf-8":
        stream.reconfigure(encoding="utf-8")

BASE = "https://saas.eric-bot.com/v1.0/eric-api"

# CLI help and validation share these contracts; documentation is checked in tests.
SUPPORTED_REGIONS = {
    "d001": tuple("SE EU CH IE BR MX US WO GB IL JP IN DK DE AU IT NZ AT CA BX FI FR CN KR TH MY".split()),
    "i001": ("US",),
    "l001": tuple("US WO ES GB DE IT CA MX EM AU FR JP TR BX CN EU".split()),
    "t001": tuple("AU BX CA DE EM ES FR GB IT JP MX TR US WO CN".split()),
}
# Only enforce a site allowlist where a complete platform contract is documented.
# Other platforms still require nonempty string arrays; the API validates support.
PLATFORM_SITE_ALLOWLISTS = {
    "amazon": tuple("br fr au us uk jp it es mx de ca".split()),
}


class CLIError(Exception):
    """An actionable error that does not need a traceback."""

# 扣点配置表
POINT_COSTS = {
    "d001": {"base": 10, "radar": 15, "has_radar": True},
    "i001": {"base": 10, "radar": 10, "has_radar": False},
    "l001": {"base": 10, "radar": 15, "has_radar": True},
    "t001": {"base": 1, "radar": 1, "has_radar": False},
    "t002": {"base": 1, "radar": 1, "has_radar": False},
    "c001": {"base": 1, "radar": 2, "has_radar": True},  # 雷达+1
    "p001": {"base": 1, "radar": 1, "has_radar": False},
    "p002": {"base": 5, "radar": 5, "has_radar": False},  # 图文同时检测仍为5点
    **{cmd: {"base": 0, "has_radar": False} for cmd in ("p004", "p005", "p006", "p007")},
}

# 默认站点配置
DEFAULT_REGIONS = {
    "d001": ["US"],
    "i001": ["US"],
    "l001": None,  # None 表示全部
    "t001": ["US"],
    "p002": ["us"],
}

def estimate_points(args):
    cost = POINT_COSTS[args.command]
    points = cost["radar"] if cost["has_radar"] and not args.no_radar else cost["base"]
    if args.command == "p002" and args.enable_feature:
        points += 2 * len(args.feature_word_ids)
    return points


def request_headers(token):
    return {"Content-Type": "application/json", "Token": token}


def perform_request(args, token, path, payload, timeout=120):
    """Shared preview, transport, failure handling and estimated billing for all commands."""
    points = estimate_points(args)
    if args.dry_run:
        preview = {
            "dry_run": True,
            "command": args.command,
            "method": "POST",
            "url": f"{BASE}/{path}",
            "headers": request_headers("<redacted>" if token else "<ERIC_API_TOKEN>"),
            "token_configured": bool(token),
            "payload": payload,
            "estimated_points": points,
            "points_consumed": 0,
        }
        if getattr(args, "auto_safe_words", False):
            preview["follow_up"] = "T002: 每个高风险词预计 1 点；词数取决于 T001 响应，试运行不执行。"
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        raise SystemExit(0)

    if args.mock_response:
        if not args.mock_responses:
            raise CLIError("模拟响应已用完；请提供包含后续 T002 响应的 JSON 数组。")
        result = args.mock_responses.pop(0)
        print(f"模拟 {args.command.upper()}：未发送请求，消耗 0 点（真实调用预计 {points} 点）", file=sys.stderr)
    else:
        print(f"📊 {args.command.upper()} 预计扣点: {points} 点（本地估算）", file=sys.stderr)
        result = api_call(token, path, payload, timeout)

    if not isinstance(result, dict) or not isinstance(result.get("success"), bool):
        raise CLIError("API 响应格式无效：需要含布尔 success 字段的 JSON 对象。")
    if not result["success"]:
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"API 错误 [{result.get('code')}]: {result.get('message')}", file=sys.stderr)
        if not args.mock_response:
            print("请求失败，扣点未确认；请以 ERiC 平台流水为准。", file=sys.stderr)
        raise SystemExit(1)
    if not args.mock_response:
        print(f"💰 {args.command.upper()} 调用完成，预计扣点: {points} 点；实际扣点请以 ERiC 平台流水为准。", file=sys.stderr)
    return result


def show_default_regions(cmd, regions):
    regions = DEFAULT_REGIONS.get(cmd) if regions is None else regions
    label = ', '.join(regions) if regions is not None else "全部国家/地区"
    print(f"📍 检测站点: {label}", file=sys.stderr)


def check_token():
    token = os.environ.get("ERIC_API_TOKEN", "").strip()
    if not token:
        raise CLIError(
            "未设置 ERIC_API_TOKEN 环境变量。登录 https://eric-bot.com 获取 API Token。\n"
            'Bash / zsh: export ERIC_API_TOKEN="your-api-token"\n'
            'PowerShell（当前会话）: $env:ERIC_API_TOKEN = "your-api-token"\n'
            'PowerShell（持久保存，新终端生效）: setx ERIC_API_TOKEN "your-api-token"\n'
            "无需 Token 的离线验证：在命令后添加 --dry-run 或 --mock-response <JSON文件>。"
        )
    return token


def ensure_requests():
    try:
        import requests
        return requests
    except ImportError as exc:
        raise CLIError(
            "缺少 requests；请在项目目录执行 python -m pip install -r requirements.txt，"
            "或 uv pip install -r requirements.txt。\n"
            "也可直接使用 uv run --with requests scripts/detect.py <子命令及参数>。"
        ) from exc


def api_call(token, path, payload, timeout=120):
    requests = ensure_requests()
    try:
        resp = requests.post(
            f"{BASE}/{path}", headers=request_headers(token), json=payload, timeout=timeout,
        )
        # Preserve ERiC error envelopes, including those delivered with HTTP 4xx/5xx.
        result = resp.json()
        if not isinstance(result, dict) or result.get("success") is not False:
            resp.raise_for_status()
        return result
    except (requests.RequestException, ValueError) as exc:
        raise CLIError(
            "API 请求失败或响应不是有效 JSON；未自动重试，扣点未确认，请查看 ERiC 平台流水。"
        ) from exc


def load_image(source, offline=False):
    """Encode a local file, downloaded URL or fully validated base64 string."""
    if source.startswith(("http://", "https://")):
        if offline:
            raise CLIError("离线模式不下载图片 URL；请先保存图片，再提供本地路径或 base64。")
        requests = ensure_requests()
        try:
            resp = requests.get(source, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            if not resp.content:
                raise CLIError("下载的图片为空。")
            return base64.b64encode(resp.content).decode("ascii")
        except requests.RequestException as exc:
            raise CLIError("下载图片失败；请检查图片 URL 或改用本地路径。") from exc
    try:
        if os.path.isfile(source):
            with open(source, "rb") as f:
                content = f.read()
            if not content:
                raise CLIError("图片文件为空。")
            return base64.b64encode(content).decode("ascii")
    except OSError as exc:
        raise CLIError(f"无法读取图片文件：{exc}") from exc
    try:
        if source and base64.b64decode(source, validate=True):
            return source
    except (ValueError, binascii.Error):
        pass
    raise CLIError(
        "无法识别图片来源。请提供可访问的本地图片路径、HTTP(S) URL 或完整 base64。\n"
        "聊天中可见的图片不一定有可读取的文件；请将图片保存到本地后提供路径，或提供公开图片 URL。"
    )


# ── D001 外观专利检测 ──────────────────────────────────────────

def cmd_d001(args, token):
    # 默认开启雷达，使用 --no-radar 关闭
    enable_radar = not getattr(args, 'no_radar', False)

    show_default_regions("d001", args.regions)

    img_b64 = load_image(args.image, offline=args.dry_run or bool(args.mock_response))
    payload = {
        "product_title": args.title,
        "product_description": args.description,
        "regions": args.regions,
        "img_64lis": [img_b64],
        "top_loc": args.loc,
        "patent_status": args.patent_status,
        "top_number": args.top,
        "enable_tro": not args.no_tro,
        "source_language": args.lang,
        "query_mode": args.mode,
        "enable_radar": enable_radar,
    }
    result = perform_request(args, token, "patent/design/v1/detection", payload)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    patents = result.get("data", {}).get("list", [])
    print(f"共找到 {len(patents)} 条相似外观专利\n")
    for i, p in enumerate(patents[:20], 1):
        sim = float(p.get("similarity", 0))
        risk = "🔴高风险" if sim > 0.8 else ("🟡中风险" if sim > 0.5 else "🟢低风险")
        tro = " [TRO]" if p.get("tro_holder") or p.get("tro_case") else ""
        radar = ""
        if enable_radar and (p.get("radar_result") or {}).get("same"):
            radar = " [雷达:疑似侵权]"
            risk = "🔴高风险"
        print(f"{i}. {risk}{tro}{radar}")
        print(f"   相似度: {sim:.4f} | 公开号: {p.get('publication_number', '')}")
        print(f"   专利标题: {p.get('patent_prod', '')} / {p.get('patent_prod_cn', '')}")
        print(f"   有效性: {p.get('patent_validity', '')} | 受理局: {p.get('registration_office_code', '')}")
        print()
    if len(patents) > 20:
        print(f"... 还有 {len(patents) - 20} 条结果未显示，使用 --json 查看完整结果")


# ── I001 发明专利检测 ──────────────────────────────────────────

def cmd_i001(args, token):
    show_default_regions("i001", args.regions)

    result = perform_request(args, token, "patent/utility/v1/detection", {
        "product_title": args.title,
        "product_description": args.description,
        "regions": args.regions,
        "top_number": args.top,
    })

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    patents = result.get("data", {}).get("data", [])
    print(f"共找到 {len(patents)} 条相似发明专利\n")
    for i, p in enumerate(patents[:20], 1):
        sim = float(p.get("similarity", 0))
        risk = "🔴高风险" if sim > 0.8 else ("🟡中风险" if sim > 0.5 else "🟢低风险")
        tro = " [TRO]" if p.get("tro_holder") or p.get("tro_case") else ""
        print(f"{i}. {risk}{tro}")
        print(f"   相似度: {sim:.4f} | 公开号: {p.get('publication_number', '')}")
        print(f"   标题: {p.get('title', '')} / {p.get('title_cn', '')}")
        print(f"   有效性: {p.get('patent_validity', '')}")
        print()
    if len(patents) > 20:
        print(f"... 还有 {len(patents) - 20} 条结果未显示，使用 --json 查看完整结果")


# ── L001 图形商标检测 ──────────────────────────────────────────

def cmd_l001(args, token):
    # 默认开启雷达，使用 --no-radar 关闭
    enable_radar = not getattr(args, 'no_radar', False)

    show_default_regions("l001", args.regions)

    img_b64 = load_image(args.image, offline=args.dry_run or bool(args.mock_response))
    payload = {
        "product_title": args.title,
        "base64_image": img_b64,
        "trademark_name": args.trademark_name,
        "top_number": args.top,
        "enable_localizing": args.enable_localizing,
        "enable_radar": enable_radar,
    }
    if args.regions:
        payload["regions"] = args.regions

    result = perform_request(args, token, "trademark/graphic/v1/detection", payload)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    data = result.get("data", {})
    print(f"检测到 {data.get('bounding_box_count', 0)} 个logo区域")
    if data.get("radar_result"):
        print(f"整体雷达风险: {data['radar_result']}\n")

    for dr in data.get("detection_results", []):
        idx = dr.get("index", 0)
        total = dr.get("total_detection_result_count", 0)
        print(f"--- 区域 {idx} (召回: {total}条) ---")
        for rg in dr.get("top_graphic_trademarks", []):
            region = rg.get("region", "")
            tms = rg.get("graphic_trademarks", [])
            print(f"\n  国家/地区: {region} ({len(tms)} 条)")
            for j, tm in enumerate(tms[:10], 1):
                sim = float(tm.get("similarity", 0))
                risk = "🔴高" if sim > 0.8 else ("🟡中" if sim > 0.5 else "🟢低")
                sub_r = f" [{tm.get('sub_radar_result')}]" if tm.get("sub_radar_result") else ""
                print(f"  {j}. {risk}{sub_r} 相似度:{sim:.4f} | {tm.get('trademark_name','')} | 权利人:{tm.get('applicant_name','')} | 状态:{tm.get('trade_mark_status','')}")
            if len(tms) > 10:
                print(f"  ... 还有 {len(tms) - 10} 条")
        print()


# ── T001 文本商标检测 ──────────────────────────────────────────

def cmd_t001(args, token):
    show_default_regions("t001", args.regions)
    # 首次检测只调 T001，不自动调 T002
    auto_safe = args.auto_safe_words

    result = perform_request(args, token, "trademark/text/v1/detection", {
        "product_title": args.title,
        "product_text": args.text,
        "regions": args.regions,
    }, timeout=90)  # 超时配置为90秒

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    data = result.get("data", {})
    radar = data.get("text_trademark_radar", 0)
    radar_labels = {0: "🟢低风险", 1: "🟡待人工核查", 2: "🔴高风险"}
    print(f"整体风险等级: {radar_labels.get(radar, radar)}\n")

    trademarks = data.get("text_trademarks", data.get("trademark_list", []))
    if not trademarks:
        print("未检测到商标词风险")
        return

    trademarks.sort(key=lambda x: x.get("highest_mode_score", 0), reverse=True)
    for i, tm in enumerate(trademarks, 1):
        score = tm.get("highest_mode_score", 0)
        risk = "🔴" if score >= 3 else ("🟡" if score >= 1 else "🟢")
        flags = []
        if tm.get("is_famous"): flags.append("著名商标")
        if tm.get("is_active_holder"): flags.append("活跃维权人")
        if tm.get("is_amazon_brand"): flags.append("Amazon品牌")
        if tm.get("is_common_sense"): flags.append("常用词")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"{i}. {risk} {tm.get('trademark_name', tm.get('trademark', ''))} (分数:{score}/5, 状态:{tm.get('status', '')}){flag_str}")
        rs = tm.get("region_score", [])
        if rs:
            scores_str = ", ".join(f"{r.get('region','')}:{r.get('score',0)}" for r in rs)
            print(f"   各国风险: {scores_str}")

    if auto_safe:
        high_risk = [tm for tm in trademarks if tm.get("highest_mode_score", 0) >= 3]
        followup_args = copy.copy(args)
        followup_args.command = "t002"
        for tm in high_risk:
            _get_safe_words(followup_args, token, args.title, args.text, tm.get("trademark_name", tm.get("trademark", "")))

# ── T002 商标替换词 ────────────────────────────────────────────

def _get_safe_words(args, token, title, text, trademark_name, output_json=False):
    result = perform_request(args, token, "trademark/text/v1/safe-words-generation", {
        "product_title": title,
        "product_text": text,
        "trademark_name": trademark_name,
    }, timeout=60)
    if output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    words = result.get("data", {}).get("words", [])
    if words:
        print(f"\n「{trademark_name}」的安全替换词: {', '.join(words)}")
    else:
        print(f"\n未找到「{trademark_name}」的合适替换词")

def cmd_t002(args, token):
    _get_safe_words(args, token, args.title, args.text, args.trademark, args.json)

# ── C001 版权检测 ──────────────────────────────────────────────

def normalize_radar(value):
    """1/0 and legacy high_risk/low_risk; absent or unknown stays unknown."""
    if isinstance(value, str):
        value = value.strip().lower()
    if value in (1, "1", "high_risk"):
        return True
    if value in (0, "0", "low_risk"):
        return False
    return None


def radar_label(value):
    normalized = normalize_radar(value)
    if normalized is True:
        return "🔴高风险"
    if normalized is False:
        return "未标记高风险"
    return "未分析/未知"


def cmd_c001(args, token):
    # 默认开启雷达，使用 --no-radar 关闭
    enable_radar = not getattr(args, 'no_radar', False)

    print("📍 版权库匹配检测", file=sys.stderr)

    img_b64 = load_image(args.image, offline=args.dry_run or bool(args.mock_response))
    result = perform_request(args, token, "copyright/v1/detection", {
        "img_64lis": [img_b64],
        "top_number": args.top,
        "enable_radar": enable_radar,
    })

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    data = result.get("data") or {}
    items = data.get("list") or []
    if enable_radar:
        print(f"整体雷达风险: {radar_label(data.get('radar_result'))}")
    print(f"共找到 {len(items)} 条相似版权画作\n")
    for i, item in enumerate(items[:20], 1):
        similarity = item.get("similarity")
        sim = float(similarity if similarity is not None else item.get("cosine") or 0)
        radar = item.get("sub_radar_result")
        high_risk = sim > 0.8 or (enable_radar and normalize_radar(radar) is True)
        risk = "🔴高风险" if high_risk else ("🟡中风险" if sim > 0.5 else "🟢低风险")
        radar_info = f" [雷达:{radar_label(radar)}]" if enable_radar else ""
        tro = " [TRO维权人]" if item.get("tro_holder") else ""
        print(f"{i}. {risk}{radar_info}{tro}")
        print(f"   相似度: {sim:.4f} | 权利人: {item.get('rights_owner', '')}")
        print(f"   版权标识码: {item.get('copyright_code', item.get('design_code', ''))}")
        if item.get("path"):
            print(f"   版权画图片: {item.get('path')}")
        print()
    if len(items) > 20:
        print(f"... 还有 {len(items) - 20} 条结果未显示，使用 --json 查看完整结果")


# ── P001 纯图检测 ──────────────────────────────────────────────

def cmd_p001(args, token):

    img_b64 = load_image(args.image, offline=args.dry_run or bool(args.mock_response))
    result = perform_request(args, token, "policy-compliance/v1/gun-parts-search",
                      {"base64_image": img_b64, "type": ["gun_parts"]})

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    items = result.get("data", {}).get("list", [])
    # API 可能返回字符串消息而非对象列表
    real_items = [it for it in items if isinstance(it, dict)]
    if not real_items:
        print("未找到相似违规产品，产品图片可能无违禁品风险")
        for it in items:
            if isinstance(it, str):
                print(f"  {it}")
        return

    print(f"找到 {len(real_items)} 条相似违规产品:\n")
    for i, item in enumerate(real_items, 1):
        cosine = float(item.get("cosine", 0))
        print(f"{i}. 相似度: {cosine:.4f}")
        print(f"   标题: {item.get('pd_title', '')}")
        print(f"   中文: {item.get('pd_title_CHN_censored', '')}")
        print()

    if any(float(it.get("cosine", 0)) >= 0.4 for it in real_items):
        print("建议: 存在高相似度违规产品，建议继续使用 p002 确认具体违反的政策")


# ── P002 纯文本检测 ────────────────────────────────────────────

def cmd_p002(args, token):
    platform_sites = args.platform_sites
    feature_word_ids = args.feature_word_ids
    print(f"📍 检测平台站点: {json.dumps(platform_sites, ensure_ascii=False)}", file=sys.stderr)

    payload = {
        "product_title": args.title,
        "product_description": args.description or "",
        "product_title_suspected": [args.suspected] if args.suspected else [],
        "platform_sites": platform_sites,
        "feature_detect": {
            "enable": args.enable_feature,
            "features": {
                "feature_word_ids": feature_word_ids,
                "image": args.feature_image or "",
            },
        },
    }
    if args.type:
        payload["type"] = args.type

    result = perform_request(args, token, "policy-compliance/v1/detection", payload, timeout=60)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    items = result.get("data", {}).get("list", [])
    if not items:
        print("未检测到政策合规风险")
        return

    print(f"检测到 {len(items)} 条政策匹配:\n")
    for i, item in enumerate(items, 1):
        prohibited = item.get("prohibited", 0)
        compliance = item.get("compliance", 0)
        if prohibited:
            status = "🔴 禁售"
        elif compliance:
            status = "🟡 限售"
        else:
            status = "🟢 无风险"
        print(f"{i}. {status}")
        print(f"   平台: {item.get('platform', '')} | 地区: {item.get('site', '')}")
        print(f"   政策: {item.get('name_cn', '')} ({item.get('name', '')})")
        if item.get("reason"):
            print(f"   原因: {item.get('reason')}")
        print()


# ── P004-P007 风险特征词管理 ───────────────────────────────────

def cmd_p004(args, token):
    result = perform_request(args, token, "policy-compliance/feature/v1/suggestion", {"word": args.word}, timeout=30)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    data = result.get("data", {})
    status_labels = {-2: "含糊无关", -1: "已够清晰，可直接保存", 0: "已匹配出多个清晰词"}
    print(f"状态: {status_labels.get(data.get('status', 0), data.get('status'))}")
    words = data.get("word_arr", [])
    if words:
        print(f"联想词: {', '.join(words)}")

def cmd_p005(args, token):
    result = perform_request(args, token, "policy-compliance/feature/v1/save", {"word": args.word}, timeout=30)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"保存成功，ID: {result.get('data', {}).get('id')}")

def cmd_p006(args, token):
    result = perform_request(args, token, "policy-compliance/feature/v1/delete", {"id": args.id}, timeout=30)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"删除成功，ID: {result.get('data', {}).get('id')}")

def cmd_p007(args, token):
    result = perform_request(args, token, "policy-compliance/feature/v1/list",
                      {"per_page": args.per_page, "page": args.page}, timeout=30)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    data = result.get("data", {})
    items = data.get("data", [])
    print(f"共 {data.get('total', 0)} 条特征词 (第{args.page}页):\n")
    for item in items:
        ps_labels = {0: "未拉取", 1: "可用", 2: "拉取失败"}
        ps = ps_labels.get(item.get("pull_status", 0), "未知")
        print(f"  ID:{item.get('id')} | {item.get('words', '')} | 状态:{ps} | {item.get('create_time', '')}")

# ── 主入口 ─────────────────────────────────────────────────────

def bounded_int(minimum, maximum=None):
    def parse(value):
        try:
            number = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{value!r} 不是整数") from exc
        if number < minimum or (maximum is not None and number > maximum):
            limit = f"{minimum}-{maximum}" if maximum is not None else f">= {minimum}"
            raise argparse.ArgumentTypeError(f"{value!r} 超出范围，要求 {limit}")
        return number
    return parse


def parse_json(value, option):
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise CLIError(f"{option} JSON 格式无效：{exc}") from exc


def validate_args(args):
    limits = {
        "i001": {"title": 500, "description": 30000},
        "t001": {"title": 300, "text": 5000},
        "t002": {"title": 300, "text": 5000},
        "p002": {"title": 300, "description": 5000},
    }
    for field, limit in limits.get(args.command, {}).items():
        if len(getattr(args, field)) > limit:
            raise CLIError(f"--{field} 长度 {len(getattr(args, field))} 超过最大 {limit} 字符")
    required = {
        "i001": ("title", "description"), "t001": ("title",),
        "t002": ("title", "text", "trademark"), "p002": ("title",),
        "p004": ("word",), "p005": ("word",),
    }
    for field in required.get(args.command, ()):
        if not getattr(args, field).strip():
            raise CLIError(f"{field} 不能为空或仅含空格")
    if args.command == "p002":
        sites = parse_json(args.platform_sites, "--platform-sites") if args.platform_sites else {"amazon": args.sites}
        if not isinstance(sites, dict) or not sites:
            raise CLIError("--platform-sites 必须是非空对象，例如 {\"amazon\":[\"us\"]}")
        for platform, values in sites.items():
            if not platform.strip() or not isinstance(values, list) or not values:
                raise CLIError("--platform-sites 的平台名和站点数组均不能为空")
            supported_sites = PLATFORM_SITE_ALLOWLISTS.get(platform.strip().lower())
            for site in values:
                if not isinstance(site, str) or not site.strip():
                    raise CLIError("--platform-sites 的站点必须是非空字符串")
                if supported_sites is not None and site.lower() not in supported_sites:
                    raise CLIError(
                        f"--platform-sites 平台 {platform!r} 不支持站点 {site!r}；"
                        f"支持 {', '.join(supported_sites)}"
                    )
            sites[platform] = [site.lower() for site in values]
        args.platform_sites = sites
        ids = parse_json(args.feature_word_ids, "--feature-word-ids") if args.feature_word_ids else []
        if not isinstance(ids, list) or any(type(value) is not int or value <= 0 for value in ids):
            raise CLIError("--feature-word-ids 必须是正整数 ID 数组，例如 [123, 456]")
        if len(ids) != len(set(ids)):
            raise CLIError("--feature-word-ids 不能包含重复 ID")
        if (ids or args.feature_image) and not args.enable_feature:
            raise CLIError("--feature-word-ids / --feature-image 需要 --enable-feature")
        if args.enable_feature and not ids:
            raise CLIError("--enable-feature 需要至少一个 --feature-word-ids 中的 ID")
        if args.enable_feature and not args.feature_image.strip():
            raise CLIError("--enable-feature 需要 --feature-image 图片 URL")
        if args.suspected and not args.type:
            raise CLIError("--suspected 需要 --type，例如 --type gun_parts")
        args.feature_word_ids = ids


def build_parser():
    parser = argparse.ArgumentParser(
        description="睿观 ERiC 合规检测套件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""子命令说明:
  d001        D001 外观专利检测 (图片)
  i001        I001 发明专利检测 (文本)
  l001        L001 图形商标检测 (图片)
  t001        T001 文本商标检测 (文本)
  t002        T002 商标替换词 (文本)
  c001        C001 版权检测 (图片)
  p001        P001 政策合规-纯图检测 (图片)
  p002        P002 政策合规-纯文本检测 (文本)
  p004        P004 风险特征词联想
  p005        P005 风险特征词保存
  p006        P006 风险特征词删除
  p007        P007 风险特征词列表""",
    )
    sub = parser.add_subparsers(dest="command", help="检测类型")

    # D001
    d = sub.add_parser("d001", help="D001 外观专利检测")
    d.add_argument("image", help="图片来源: 文件路径 / URL / base64字符串")
    d.add_argument("--regions", nargs="+", type=str.upper, choices=SUPPORTED_REGIONS["d001"], default=["US"], help="国家代码 (默认 US)")
    d.add_argument("--top", type=bounded_int(1, 500), default=50, help="召回数量 1-500 (默认 50)")
    d.add_argument("--mode", choices=["hybrid", "physical", "line"], default="hybrid", help="检索模式")
    d.add_argument("--title", default="", help="产品标题")
    d.add_argument("--description", default="", help="产品描述")
    d_radar = d.add_mutually_exclusive_group()
    d_radar.add_argument("--enable-radar", action="store_true", default=True, help="开启雷达分析（默认开启）")
    d_radar.add_argument("--no-radar", action="store_true", help="关闭雷达分析")
    d.add_argument("--no-tro", action="store_true", help="关闭TRO增强")
    d.add_argument("--loc", nargs="+", default=None, help="LOC分类范围")
    d.add_argument("--patent-status", nargs="+", type=int, choices=[0, 1], default=[], help="专利有效性 (1=有效, 0=失效)")
    d.add_argument("--lang", default="", help="原文语言代码")
    d.add_argument("--json", action="store_true", help="输出原始JSON")

    # I001
    i = sub.add_parser("i001", help="I001 发明专利检测")
    i.add_argument("--title", required=True, help="产品标题 (最大500字符)")
    i.add_argument("--description", required=True, help="产品描述 (最大30000字符)")
    i.add_argument("--regions", nargs="+", type=str.upper, choices=SUPPORTED_REGIONS["i001"], default=["US"], help="国家代码 (当前仅 US)")
    i.add_argument("--top", type=bounded_int(1, 500), default=100, help="召回数量 1-500 (默认 100)")
    i.add_argument("--json", action="store_true", help="输出原始JSON")

    # L001
    l = sub.add_parser("l001", help="L001 图形商标检测")
    l.add_argument("image", help="图片来源: 文件路径 / URL / base64字符串")
    l.add_argument("--top", type=bounded_int(1, 100), default=20, help="召回数量 1-100 (默认 20)")
    l.add_argument("--regions", nargs="+", type=str.upper, choices=SUPPORTED_REGIONS["l001"], default=None, help="检测国家/地区")
    l.add_argument("--title", default="", help="产品标题")
    l.add_argument("--trademark-name", default="", help="可能的logo名称")
    l.add_argument("--enable-localizing", action="store_true", help="开启切图")
    l_radar = l.add_mutually_exclusive_group()
    l_radar.add_argument("--enable-radar", action="store_true", default=True, help="开启雷达分析（默认开启）")
    l_radar.add_argument("--no-radar", action="store_true", help="关闭雷达分析")
    l.add_argument("--json", action="store_true", help="输出原始JSON")

    # T001
    t1 = sub.add_parser("t001", help="T001 文本商标检测")
    t1.add_argument("--title", required=True, help="产品标题 (最大300字符)")
    t1.add_argument("--text", default="", help="产品文本 (最大5000字符)")
    t1.add_argument("--regions", nargs="+", type=str.upper, choices=SUPPORTED_REGIONS["t001"], default=["US"], help="国家/地区 (默认 US)")
    t1.add_argument("--auto-safe-words", action="store_true", help="自动为高风险词获取替换词")
    t1.add_argument("--json", action="store_true", help="输出原始JSON")

    # T002
    t2 = sub.add_parser("t002", help="T002 商标替换词")
    t2.add_argument("--title", required=True, help="产品标题")
    t2.add_argument("--text", required=True, help="产品描述")
    t2.add_argument("--trademark", required=True, help="商标词")
    t2.add_argument("--json", action="store_true", help="输出原始JSON")

    # C001
    c = sub.add_parser("c001", help="C001 版权检测")
    c.add_argument("image", help="图片来源: 文件路径 / URL / base64字符串")
    c.add_argument("--top", type=bounded_int(1, 200), default=100, help="召回数量 1-200 (默认 100)")
    c_radar = c.add_mutually_exclusive_group()
    c_radar.add_argument("--enable-radar", action="store_true", default=True, help="开启雷达检测（默认开启，+1点）")
    c_radar.add_argument("--no-radar", action="store_true", help="关闭雷达检测")
    c.add_argument("--json", action="store_true", help="输出原始JSON")

    # P001
    p1 = sub.add_parser("p001", help="P001 政策合规-纯图检测")
    p1.add_argument("image", help="图片来源: 文件路径 / URL / base64字符串")
    p1.add_argument("--json", action="store_true", help="输出原始JSON")

    # P002
    p2 = sub.add_parser("p002", help="P002 政策合规-纯文本检测")
    p2.add_argument("--title", required=True, help="产品标题")
    p2.add_argument("--description", default="", help="产品描述")
    p2.add_argument("--sites", nargs="+", type=str.lower, choices=PLATFORM_SITE_ALLOWLISTS["amazon"], default=["us"], help="Amazon 国家/地区 (默认 us)")
    p2.add_argument("--platform-sites", default=None, help='平台站点 JSON，覆盖 --sites (如 \'{"tiktok":["sg"]}\')；其他平台的站点支持由 API 校验')
    p2.add_argument("--type", nargs="+", default=None, help="检测类型 (如 gun_parts)")
    p2.add_argument("--suspected", default="", help="疑似违规产品标题")
    p2.add_argument("--enable-feature", action="store_true", help="启用风险特征词检测")
    p2.add_argument("--feature-word-ids", default=None, help="风险特征词ID列表JSON")
    p2.add_argument("--feature-image", default="", help="检测图片URL")
    p2.add_argument("--json", action="store_true", help="输出原始JSON")

    # P004
    p4 = sub.add_parser("p004", help="P004 风险特征词联想")
    p4.add_argument("word", help="模糊词")
    p4.add_argument("--json", action="store_true", help="输出原始JSON")

    # P005
    p5 = sub.add_parser("p005", help="P005 风险特征词保存")
    p5.add_argument("word", help="特征词")
    p5.add_argument("--json", action="store_true", help="输出原始JSON")

    # P006
    p6 = sub.add_parser("p006", help="P006 风险特征词删除")
    p6.add_argument("id", type=bounded_int(1), help="特征词ID")
    p6.add_argument("--json", action="store_true", help="输出原始JSON")

    # P007
    p7 = sub.add_parser("p007", help="P007 风险特征词列表")
    p7.add_argument("--per-page", type=bounded_int(1), default=100, help="每页数量 (默认 100)")
    p7.add_argument("--page", type=bounded_int(1), default=1, help="页码 (默认 1)")
    p7.add_argument("--json", action="store_true", help="输出原始JSON")

    for command_parser in (d, i, l, t1, t2, c, p1, p2, p4, p5, p6, p7):
        modes = command_parser.add_mutually_exclusive_group()
        modes.add_argument("--dry-run", action="store_true", help="离线校验并输出请求 JSON；无需 Token，不联网，不扣点")
        modes.add_argument("--mock-response", metavar="FILE", help="使用本地响应 JSON 或响应数组；无需 Token，不联网，不扣点")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        validate_args(args)
    except CLIError as exc:
        parser.error(str(exc))
    cmds = {
        "d001": cmd_d001, "i001": cmd_i001, "l001": cmd_l001,
        "t001": cmd_t001, "t002": cmd_t002, "c001": cmd_c001,
        "p001": cmd_p001, "p002": cmd_p002,
        "p004": cmd_p004, "p005": cmd_p005, "p006": cmd_p006, "p007": cmd_p007,
    }
    try:
        if args.mock_response:
            with open(args.mock_response, encoding="utf-8-sig") as f:
                responses = json.load(f)
            args.mock_responses = responses if isinstance(responses, list) else [responses]
            if not args.mock_responses or any(
                not isinstance(response, dict) or not isinstance(response.get("success"), bool)
                for response in args.mock_responses
            ):
                raise CLIError("模拟响应必须是含布尔 success 字段的对象或非空对象数组。")
        token = os.environ.get("ERIC_API_TOKEN", "").strip() if args.dry_run or args.mock_response else check_token()
        cmds[args.command](args, token)
    except (CLIError, OSError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
