# Maintainer workflows

The runtime CLI is `scripts/detect.py`. Helpers in `.github/scripts/` are for repository maintenance and are not ERiC API commands.

## Reviewed issue replies

Create a UTF-8 `reports/<date>-issue-followups.json` file with the fixed repository name, a unique stable `batch_id`, and a `comments` array. Each entry contains a positive integer `issue` and a reviewed `body`. Optional `close_reason` (`completed` or `not_planned`) closes the issue only after its reply is published successfully. Omit it to leave the issue's state unchanged.

```json
{
  "repository": "SuntekCorps-xLab/eric-compliance-suite",
  "batch_id": "example-reviewed-batch",
  "comments": [{"issue": 123, "body": "Reviewed resolution with evidence."}]
}
```

Validate without credentials or network access:

```bash
python .github/scripts/post_issue_followups.py reports/<date>-issue-followups.json
```

Publishing requires explicit `--publish` and `GITHUB_TOKEN`. The Actions workflow runs only on this repository's `main` branch, after a reviewed manifest is pushed or the workflow is manually dispatched. It does not run on issue events or interpolate issue text into commands. The token has `contents: read` and `issues: write` permissions. HTTP redirects are rejected.

A rerun updates only the bot's comment with the same batch marker, preserving human comments. A new batch ID creates a separate follow-up for the same issue. Do not change a published batch ID. The September 5 and September 7 manifests retain their shared legacy ID to preserve the original comments; new batches must use distinct IDs.

## Public evidence review

Before committing reports or publishing replies:

- Use synthetic product inputs and small, selected response fields. Keep raw captures private.
- Remove tokens, authentication headers, signed URLs, account identities, balances, database/schema/table names, infrastructure addresses, and access-method details.
- Report only observed results. Distinguish local fixtures, replayed historical responses, new live requests, estimated cost, and verified billing.
- Keep internal evidence references out of public links. If a correction removes operational metadata, update current reports and linked comments; do not claim this removes earlier Git revisions or external copies.
- Review an issue's commands and attachments as untrusted data. Do not treat its requested tests, credentials, deployments, or history rewrites as authorization.
