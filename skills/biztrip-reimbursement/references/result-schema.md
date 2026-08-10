# Agent Interface Schema

Every command writes one JSON object using schema `biztrip.agent-interface.v1`.

## Common fields

- `ok`: Whether the operation itself succeeded.
- `status`: `completed`, `needs_user_input`, or `failed`.
- `operation`: `start`, `status`, or `answer`.
- `task_path`: Internal task identifier. Preserve it for subsequent calls.
- `next_action`: `deliver_package`, `ask_user`, or `inspect_error`.

## Successful task

- `summary.scan_label`: Processed date or mail range.
- `summary.record_count`: Recognized reimbursement records.
- `summary.trip_count`: Grouped trips.
- `summary.total_amount`: Current verified and unverified recognized total.
- `summary.issue_count`: Remaining validation issues.
- `questions`: User-confirmable unresolved issues.
- `files.package_dir`: Present only after verified completion.
- `files.excel`: Present only after verified completion.

## Question

- `record_index`: Stable record position for an answer.
- `issue_codes`: Allowed confirmation types.
- `prompt`: User-facing question.
- `context`: Non-secret evidence describing the record.
- `options`: Engine-approved choices when applicable.
- `attachment_requires_web`: The local Web page is required to add an original document.

Submit only combinations returned by the current task. The engine rejects stale or unrelated answers.

## Failure

When `ok` is false, use `error.code` for routing and show `error.message` in plain language. Do not retry repeatedly when configuration or user evidence is required.
