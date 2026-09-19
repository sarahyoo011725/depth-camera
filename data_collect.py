"""
data_collect.py

Data collection tool for Person A (perception). Captures synchronized
color + depth + point cloud data from BOTH cameras (D415 + D435) and
saves everything to disk in an organized, timestamped session folder.

Two modes:
  - Manual capture: press SPACE to save a snapshot, 'q' to quit
  - Continuous capture: automatically saves a snapshot every N seconds

Each capture saves, per camera:
  - <cam>_color.png           -- RGB image
  - <cam>_depth_raw.npy        -- raw depth in millimeters (uint16)
  - <cam>_depth_colormap.png   -- visualized depth (for quick viewing)
  - <cam>_pointcloud.npy       -- Nx3 point cloud in meters, camera frame
  - metadata.json              -- timestamp, capture index, camera serials

Usage:
    # Manual mode (default) -- press SPACE to capture, q to quit
    python data_collect.py --d415-serial <serial> --d435-serial <serial>

    # Continuous mode -- auto-capture every 2 seconds
    python data_collect.py --d415-serial <serial> --d435-serial <serial> --auto --interval 2.0

    # Custom output location / session name
    python data_collect.py --d415-serial <serial> --d435-serial <serial> --out data/session1
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import numpy as np
import cv2

from camera import RealSenseCamera

DEFAULT_D415_SERIAL = "REPLACE_WITH_D415_SERIAL"
DEFAULT_D435_SERIAL = "REPLACE_WITH_D435_SERIAL"


def make_session_dir(base_out: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(base_out, f"session_{timestamp}")
    os.makedirs(session_dir, exist_ok=True)
    return session_dir


def save_capture(session_dir: str, capture_idx: int, cam_name: str,
                  color_image, depth_image, points):
    """Saves one camera's data for a single capture index."""
    capture_dir = os.path.join(session_dir, f"capture_{capture_idx:04d}")
    os.makedirs(capture_dir, exist_ok=True)

    color_path = os.path.join(capture_dir, f"{cam_name.lower()}_color.png")
    depth_raw_path = os.path.join(capture_dir, f"{cam_name.lower()}_depth_raw.npy")
    depth_colormap_path = os.path.join(capture_dir, f"{cam_name.lower()}_depth_colormap.png")
    pointcloud_path = os.path.join(capture_dir, f"{cam_name.lower()}_pointcloud.npy")

    cv2.imwrite(color_path, color_image)
    np.save(depth_raw_path, depth_image)

    depth_colormap = cv2.applyColorMap(
        cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET
    )
    cv2.imwrite(depth_colormap_path, depth_colormap)

    if points is not None:
        np.save(pointcloud_path, points)

    return capture_dir


def run(d415_serial, d435_serial, out_base, auto, interval):
    session_dir = make_session_dir(out_base)
    print(f"Session folder: {session_dir}\n")

    cam_d415 = RealSenseCamera(serial=d415_serial, name="D415")
    cam_d435 = RealSenseCamera(serial=d435_serial, name="D435")

    print("Starting cameras...")
    cam_d415.start()
    cam_d435.start()

    if auto:
        print(f"AUTO mode: capturing every {interval:.1f}s. Ctrl+C to stop.\n")
    else:
        print("MANUAL mode: press SPACE (in the preview window) to capture, "
              "'q' to quit.\n")

    capture_idx = 0
    all_metadata = []
    last_capture_time = 0.0

    try:
        while True:
            color_d415, depth_d415 = cam_d415.get_frames()
            color_d435, depth_d435 = cam_d435.get_frames()

            if color_d415 is None or color_d435 is None:
                print("Warning: dropped frame, retrying...")
                continue

            # Live preview so you can see what you're about to capture
            preview_d415 = cv2.resize(color_d415, (320, 240))
            preview_d435 = cv2.resize(color_d435, (320, 240))
            preview = np.hstack((preview_d415, preview_d435))
            cv2.putText(preview, f"D415 | D435   captures: {capture_idx}",
                        (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            if not auto:
                cv2.putText(preview, "SPACE = capture, q = quit",
                            (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.imshow("Data Collection Preview", preview)

            key = cv2.waitKey(1) & 0xFF

            should_capture = False
            if auto:
                if time.time() - last_capture_time >= interval:
                    should_capture = True
            else:
                if key == ord(' '):
                    should_capture = True

            if key == ord('q'):
                break

            if should_capture:
                points_d415 = cam_d415.get_point_cloud()
                points_d435 = cam_d435.get_point_cloud()

                dir_d415 = save_capture(session_dir, capture_idx, "D415",
                                         color_d415, depth_d415, points_d415)
                save_capture(session_dir, capture_idx, "D435",
                             color_d435, depth_d435, points_d435)

                metadata = {
                    "capture_idx": capture_idx,
                    "timestamp": time.time(),
                    "d415_serial": d415_serial,
                    "d435_serial": d435_serial,
                }
                all_metadata.append(metadata)

                print(f"  [capture {capture_idx:04d}] saved -> "
                      f"{os.path.basename(os.path.dirname(dir_d415))}/"
                      f"{os.path.basename(dir_d415)}")

                capture_idx += 1
                last_capture_time = time.time()

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        cam_d415.stop()
        cam_d435.stop()
        cv2.destroyAllWindows()

        metadata_path = os.path.join(session_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump({
                "session_dir": session_dir,
                "total_captures": capture_idx,
                "d415_serial": d415_serial,
                "d435_serial": d435_serial,
                "captures": all_metadata,
            }, f, indent=2)

        print(f"\nDone. {capture_idx} capture(s) saved to: {session_dir}")
        print(f"Metadata written to: {metadata_path}")


def main():
    parser = argparse.ArgumentParser(description="Collect synchronized data from both cameras.")
    parser.add_argument("--d415-serial", type=str, default=DEFAULT_D415_SERIAL)
    parser.add_argument("--d435-serial", type=str, default=DEFAULT_D435_SERIAL)
    parser.add_argument("--out", type=str, default="data",
                         help="Base output directory (a timestamped session folder is created inside it)")
    parser.add_argument("--auto", action="store_true",
                         help="Auto-capture on an interval instead of manual SPACE press")
    parser.add_argument("--interval", type=float, default=2.0,
                         help="Seconds between captures in --auto mode")
    args = parser.parse_args()

    if args.d415_serial.startswith("REPLACE_WITH") or args.d435_serial.startswith("REPLACE_WITH"):
        print("ERROR: set both serial numbers (edit this file's defaults, "
              "or pass --d415-serial / --d435-serial). Run device_check.py "
              "first to get them.")
        sys.exit(1)

    run(args.d415_serial, args.d435_serial, args.out, args.auto, args.interval)


if __name__ == "__main__":
    main()