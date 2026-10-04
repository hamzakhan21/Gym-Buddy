"""
pose_utils.py
Small helpers around MediaPipe Pose: mapping generic joint names ("SHOULDER",
"ELBOW", ...) to left/right landmarks, pixel-coordinate conversion, the
arctan2-based joint-angle calculation, and visibility scoring used to pick
the more clearly-visible arm.
"""

import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose

# Maps a generic joint name to the actual MediaPipe landmark for a given side.
# Add joints here (e.g. 'KNEE', 'ANKLE') if you extend to lower-body exercises.
_JOINT_NAME_TO_LANDMARK = {
    'LEFT': {
        'SHOULDER': mp_pose.PoseLandmark.LEFT_SHOULDER,
        'ELBOW': mp_pose.PoseLandmark.LEFT_ELBOW,
        'WRIST': mp_pose.PoseLandmark.LEFT_WRIST,
        'HIP': mp_pose.PoseLandmark.LEFT_HIP,
    },
    'RIGHT': {
        'SHOULDER': mp_pose.PoseLandmark.RIGHT_SHOULDER,
        'ELBOW': mp_pose.PoseLandmark.RIGHT_ELBOW,
        'WRIST': mp_pose.PoseLandmark.RIGHT_WRIST,
        'HIP': mp_pose.PoseLandmark.RIGHT_HIP,
    },
}


def get_landmark(landmarks, side, joint_name):
    """Return the mediapipe NormalizedLandmark for e.g. side='LEFT', joint_name='ELBOW'."""
    idx = _JOINT_NAME_TO_LANDMARK[side][joint_name]
    return landmarks[idx.value]


def to_pixel(landmark, frame_shape):
    """Convert a normalized (0-1) landmark to pixel (x, y) coordinates for this frame."""
    h, w = frame_shape[:2]
    return np.array([landmark.x * w, landmark.y * h])


def calculate_angle(a, b, c):
    """
    Calculate the angle (in degrees) at vertex b, formed by points a-b-c,
    using the arctan2 vector-angle method.

    a, b, c : array-like (x, y) coordinates (pixel or normalized - consistent units).
    Returns a value in [0, 180].
    """
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    c = np.array(c, dtype=float)

    radians = (np.arctan2(c[1] - b[1], c[0] - b[0]) -
               np.arctan2(a[1] - b[1], a[0] - b[0]))
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360.0 - angle
    return angle


def joint_visibility(landmarks, side, joint_names):
    """Average MediaPipe 'visibility' score (0-1) across the given joints on one side."""
    vis = [get_landmark(landmarks, side, name).visibility for name in joint_names]
    return float(np.mean(vis))
