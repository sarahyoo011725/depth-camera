# RealSense Data Collection Pipeline

Setup + sanity-check scripts for collecting data from two Intel RealSense
depth cameras (D415 + D435) for the GitIRL project's perception module.

## Install

```bash
pip install pyrealsense2 opencv-python numpy
```

## Run these in order

### 1. Confirm both cameras are detected
```bash
python device_check.py --expect 2
```
This lists every connected RealSense device with its serial number. **Copy
the serial numbers down** — you'll need them for every script below. If this
fails or shows the wrong count, fix that before doing anything else (check
USB connections, try different ports).

### 2. Capture one test frame from each camera
Edit `capture_test.py` and fill in `DEFAULT_D415_SERIAL` /
`DEFAULT_D435_SERIAL` with the serials from step 1 (or pass them as flags):
```bash
python capture_test.py --d415-serial <serial> --d435-serial <serial>
```
Check the images saved in `capture_test_output/` — the color image should
look normal, and the depth colormap should show a sensible gradient (not
all black/all noise).

### 3. Live preview (use this while physically mounting cameras)
```bash
python live_preview.py --serial <serial> --name D415
```
Shows a live color + depth window so you can aim/position the camera.
Press `q` to quit. Run again with the D435 serial when repositioning that one.

### 4. Test both cameras running simultaneously
```bash
python dual_stream_test.py --d415-serial <serial> --d435-serial <serial>
```
Checks for USB bandwidth issues when both cameras stream at once. If you see
frequent failures, plug each camera into a **separate USB controller**, not
the same hub — this is the most common issue with 2+ RealSense cameras.

## Files

| File | Purpose |
|---|---|
| `camera.py` | Reusable `RealSenseCamera` class — wraps pipeline setup, alignment, frame capture, point cloud extraction |
| `device_check.py` | Lists connected cameras + serial numbers |
| `capture_test.py` | Grabs one frame per camera, saves images for visual sanity check |
| `live_preview.py` | Live view for physically positioning a camera |
| `dual_stream_test.py` | Confirms both cameras can stream simultaneously without bandwidth issues |

## Using `camera.py` in your own code

```python
from camera import RealSenseCamera

with RealSenseCamera(serial="<your_serial>", name="D415") as cam:
    color_image, depth_image = cam.get_frames()   # numpy arrays
    points = cam.get_point_cloud()                  # Nx3 array, meters, camera frame
    intrinsics = cam.get_intrinsics()                # for pose math (e.g. ArUco)
```

- `color_image`: HxWx3 uint8, BGR
- `depth_image`: HxW uint16, millimeters per pixel
- `points`: Nx3 float32, meters, in **camera frame** (not yet transformed
  to robot/world frame — that transform is a one-time calibration you do
  separately per camera mount position)

## Next steps (not yet in this folder)
- ArUco marker detection on the color frame → feed pixel coords into depth
  for 6-DOF pose estimation
- Camera-to-robot-base extrinsic calibration (one-time, per camera)
- WebSocket server to stream processed pose JSON (not raw frames/point
  clouds) to the rest of the team
