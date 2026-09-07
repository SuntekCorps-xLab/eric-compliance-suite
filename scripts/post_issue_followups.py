#!/usr/bin/env python3
"""Publish the reviewed follow-ups for the September 2026 CLI issues."""

import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


REPOSITORY = "SuntekCorps-xLab/eric-compliance-suite"
MARKER = "<!-- eric-cli-followup-2026-09-05 -->"


def load_followups(path):
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("repository") != REPOSITORY:
        raise ValueError("Follow-ups must target this repository")
    comments = document.get("comments")
    if not isinstance(comments, list) or not comments:
        raise ValueError("A nonempty comments array is required")
    seen = set()
    for comment in comments:
        issue, body = comment.get("issue"), comment.get("body")
        if type(issue) is not int or not 1 <= issue <= 17 or issue in seen:
            raise ValueError("Issue numbers must be unique integers from 1 through 17")
        if not isinstance(body, str) or not body.strip() or len(body) > 60000:
            raise ValueError("Each comment needs a nonempty body under 60,000 characters")
        seen.add(issue)
    return comments


def github_request(method, path, token, payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "eric-cli-issue-followups",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def publish_comment(issue, body, request):
    full_body = body.rstrip() + "\n\n" + MARKER
    page = 1
    while True:
        existing = request("GET", f"issues/{issue}/comments?per_page=100&page={page}")
        for comment in existing:
            if comment.get("user", {}).get("login") != "github-actions[bot]":
                continue
            if MARKER not in comment.get("body", ""):
                continue
            if comment["body"] == full_body:
                return "unchanged", comment["html_url"]
            updated = request("PATCH", f"issues/comments/{comment['id']}", {"body": full_body})
            return "updated", updated["html_url"]
        if len(existing) < 100:
            break
        page += 1
    created = request("POST", f"issues/{issue}/comments", {"body": full_body})
    return "created", created["html_url"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="Reviewed JSON follow-up file")
    parser.add_argument("--publish", action="store_true", help="Publish using GITHUB_TOKEN; otherwise only validate")
    args = parser.parse_args(argv)
    try:
        comments = load_followups(args.file)
        if not args.publish:
            print(f"Validated {len(comments)} issue follow-ups; no network requests made.")
            return 0
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if not token:
            raise ValueError("GITHUB_TOKEN is required to publish")
        for comment in comments:
            status, url = publish_comment(
                comment["issue"], comment["body"],
                lambda method, path, payload=None: github_request(method, path, token, payload),
            )
            print(f"#{comment['issue']}: {status} {url}", flush=True)
        return 0
    except urllib.error.HTTPError as exc:
        print(f"GitHub API returned HTTP {exc.code}; remaining comments were not published.", file=sys.stderr)
    except (OSError, ValueError) as exc:
        print(f"Follow-up publishing failed: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
