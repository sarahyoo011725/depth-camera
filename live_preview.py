"""
live_preview.py

Live side-by-side view of color + depth colormap for ONE camera at a time.
Use this while physically mounting/aiming your cameras (D415 at the
workspace, D435 at the back) so you can see exactly what each one covers.

Usage:
    python live_preview.py --serial 123456789012 --name D415

Press 'q' to quit.
"""

import argparse

import numpy as np
import cv2

from camera import RealSenseCamera


def main():
    parser = argparse.ArgumentParser(description="Live preview for one RealSense camera.")
    parser.add_argument("--serial", type=str, required=True,
                         help="Camera serial number (from device_check.py)")
    parser.add_argument("--name", type=str, default="camera",
                         help="Label for this camera, e.g. D415 or D435")
    args = parser.parse_args()

    print(f"Starting live preview for {args.name} (serial={args.serial}). Press 'q' to quit.")

    with RealSenseCamera(serial=args.serial, name=args.name) as cam:
        try:
            while True:
                color_image, depth_image = cam.get_frames()
                if color_image is None or depth_image is None:
                    continue

                depth_colormap = cv2.applyColorMap(
                    cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET
                )

                # Make sure both images are the same size before stacking
                if color_image.shape[:2] != depth_colormap.shape[:2]:
                    depth_colormap = cv2.resize(
                        depth_colormap, (color_image.shape[1], color_image.shape[0])
                    )

                combined = np.hstack((color_image, depth_colormap))
                cv2.putText(combined, f"{args.name} -- color | depth  (press q to quit)",
                            (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                cv2.imshow("RealSense Live Preview", combined)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
