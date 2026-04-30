#!/usr/bin/env python3
"""Push exported catalog JSON files to Cloudflare R2.

Exports catalog markdown to JSON, then uploads all files under the
``pindata/`` prefix using boto3 (S3-compatible API).  The same
R2 bucket holds raw ingest sources (IPDB, OPDB, etc.) at the root, so
the prefix keeps catalog exports separate.

Writes its own manifest at ``pindata/manifest.json``.  The
root-level ``manifest.json`` is owned by pinexplore's push script and
covers only non-prefixed ingest source files.

Usage:
    python scripts/push_to_r2.py [--skip-export]

Requires R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET
in environment or .env.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")
EXPORT_DIR = REPO_ROOT / "export"
EXCLUDE = {
    "manifest.json",
    ".DS_Store",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_files(src: Path) -> list[dict]:
    """Walk src and return manifest entries, excluding dotfiles and stale files."""
    entries = []
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.startswith(".") or f in EXCLUDE:
                continue
            full = Path(root) / f
            rel = full.relative_to(src).as_posix()
            entries.append(
                {
                    "path": rel,
                    "size": full.stat().st_size,
                    "sha256": _sha256(full),
                }
            )
    entries.sort(key=lambda e: e["path"])
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Push catalog exports to R2.")
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Skip regenerating exports (use existing files).",
    )
    args = parser.parse_args()

    try:
        import boto3
    except ImportError:
        print("ERROR: boto3 is required. pip install boto3", file=sys.stderr)
        return 1

    # Validate env vars
    account_id = os.environ.get("R2_ACCOUNT_ID")
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")
    bucket = os.environ.get("R2_BUCKET")

    missing = [
        name
        for name, val in [
            ("R2_ACCOUNT_ID", account_id),
            ("R2_ACCESS_KEY_ID", access_key),
            ("R2_SECRET_ACCESS_KEY", secret_key),
            ("R2_BUCKET", bucket),
        ]
        if not val
    ]
    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}", file=sys.stderr)
        return 1

    # Step 1: Export catalog to JSON
    if not args.skip_export:
        print("Exporting catalog to JSON...")
        export_script = REPO_ROOT / "scripts" / "export_catalog_json.py"
        result = subprocess.run([sys.executable, str(export_script)])
        if result.returncode != 0:
            print("ERROR: export_catalog_json.py failed", file=sys.stderr)
            return 1

    # Step 2: Build manifest
    print("Building manifest...")
    entries = _collect_files(EXPORT_DIR)
    manifest_path = EXPORT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"  {len(entries)} files in manifest")

    # Step 3: Upload to R2 under pindata/ prefix
    print("Uploading to R2...")
    endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    # Upload files first, manifest last
    uploaded = 0
    skipped = 0
    for entry in entries:
        local_path = EXPORT_DIR / entry["path"]
        key = f"pindata/{entry['path']}"

        # Skip if remote file matches size AND content hash.
        try:
            head = s3.head_object(Bucket=bucket, Key=key)
            remote_size = head["ContentLength"]
            remote_etag = head["ETag"].strip('"')
            local_md5 = hashlib.md5(local_path.read_bytes()).hexdigest()
            if remote_size == entry["size"] and remote_etag == local_md5:
                skipped += 1
                continue
        except s3.exceptions.ClientError:
            pass  # File doesn't exist remotely yet

        print(f"  {key}")
        s3.upload_file(str(local_path), bucket, key)
        uploaded += 1

    # Upload manifest last so consumers never see stale references
    s3.upload_file(str(manifest_path), bucket, "pindata/manifest.json")

    print(f"Done. {uploaded} uploaded, {skipped} unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
