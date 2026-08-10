---
name: biztrip-reimbursement
description: Organize, verify, and complete business-trip reimbursement packages with the local BizTrip Agent engine. Use when a user asks to scan travel emails, collect invoices or itineraries, organize expenses for a date range, resolve missing reimbursement information, check task progress, or produce a verified reimbursement package.
---

# BizTrip Reimbursement

Use this skill as a thin conversational entry to the local BizTrip Agent engine. Let the engine read mail, parse attachments, validate evidence, calculate totals, and create files. Never reproduce those operations in the model.

## Operating Rules

- Never request, read, print, transmit, or edit email authorization codes, passwords, API keys, or `.env` values.
- Never invent or silently repair an amount, date, vendor, attachment, duplicate decision, or trip assignment.
- Treat engine questions as the only fields the user may confirm.
- Do not claim completion unless the engine returns `status: completed`.
- Do not expose internal records JSON to ordinary users. Report the package directory and Excel path when complete.
- Keep reimbursement evidence local. Do not upload attachments to another service.

## Locate the Engine

Use the first available command:

1. `biztrip`
2. `.venv/bin/biztrip` from a BizTrip Agent checkout
3. `python -m biztrip_agent.cli` from an installed environment

If none is available, run the bundled installer in check mode:

```bash
python <SKILL_DIR>/scripts/install_engine.py --check
```

Resolve `<SKILL_DIR>` from this `SKILL.md` location. Do not assume the user's current working directory.

If it returns `not_installed`, explain that the free local engine will be downloaded from the public BizTrip Agent GitHub repository and installed into the user's local application directory. Ask for permission before downloading or installing anything. After approval, run:

```bash
python <SKILL_DIR>/scripts/install_engine.py
```

Parse its single JSON result and use `engine_command` for all later commands. Never run installation without explicit user approval. Never ask for administrator access, modify the system Python, or replace an existing installation.

If Python is unavailable or below 3.8, show the returned requirement and direct the user to `https://www.python.org/downloads/`. Do not execute an untrusted third-party installer.

## Start a Task

Convert the user's natural-language period into explicit dates. If the period is ambiguous and affects which expenses are included, ask one concise question before running.

Run:

```bash
biztrip agent start --start YYYY-MM-DD --end YYYY-MM-DD
```

When the user explicitly asks for recent mail instead of a date range, run:

```bash
biztrip agent start --count 60
```

Parse stdout as one JSON object. Follow `status` and `next_action`; do not infer success from process text.

If starting the task returns `setup_required` or `task_not_created`, launch the returned engine command with `web`. Tell the user to finish mailbox setup and configure their own OpenAI-compatible model Base URL, API Key, and model name in that local page. Do not collect the mailbox address, authorization code, model URL, or API Key in chat. After the user confirms setup is complete, retry the task once.

## Continue a Task

To inspect a known task:

```bash
biztrip agent status --task TASK_PATH
```

If the task path is unavailable, query the latest local task:

```bash
biztrip agent status
```

Keep `task_path` for the current conversation. Do not make the user handle it.

## Resolve Questions

For `needs_user_input`, ask only the returned questions. Present relevant context and available options in plain language. Preserve the returned `record_index` and `issue_code` internally.

Write confirmed answers to a temporary UTF-8 JSON file:

```json
{
  "answers": [
    {"record_index": 1, "issue_code": "missing_amount", "value": "88.50"}
  ]
}
```

Submit them:

```bash
biztrip agent answer --task TASK_PATH --answers-file ANSWERS_PATH
```

Continue until the engine returns `completed` or no further user-confirmable evidence exists.

If `attachment_requires_web` is true, tell the user the original document must be added through the local BizTrip Web page. Start it with `biztrip web`; never substitute a guessed path or upload the document elsewhere.

## Deliver the Result

For `completed`, report:

- Number of recognized records and trips.
- Verified total amount.
- Package directory.
- Excel path.

For `failed`, explain the returned error message in plain language. If it concerns local setup or mailbox connectivity, direct the user to the local Web setup page. Never ask them to paste secrets into chat.

Read [references/result-schema.md](references/result-schema.md) only when field-level response details are needed.
