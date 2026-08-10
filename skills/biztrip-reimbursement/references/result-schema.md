# Skill Audit Result Schema

The audit command writes one JSON object using schema `biztrip.audit.v1`.

## Command

```bash
biztrip agent audit --start YYYY-MM-DD --end YYYY-MM-DD
biztrip agent audit --count 60
```

## Successful audit

- `ok`: `true`.
- `operation`: `audit`.
- `status`: `audit_ready`.
- `summary.scan_label`: Processed date or mail range.
- `summary.record_count`: Recognized reimbursement records.
- `summary.trip_count`: Detected trips.
- `summary.total_amount`: Estimated recognized total.
- `summary.complete_record_count`: Records with no detected completeness issue.
- `summary.affected_record_count`: Records affected by at least one issue.
- `summary.issue_count`: Total detected issues.
- `categories`: Counts and amounts grouped by expense category.
- `trips`: Detected trip summaries.
- `records`: A bounded preview of records and issue codes.
- `records_truncated`: Whether additional records were omitted from the response.
- `files.package_dir`: Always empty in Skill audit mode.
- `files.excel`: Always empty in Skill audit mode.
- `next_action`: `present_audit`.
- `full_package.requires`: `local_personal_app`.

The host Agent explains these facts but must not silently repair them. This schema intentionally has no answer submission or package delivery operation.

## Failure

When `ok` is false, use `error.code` for routing and show `error.message` in plain language. `setup_required` means the user must save mailbox details on the local page. A Skill audit never requires a separate model API key.
