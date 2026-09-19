"""
camera.py

Reusable wrapper around a single RealSense camera (D415, D435, etc).
Handles pipeline setup, depth-to-color alignment, frame capture, and
point cloud extraction. Use as a context manager so start/stop is
always handled cleanly.

Example:
    with RealSenseCamera(serial="123456789012", name="D415") as cam:
        color, depth = cam.get_frames()
        points = cam.get_point_cloud()
"""

import numpy as np

try:
    import pyrealsense2 as rs
except ImportError as e:
    raise ImportError(
        "pyrealsense2 not found. Install it with: pip install pyrealsense2"
    ) from e


class RealSenseCamera:
    def __init__(self, serial: str, name: str = "camera",
                 width: int = 640, height: int = 480, fps: int = 30):
        """
        serial: the camera's serial number (from device_check.py)
        name:   a human-readable label, used in logs/filenames (e.g. "D415")
        """
        self.serial = serial
        self.name = name
        self.width = width
        self.height = height
        self.fps = fps

        self.pipeline = None
        self.config = None
        self.align = None
        self.profile = None
        self._started = False

    def start(self):
        if self._started:
            print(f"[{self.name}] Already started, skipping.")
            return

        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_device(self.serial)
        self.config.enable_stream(rs.stream.depth, self.width, self.height,
                                   rs.format.z16, self.fps)
        self.config.enable_stream(rs.stream.color, self.width, self.height,
                                   rs.format.bgr8, self.fps)

        try:
            self.profile = self.pipeline.start(self.config)
        except RuntimeError as e:
            raise RuntimeError(
                f"[{self.name}] Failed to start camera (serial={self.serial}). "
                f"Is it plugged in and not in use by another process? "
                f"Original error: {e}"
            ) from e

        # Always align depth to color -- otherwise depth pixel (x,y) does
        # NOT correspond to color pixel (x,y), and object masks won't line
        # up with the correct depth values.
        self.align = rs.align(rs.stream.color)

        self._started = True
        print(f"[{self.name}] Started (serial={self.serial}).")

    def stop(self):
        if self._started and self.pipeline is not None:
            self.pipeline.stop()
            self._started = False
            print(f"[{self.name}] Stopped.")

    def get_frames(self, timeout_ms: int = 5000):
        """
        Grabs one aligned color+depth frame pair.
        Returns (color_image, depth_image) as numpy arrays, or (None, None)
        if a frame couldn't be captured.

        color_image: HxWx3 uint8 (BGR)
        depth_image: HxW uint16 (millimeters per pixel)
        """
        if not self._started:
            raise RuntimeError(f"[{self.name}] Camera not started. Call start() first.")

        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=timeout_ms)
        except RuntimeError as e:
            print(f"[{self.name}] Frame wait timed out or failed: {e}")
            return None, None

        aligned_frames = self.align.process(frames)
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()

        if not depth_frame or not color_frame:
            print(f"[{self.name}] Got incomplete frame set (missing depth or color).")
            return None, None

        color_image = np.asanyarray(color_frame.get_data())
        depth_image = np.asanyarray(depth_frame.get_data())

        # Keep raw rs frame objects available for point cloud extraction
        self._last_color_frame = color_frame
        self._last_depth_frame = depth_frame

        return color_image, depth_image

    def get_point_cloud(self):
        """
        Extracts a 3D point cloud from the most recently captured frames
        (call get_frames() first). Returns an Nx3 numpy array of (x, y, z)
        in meters, in CAMERA FRAME (not yet transformed to world/robot frame).
        """
        if not hasattr(self, "_last_depth_frame") or self._last_depth_frame is None:
            raise RuntimeError(
                f"[{self.name}] No frame captured yet. Call get_frames() first."
            )

        pc = rs.pointcloud()
        pc.map_to(self._last_color_frame)
        points = pc.calculate(self._last_depth_frame)

        vtx = np.asanyarray(points.get_vertices()).view(np.float32).reshape(-1, 3)
        return vtx

    def get_intrinsics(self):
        """Returns the color stream's camera intrinsics (needed for pose math,
        e.g. cv2.aruco.estimatePoseSingleMarkers)."""
        if self.profile is None:
            raise RuntimeError(f"[{self.name}] Camera not started.")
        color_stream = self.profile.get_stream(rs.stream.color)
        intrinsics = color_stream.as_video_stream_profile().get_intrinsics()
        return intrinsics

    # Context manager support
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
