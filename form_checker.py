"""
form_checker.py
Lightweight heuristic form checks - not a substitute for a trainer, but
catches the two most common dumbbell-curl mistakes:

  1. Elbow drifting away from the torso (swinging the elbow forward/out
     instead of keeping it pinned at the side).
  2. Excessive shoulder/torso movement between frames (a proxy for body
     swing / using momentum instead of the target muscle).

Tune the *_THRESHOLD constants below for your body proportions and camera
distance - see the calibration guide.
"""

from collections import deque
import numpy as np


class FormChecker:
    # Elbow-to-hip horizontal distance, normalized by torso length
    # (shoulder-to-hip). Above this fraction => "drifting" warning.
    ELBOW_DRIFT_THRESHOLD = 0.35

    # Average frame-to-frame shoulder movement, normalized by frame height.
    # Above this fraction => "swinging / momentum" warning.
    SHOULDER_SWAY_THRESHOLD = 0.04
    SWAY_HISTORY_LEN = 6

    def __init__(self):
        self.shoulder_history = deque(maxlen=self.SWAY_HISTORY_LEN)

    def check_elbow_drift(self, elbow_xy, hip_xy, shoulder_xy):
        torso_len = np.linalg.norm(np.array(shoulder_xy) - np.array(hip_xy))
        if torso_len < 1e-6:
            return False
        drift = abs(elbow_xy[0] - hip_xy[0]) / torso_len
        return drift > self.ELBOW_DRIFT_THRESHOLD

    def check_torso_sway(self, shoulder_xy, frame_height):
        self.shoulder_history.append(np.array(shoulder_xy))
        if len(self.shoulder_history) < 2:
            return False
        deltas = [
            np.linalg.norm(self.shoulder_history[i] - self.shoulder_history[i - 1])
            for i in range(1, len(self.shoulder_history))
        ]
        avg_delta = float(np.mean(deltas)) / frame_height
        return avg_delta > self.SHOULDER_SWAY_THRESHOLD

    def reset(self):
        self.shoulder_history.clear()
