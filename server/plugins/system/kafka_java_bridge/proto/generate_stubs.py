#!/usr/bin/env python3
"""
Generate Python gRPC stubs from kafka_bridge.proto.

Run this script once after cloning, and again whenever the proto changes.

Prerequisites:
    pip install grpcio-tools

Generated files (written to this directory):
    kafka_bridge_pb2.py       — protobuf message classes
    kafka_bridge_pb2_grpc.py  — gRPC client / server stubs

Usage:
    cd server/plugins/system/kafka_java_bridge
    python proto/generate_stubs.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO_FILE = HERE / "kafka_bridge.proto"


def main() -> None:
    if not PROTO_FILE.exists():
        sys.exit(f"ERROR: proto file not found: {PROTO_FILE}")

    try:
        import grpc_tools  # noqa: F401 — just checking it is importable
    except ImportError:
        sys.exit(
            "ERROR: grpcio-tools is not installed.\n"
            "       Run: pip install grpcio-tools"
        )

    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"--proto_path={HERE}",
        f"--python_out={HERE}",
        f"--grpc_python_out={HERE}",
        str(PROTO_FILE),
    ]

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        sys.exit(f"protoc exited with code {result.returncode}")

    # grpc_tools emits absolute imports; patch to relative for package use
    for stub_file in (HERE / "kafka_bridge_pb2_grpc.py",):
        if stub_file.exists():
            text = stub_file.read_text()
            text = text.replace(
                "import kafka_bridge_pb2 as kafka__bridge__pb2",
                "from . import kafka_bridge_pb2 as kafka__bridge__pb2",
            )
            stub_file.write_text(text)

    print("Done — stubs written to:", HERE)
    print("  kafka_bridge_pb2.py")
    print("  kafka_bridge_pb2_grpc.py")


if __name__ == "__main__":
    main()
