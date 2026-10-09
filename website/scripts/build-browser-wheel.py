from __future__ import annotations

import base64
import hashlib
import re
import sys
import zipfile
from pathlib import Path


def main() -> None:
    repository = Path(__file__).resolve().parents[2]
    destination = Path(sys.argv[1]).resolve()
    project = (repository / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version = "([^"]+)"$', project, re.MULTILINE).group(1)
    package = repository / "src" / "slopmeter"
    dist_info = f"slop_meeter-{version}.dist-info"
    members: dict[str, bytes] = {}
    for source in sorted(package.rglob("*")):
        if not source.is_file() or source.suffix in {".pyc", ".pyo"} or "__pycache__" in source.parts:
            continue
        members[(Path("slopmeter") / source.relative_to(package)).as_posix()] = source.read_bytes()
    members[f"{dist_info}/METADATA"] = (
        "Metadata-Version: 2.3\n"
        "Name: slop-meeter\n"
        f"Version: {version}\n"
        "Summary: Evidence-first repository assessment, without the vibes\n"
        "Requires-Python: >=3.11\n\n"
    ).encode()
    members[f"{dist_info}/WHEEL"] = (
        b"Wheel-Version: 1.0\nGenerator: slop-meeter-browser-build\n"
        b"Root-Is-Purelib: true\nTag: py3-none-any\n"
    )
    record_path = f"{dist_info}/RECORD"
    records = []
    for name, contents in sorted(members.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(contents).digest()).rstrip(b"=").decode()
        records.append(f"{name},sha256={digest},{len(contents)}")
    records.append(f"{record_path},,")
    members[record_path] = ("\n".join(records) + "\n").encode()

    destination.parent.mkdir(parents=True, exist_ok=True)
    timestamp = (2026, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as wheel:
        for name, contents in sorted(members.items()):
            info = zipfile.ZipInfo(name, timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            wheel.writestr(info, contents)


if __name__ == "__main__":
    main()
