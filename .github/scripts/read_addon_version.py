#!/usr/bin/env python3
"""Print addon version from addon.xml."""

import argparse
import sys
import xml.etree.ElementTree as ET


def main() -> int:
    parser = argparse.ArgumentParser(description="Read addon version from addon.xml")
    parser.add_argument(
        "--addon-xml",
        default="addon.xml",
        help="Path to addon.xml (default: addon.xml)",
    )
    args = parser.parse_args()

    try:
        root = ET.parse(args.addon_xml).getroot()
    except (OSError, ET.ParseError) as exc:
        print(f"Failed to read {args.addon_xml}: {exc}", file=sys.stderr)
        return 1

    version = root.attrib.get("version")
    if not version:
        print(f"Missing 'version' attribute in {args.addon_xml}", file=sys.stderr)
        return 1

    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
