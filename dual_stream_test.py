"""
dual_stream_test.py

Runs BOTH cameras simultaneously for ~10 seconds, capturing frames from
each in a loop and printing timestamps. This is a bandwidth/stability
check: if running both cameras at once causes dropped frames, USB errors,
or a crash, you likely need to split them across separate USB controllers
(not the same hub).

Usage:
    python dual_stream_test.py --d415-serial 123456789012 --d435-serial 987654321098
    python dual_stream_test.py --duration 15
"""

import argparse
import time
import sys

from camera import RealSenseCamera

DEFAULT_D415_SERIAL = "REPLACE_WITH_D415_SERIAL"
DEFAULT_D435_SERIAL = "REPLACE_WITH_D435_SERIAL"


def main():
    parser = argparse.ArgumentParser(description="Test both cameras streaming simultaneously.")
    parser.add_argument("--d415-serial", type=str, default=DEFAULT_D415_SERIAL)
    parser.add_argument("--d435-serial", type=str, default=DEFAULT_D435_SERIAL)
    parser.add_argument("--duration", type=float, default=10.0,
                         help="How many seconds to run the test for.")
    args = parser.parse_args()

    if args.d415_serial.startswith("REPLACE_WITH") or args.d435_serial.startswith("REPLACE_WITH"):
        print("ERROR: set both serial numbers (edit this file, or pass "
              "--d415-serial / --d435-serial). Run device_check.py first "
              "to get them.")
        sys.exit(1)

    cam_d415 = RealSenseCamera(serial=args.d415_serial, name="D415")
    cam_d435 = RealSenseCamera(serial=args.d435_serial, name="D435")

    print("Starting both cameras...")
    try:
        cam_d415.start()
    except Exception as e:
        print(f"FAILED to start D415: {e}")
        sys.exit(1)

    try:
        cam_d435.start()
    except Exception as e:
        print(f"FAILED to start D435: {e}")
        print("(This is often a USB bandwidth issue -- try separate USB "
              "controllers/ports, not the same hub.)")
        cam_d415.stop()
        sys.exit(1)

    print(f"\nBoth cameras started. Streaming for {args.duration:.0f} seconds...\n")

    frame_counts = {"D415": 0, "D435": 0}
    fail_counts = {"D415": 0, "D435": 0}
    start_time = time.time()

    try:
        while time.time() - start_time < args.duration:
            for cam, key in [(cam_d415, "D415"), (cam_d435, "D435")]:
                color, depth = cam.get_frames(timeout_ms=2000)
                if color is None:
                    fail_counts[key] += 1
                else:
                    frame_counts[key] += 1

            elapsed = time.time() - start_time
            print(f"\r  t={elapsed:5.1f}s  D415 frames={frame_counts['D415']:4d} "
                  f"(fails={fail_counts['D415']})   "
                  f"D435 frames={frame_counts['D435']:4d} (fails={fail_counts['D435']})",
                  end="", flush=True)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        print("\n\nStopping cameras...")
        cam_d415.stop()
        cam_d435.stop()

    print("\n=== Result ===")
    for key in ["D415", "D435"]:
        total = frame_counts[key] + fail_counts[key]
        rate = (frame_counts[key] / total * 100) if total > 0 else 0
        print(f"  {key}: {frame_counts[key]} ok / {fail_counts[key]} failed "
              f"({rate:.1f}% success)")

    if any(fail_counts.values()):
        print("\nSome frames failed. If failures are frequent, this points "
              "to a USB bandwidth issue -- try separate USB controllers "
              "for each camera, or lower resolution/fps.")
    else:
        print("\nBoth cameras streamed cleanly with no dropped frames.")


if __name__ == "__main__":
    main()
