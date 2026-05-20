"""Argument parsing for the CLI."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ministats")
    p.add_argument("path", help="path to a CSV file (one numeric column)")
    p.add_argument(
        "--format", choices=["json", "text"], default="json",
        help="output format (default: json)",
    )
    return p
