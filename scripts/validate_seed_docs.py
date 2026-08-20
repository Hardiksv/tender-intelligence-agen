#!/usr/bin/env python3
"""
Validates every file in data/raw/ is a genuine PDF (starts with %PDF- magic bytes),
not an HTML page (404/homepage) saved with a .pdf extension by a scraper that never
checked its own output.

Usage:
    python scripts/validate_seed_docs.py [path/to/data/raw]

Exit code 0 = all files are real PDFs. Exit code 1 = at least one file is bad
(details printed to stdout).
"""
import sys
from pathlib import Path

PDF_MAGIC = b"%PDF-"


def check_file(path: Path) -> str | None:
    """Returns an error string if the file is not a real PDF, else None."""
    try:
        with open(path, "rb") as f:
            header = f.read(1024).lstrip(b"\xef\xbb\xbf")
    except Exception as e:
        return f"could not read file: {e}"

    if not header.startswith(PDF_MAGIC):
        preview = header[:120].decode("utf-8", errors="replace").strip().replace("\n", " ")
        kind = "HTML" if header.lstrip().lower().startswith((b"<!doctype", b"<html")) else "unknown/non-PDF"
        return f"NOT A REAL PDF ({kind}) — first bytes: {preview!r}"
    return None


def main() -> int:
    raw_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/raw")
    if not raw_dir.exists():
        print(f"Directory not found: {raw_dir}")
        return 1

    pdf_files = sorted(raw_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No .pdf files found in {raw_dir}")
        return 1

    bad = []
    for f in pdf_files:
        err = check_file(f)
        status = "OK" if err is None else "FAIL"
        print(f"[{status}] {f.name}")
        if err:
            print(f"        -> {err}")
            bad.append(f.name)

    print()
    print(f"{len(pdf_files) - len(bad)}/{len(pdf_files)} files are genuine PDFs.")
    if bad:
        print(f"BROKEN FILES ({len(bad)}): {', '.join(bad)}")
        print("Re-download these from the original source portal before submitting.")
        return 1

    print("All seed documents validated as real PDFs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())