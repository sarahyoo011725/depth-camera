"""
device_check.py

Lists all connected RealSense devices with their name and serial number.
Run this FIRST, before anything else, to confirm both cameras are detected
by the OS/SDK. Fails loudly if the expected number of devices isn't found.

Usage:
    python device_check.py
    python device_check.py --expect 2
"""

import argparse
import sys

try:
    import pyrealsense2 as rs
except ImportError as e:
    print("ERROR: pyrealsense2 not found. Install it with:")
    print("    pip install pyrealsense2")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Check connected RealSense devices.")
    parser.add_argument(
        "--expect", type=int, default=None,
        help="Expected number of devices (e.g. 2 for D415 + D435). "
             "If provided, exits with an error code if the count doesn't match."
    )
    args = parser.parse_args()

    ctx = rs.context()
    devices = ctx.query_devices()
    count = len(devices)

    print(f"Found {count} RealSense device(s):\n")

    if count == 0:
        print("  (none)")
        print("\nNo devices found. Things to check:")
        print("  - Are the cameras actually plugged in via USB?")
        print("  - Try a different USB port (prefer USB 3.x, not a hub)")
        print("  - Run 'rs-enumerate-devices' (comes with librealsense) to "
              "check at the SDK level outside Python")
        sys.exit(1)

    for i, dev in enumerate(devices):
        name = dev.get_info(rs.camera_info.name)
        serial = dev.get_info(rs.camera_info.serial_number)
        product_line = dev.get_info(rs.camera_info.product_line) \
            if dev.supports(rs.camera_info.product_line) else "unknown"
        print(f"  [{i}] {name}")
        print(f"      Serial: {serial}")
        print(f"      Product line: {product_line}")
        print()

    if args.expect is not None and count != args.expect:
        print(f"ERROR: expected {args.expect} device(s), found {count}.")
        sys.exit(1)

    print("Copy the serial numbers above into your camera config "
          "(e.g. capture_test.py or a config file) to address each "
          "camera specifically.")


if __name__ == "__main__":
    main()
