#!/usr/bin/env python3
"""Append a single prediction record to predictions.jsonl.

Kept separate from run_harness.sh because mixing shell heredocs with stdin
redirection is fragile — a typed Python script that takes the patch from a
file is the simpler invariant.
"""
import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--iid", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--patch-file", required=True)
    args = p.parse_args()

    patch = Path(args.patch_file).read_text()
    record = {
        "instance_id": args.iid,
        "model_name_or_path": args.model,
        "model_patch": patch,
    }
    json.dump(record, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
