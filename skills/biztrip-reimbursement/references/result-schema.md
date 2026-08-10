# Skill Audit Result Schema

The bundled audit script writes one JSON object using schema `biztrip.skill-audit.v1`.

## Commands

```bash
python <SKILL_DIR>/scripts/audit_mailbox.py status
python <SKILL_DIR>/scripts/audit_mailbox.py setup
python <SKILL_DIR>/scripts/audit_mailbox.py audit --start YYYY-MM-DD --end YYYY-MM-DD
python <SKILL_DIR>/scripts/audit_mailbox.py audit --count 60
```

## Successful audit

- `ok`: `true`.
- `status`: `audit_ready`.
- `scan_label`: Processed date or mail range.
- `summary.candidate_record_count`: Candidate reimbursement emails.
- `summary.amount_known_count`: Candidates with an amount found in email text.
- `summary.candidate_total`: Estimate using the first amount candidate per email.
- `summary.issue_count`: Total detected issues.
- `categories`: Counts and candidate amounts grouped by category.
- `records`: At most 20 summaries with sender hints, subjects, amount candidates, attachment names, bounded body excerpts, and issue codes.
- `records_truncated`: Whether more records were omitted.
- `files.package_dir`: Always empty.
- `files.excel`: Always empty.
- `next_action`: `present_audit`.
- `full_package.requires`: `local_personal_app`.

The host Agent explains these facts but must not silently repair them. This schema intentionally has no answer submission, attachment parsing, or package delivery operation.

## Failure

Use `error.code` for routing and show `error.message` in plain language. `setup_required` means the user must run the bundled local mailbox setup page. A Skill audit never downloads the full engine or requires a separate model API key.
