"""Find an unlinked reimbursement attachment using deterministic evidence."""

import re
import zipfile
from io import BytesIO
from pathlib import Path


SUPPORTED_SUFFIXES = {".pdf", ".zip", ".jpg", ".jpeg", ".png", ".heic"}
IDENTIFIER_FIELDS = ("订单号", "发票号码", "发票号")


def find_unlinked_attachment(record, records, attachment_dir):
    """Return one uniquely supported attachment candidate, otherwise None."""
    attachment_dir = Path(attachment_dir)
    if not attachment_dir.exists():
        return None
    used = {
        name.strip()
        for item in records
        for name in str(item.get("附件", "") or "").split(";")
        if name.strip()
    }
    candidates = []
    for path in attachment_dir.iterdir():
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES or path.name in used:
            continue
        evidence = f"{path.name}\n{_attachment_text(path)}"
        match = _match_evidence(record, evidence)
        if match:
            candidates.append({"attachment": path.name, **match})
    if not candidates:
        return None
    candidates.sort(key=lambda item: item["score"], reverse=True)
    if len(candidates) > 1 and candidates[0]["score"] == candidates[1]["score"]:
        return None
    return candidates[0]


def _match_evidence(record, evidence):
    normalized = evidence.lower()
    signals = []
    identifier_match = False
    for field in IDENTIFIER_FIELDS:
        value = str(record.get(field, "") or "").strip()
        if len(value) >= 4 and value.lower() in normalized:
            signals.append(field)
            identifier_match = True
            break

    amount_match = _amount_matches(record.get("金额"), evidence)
    date_match = _date_matches(record.get("日期"), evidence)
    vendor_match = _vendor_matches(record, normalized)
    if amount_match:
        signals.append("金额")
    if date_match:
        signals.append("日期")
    if vendor_match:
        signals.append("供应商")

    if not identifier_match and not (amount_match and date_match and vendor_match):
        return None
    return {
        "score": 10 if identifier_match else len(signals),
        "signals": signals,
        "source": "archived_attachment",
    }


def _amount_matches(value, evidence):
    try:
        expected = round(float(value), 2)
    except (TypeError, ValueError):
        return False
    numbers = re.findall(r"(?<!\d)(\d{1,9}(?:\.\d{1,2})?)(?!\d)", evidence)
    return any(round(float(number), 2) == expected for number in numbers)


def _date_matches(value, evidence):
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(value or ""))
    if not match:
        return False
    expected = tuple(int(part) for part in match.groups())
    for found in re.finditer(r"(\d{4})\D{0,3}(\d{1,2})\D{0,3}(\d{1,2})", evidence):
        if tuple(int(part) for part in found.groups()) == expected:
            return True
    return False


def _vendor_matches(record, normalized_evidence):
    vendor = record.get("供应商") or record.get("平台") or record.get("酒店名称")
    vendor = str(vendor or "").strip().lower()
    return len(vendor) >= 2 and vendor in normalized_evidence


def _attachment_text(path):
    try:
        if path.suffix.lower() == ".pdf":
            return _pdf_text(path.read_bytes())
        if path.suffix.lower() == ".zip":
            texts = []
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    if info.filename.lower().endswith(".pdf") and info.file_size <= 10 * 1024 * 1024:
                        texts.append(_pdf_text(archive.read(info)))
            return "\n".join(texts)
    except (OSError, zipfile.BadZipFile):
        return ""
    return ""


def _pdf_text(data):
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""
