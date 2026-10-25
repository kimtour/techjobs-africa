"""Scan Git blobs for high-confidence credential patterns without printing values."""

import argparse
import json
import re
import subprocess

PATTERNS = {
    "github_token": rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})",
    "aws_access_key": rb"(?:AKIA|ASIA)[A-Z0-9]{16}",
    "private_key": rb"-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----",
    "telegram_token": rb"\b[0-9]{8,}:[A-Za-z0-9_-]{30,}\b",
    "slack_token": rb"xox[baprs]-[A-Za-z0-9-]{20,}",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "refs", nargs="+", help="Explicit code refs to publish; exclude private state"
    )
    parser.add_argument("--repository", default=".")
    parser.add_argument("--check-job-content", action="store_true")
    args = parser.parse_args()
    lines = subprocess.check_output(
        ["git", "-C", args.repository, "rev-list", "--objects", *args.refs], text=True
    ).splitlines()
    objects = {line.partition(" ")[0]: line.partition(" ")[2] for line in lines}
    reader = subprocess.Popen(
        ["git", "-C", args.repository, "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    findings, blobs, total = [], 0, 0
    for oid, path in objects.items():
        reader.stdin.write((oid + "\n").encode())
        reader.stdin.flush()
        header = reader.stdout.readline().decode().split()
        data = reader.stdout.read(int(header[2]))
        reader.stdout.read(1)
        if header[1] != "blob":
            continue
        blobs += 1
        total += len(data)
        for name, pattern in PATTERNS.items():
            if re.search(pattern, data):
                findings.append({"kind": name, "object": oid, "path": path})
        if (
            args.check_job_content
            and path.endswith((".json", ".jsonl"))
            and re.search(
                rb'"(?:description|descriptionHtml|descriptionPlain|description_html|'
                rb'recruiter_email|contact_email|access_token|api_key)"\s*:',
                data,
            )
        ):
            findings.append({"kind": "forbidden_persisted_field", "object": oid, "path": path})
    reader.stdin.close()
    reader.wait()
    print(
        json.dumps({"blobs_scanned": blobs, "bytes_scanned": total, "findings": findings}, indent=2)
    )
    raise SystemExit(bool(findings))


if __name__ == "__main__":
    main()
