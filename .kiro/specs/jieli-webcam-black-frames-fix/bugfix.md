# Bugfix Requirements Document

## Introduction

This document specifies the requirements for fixing corrupted and black video frames from the Jieli "Webcam HD Full" 1080p USB camera in the web_remote_control.py interface. The current implementation uses ffmpeg subprocess calls per frame, resulting in black frames, partial JPEG corruption (green bottom halves), V4L2 timeout errors, and extremely slow frame rates (~0.5fps). The fix must deliver clean, complete webcam frames at a reasonable frame rate (5-10fps minimum) while preserving all other system functionality.

## Bug Analysis

### Current Behavior (Defect)

**Section 1: Camera Frame Capture Issues**

1.1 WHEN get_camera_frame() is called with the Jieli USB webcam THEN the system produces completely black frames with mean pixel value < 1.0

1.2 WHEN get_camera_frame() executes ffmpeg subprocess with '-frames:v 3' THEN the system displays partial JPEG frames with green corruption in the bottom half of the image

1.3 WHEN ffmpeg captures frames from /dev/video0 THEN the system logs "VIDEOIO(V4L2:/dev/video0): select() timeout" errors

1.4 WHEN ffmpeg subprocess writes to /tmp/cam_frame.jpg followed by cv2.imread() THEN the system achieves only ~0.5fps frame rate due to process spawn overhead

1.5 WHEN ffmpeg runs with default V4L2 backend on Jieli chipset THEN the system encounters "cannot get freq at ep 0x82" USB endpoint errors

### Expected Behavior (Correct)

**Section 2: Fixed Camera Frame Capture**

2.1 WHEN get_camera_frame() is called with the Jieli USB webcam THEN the system SHALL return complete, non-corrupted JPEG frames with valid pixel data (mean > 1.0)

2.2 WHEN the camera capture system processes frames THEN the system SHALL produce frames without green corruption or partial JPEG artifacts

2.3 WHEN the camera system interfaces with /dev/video0 THEN the system SHALL NOT log V4L2 timeout errors during normal operation

2.4 WHEN the web interface requests video frames THEN the system SHALL deliver frames at a minimum of 5fps and target 10fps for real-time monitoring

2.5 WHEN the camera capture system initializes THEN the system SHALL use a capture method compatible with Jieli chipset V4L2 limitations (e.g., YUYV format conversion, continuous capture stream, or alternative backend)

### Unchanged Behavior (Regression Prevention)

**Section 3: Preserved System Functionality**

3.1 WHEN the thermal camera (MLX90640) captures frames THEN the system SHALL CONTINUE TO display thermal heatmaps with crack detection overlays at 4Hz refresh rate

3.2 WHEN get_camera_frame() overlays distance information with cv2.putText() THEN the system SHALL CONTINUE TO display "Dist: X cm" text on RGB frames

3.3 WHEN camera is unavailable or returns None THEN the system SHALL CONTINUE TO return cached frames or None without crashing the web interface

3.4 WHEN generate_rgb_frames() yields frames via Flask Response THEN the system SHALL CONTINUE TO use multipart/x-mixed-replace MJPEG streaming format

3.5 WHEN init_camera() is called and camera initialization fails THEN the system SHALL CONTINUE TO set camera=None and return False without affecting other system components

3.6 WHEN web_remote_control.py runs on port 5000 THEN the system SHALL CONTINUE TO serve the HTML interface with joystick controls, thermal view, and activity logs

3.7 WHEN frame_lock threading.Lock() protects current_rgb_frame THEN the system SHALL CONTINUE TO prevent race conditions during concurrent frame access

3.8 WHEN _cam_lock prevents concurrent camera access THEN the system SHALL CONTINUE TO return cached frames if another capture is in progress
