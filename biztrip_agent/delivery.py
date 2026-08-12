"""Create the minimal user-facing reimbursement package."""

import shutil
from pathlib import Path

from biztrip_agent.results import output_label, output_timestamp
from biztrip_agent.validation import validate_reimbursement


def create_delivery_package(records, trips, output_dir, attachment_dir, scan_label, use_llm):
    """Create one package containing only the Excel report and referenced originals."""
    validation = validate_reimbursement(records, trips, attachment_dir=attachment_dir)
    if not validation["can_submit"]:
        raise ValueError("报销材料尚未通过质量核验，不能生成最终报销包。")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = _unique_package_dir(output_dir, scan_label)
    originals_dir = package_dir / "原件"
    package_dir.mkdir()
    originals_dir.mkdir()
    try:
        from phase2.agent_report import _generate_excel

        total = sum(record.get("金额", 0) or 0 for record in records)
        excel_path = _generate_excel(
            records,
            trips,
            total,
            scan_label,
            output_dir=str(package_dir),
            use_llm=use_llm,
        )
        copied = _copy_referenced_originals(records, Path(attachment_dir), originals_dir)
    except Exception:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise
    return {
        "package_dir": package_dir,
        "excel_path": Path(excel_path),
        "originals": copied,
    }


def _unique_package_dir(output_dir, scan_label):
    base = output_dir / f"报销包_{output_label(scan_label)}_{output_timestamp()}"
    candidate = base
    index = 1
    while candidate.exists():
        candidate = output_dir / f"{base.name}_{index}"
        index += 1
    return candidate


def _copy_referenced_originals(records, attachment_dir, originals_dir):
    names = []
    for record in records:
        for raw_name in str(record.get("附件", "") or "").split(";"):
            name = raw_name.strip()
            if name and name not in names:
                names.append(name)
    copied = []
    for name in names:
        source = attachment_dir / name
        destination = originals_dir / name
        shutil.copy2(source, destination)
        copied.append(destination)
    return copied
