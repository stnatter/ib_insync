#!/usr/bin/env python3
"""
Generate ib_insync/protobuf/*_pb2.py from IBKR's official .proto files.

Usage:
    python scripts/generate_proto.py <path-to-twsapi>/IBJts/source/proto

The proto directory ships with the TWS API download from IBKR:
  https://www.interactivebrokers.com/en/trading/ib-api.php
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROTO_OUT = Path(__file__).parent.parent / "ib_insync" / "protobuf"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("proto_dir", help="Path to the directory containing IBKR's .proto files")
    args = parser.parse_args()

    proto_dir = Path(args.proto_dir).resolve()
    if not proto_dir.is_dir():
        sys.exit(f"Error: {proto_dir} is not a directory")

    proto_files = sorted(proto_dir.glob("*.proto"))
    if not proto_files:
        sys.exit(f"Error: no .proto files found in {proto_dir}")

    PROTO_OUT.mkdir(parents=True, exist_ok=True)

    print(f"Generating {len(proto_files)} proto files → {PROTO_OUT}")
    result = subprocess.run(
        [
            "protoc",
            f"--proto_path={proto_dir}",
            f"--python_out={PROTO_OUT}",
            *[str(f) for f in proto_files],
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        sys.exit(f"protoc failed:\n{result.stderr}")

    # Rewrite bare inter-module imports to package-qualified ones.
    # protoc generates `import X_pb2 as X__pb2` but we need
    # `from ib_insync.protobuf import X_pb2 as X__pb2`.
    import re
    pattern = re.compile(r'^import (\w+_pb2) as (\w+)$', re.MULTILINE)
    for pb2 in PROTO_OUT.glob("*_pb2.py"):
        text = pb2.read_text()
        rewritten = pattern.sub(r'from ib_insync.protobuf import \1 as \2', text)
        if rewritten != text:
            pb2.write_text(rewritten)

    # Write __init__.py
    (PROTO_OUT / "__init__.py").write_text("")

    count = len(list(PROTO_OUT.glob("*_pb2.py")))
    print(f"Done. {count} files written to {PROTO_OUT}")


if __name__ == "__main__":
    main()
