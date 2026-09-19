"""
capture_test.py

Sanity-check script: opens each configured camera, grabs ONE frame, and
saves color + depth images to disk so you can visually confirm both
cameras are working correctly.

Fill in your camera serial numbers below (get them from device_check.py),
or pass them as CLI args.

Usage:
    python capture_test.py
    python capture_test.py --d415-serial 123456789012 --d435-serial 987654321098
"""

import argparse
import sys
import os

import numpy as np
import cv2

from camera import RealSenseCamera

# ---- EDIT THESE with your actual serial numbers from device_check.py ----
DEFAULT_D415_SERIAL = "REPLACE_WITH_D415_SERIAL"
DEFAULT_D435_SERIAL = "REPLACE_WITH_D435_SERIAL"
# ---------------------------------------------------------------------

OUTPUT_DIR = "capture_test_output"


def capture_and_save(serial: str, name: str):
    print(f"\n--- Testing {name} (serial={serial}) ---")

    if serial.startswith("REPLACE_WITH"):
        print(f"[{name}] SKIPPED: serial number not set. Edit capture_test.py "
              f"or pass --{'d415' if 'D415' in name else 'd435'}-serial.")
        return False

    try:
        with RealSenseCamera(serial=serial, name=name) as cam:
            color_image, depth_image = cam.get_frames()

            if color_image is None or depth_image is None:
                print(f"[{name}] FAILED: could not capture a frame.")
                return False

            os.makedirs(OUTPUT_DIR, exist_ok=True)

            color_path = os.path.join(OUTPUT_DIR, f"{name.lower()}_color.png")
            depth_colormap_path = os.path.join(OUTPUT_DIR, f"{name.lower()}_depth_colormap.png")
            depth_raw_path = os.path.join(OUTPUT_DIR, f"{name.lower()}_depth_raw.npy")

            cv2.imwrite(color_path, color_image)

            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET
            )
            cv2.imwrite(depth_colormap_path, depth_colormap)
            np.save(depth_raw_path, depth_image)

            # Basic sanity stats
            valid_depth = depth_image[depth_image > 0]
            if len(valid_depth) > 0:
                mean_mm = float(np.mean(valid_depth))
                print(f"[{name}] Mean valid depth: {mean_mm:.1f} mm "
                      f"({mean_mm / 1000:.2f} m)")
            else:
                print(f"[{name}] WARNING: no valid depth pixels found "
                      f"(all zero) -- check for reflective/dark surfaces "
                      f"or out-of-range distance.")

            print(f"[{name}] SUCCESS. Saved:")
            print(f"    {color_path}")
            print(f"    {depth_colormap_path}")
            print(f"    {depth_raw_path}")
            return True

    except Exception as e:
        print(f"[{name}] FAILED with error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Capture test frames from both cameras.")
    parser.add_argument("--d415-serial", type=str, default=DEFAULT_D415_SERIAL)
    parser.add_argument("--d435-serial", type=str, default=DEFAULT_D435_SERIAL)
    args = parser.parse_args()

    results = {}
    results["D415"] = capture_and_save(args.d415_serial, "D415")
    results["D435"] = capture_and_save(args.d435_serial, "D435")

    print("\n=== Summary ===")
    for name, ok in results.items():
        status = "OK" if ok else "FAILED / SKIPPED"
        print(f"  {name}: {status}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
