"""
rep_counter.py
Per-arm state machine for rep + set counting on a single tracked angle.

A rep only counts on a full down -> up -> down-armed transition (we re-arm
on reaching "down" again), which prevents jitter around the threshold from
registering multiple reps. Angles are smoothed with a moving average over
the last N frames before being compared to the thresholds.
"""

import time
from collections import deque


class ArmRepCounter:
    def __init__(self, exercise_cfg, reps_per_set=10, rest_seconds=30, smoothing_window=5):
        self.cfg = exercise_cfg
        self.reps_per_set = reps_per_set
        self.rest_seconds = rest_seconds
        self.smoothing_window = smoothing_window
        self.angle_history = deque(maxlen=smoothing_window)

        self.stage = None          # 'down' or 'up'
        self.reps = 0               # reps in the CURRENT set
        self.sets = 0                # completed sets this session
        self.total_reps_all_sets = 0  # reps across the whole session

        self.resting = False
        self.rest_start_time = None

    def reset(self):
        """Reset all counts (used by the 'r' key) but keep the same config."""
        self.__init__(self.cfg, self.reps_per_set, self.rest_seconds, self.smoothing_window)

    def _smoothed_angle(self, raw_angle):
        self.angle_history.append(raw_angle)
        return sum(self.angle_history) / len(self.angle_history)

    def rest_time_remaining(self):
        if not self.resting:
            return 0.0
        elapsed = time.time() - self.rest_start_time
        return max(0.0, self.rest_seconds - elapsed)

    def update(self, raw_angle):
        """
        Feed one new raw angle reading (in degrees) for this frame.
        Returns True if a rep was just completed on this call.
        """
        # While resting between sets, don't count reps - just keep the
        # smoothing buffer warm so there's no jump when rest ends.
        if self.resting:
            if self.rest_time_remaining() <= 0:
                self.resting = False
                self.stage = None  # require a fresh 'down' before the next rep counts
            else:
                self.angle_history.append(raw_angle)
                return False

        angle = self._smoothed_angle(raw_angle)
        rep_completed = False

        if self.cfg.direction == 'decreasing':
            # e.g. bicep curl: starts extended (large angle) -> curls to a small angle
            if angle >= self.cfg.down_angle:
                self.stage = 'down'
            elif angle <= self.cfg.up_angle and self.stage == 'down':
                self.stage = 'up'
                rep_completed = True
        else:  # 'increasing'
            # e.g. shoulder press / lateral raise: starts small angle -> extends large
            if angle <= self.cfg.down_angle:
                self.stage = 'down'
            elif angle >= self.cfg.up_angle and self.stage == 'down':
                self.stage = 'up'
                rep_completed = True

        if rep_completed:
            self.reps += 1
            self.total_reps_all_sets += 1
            if self.reps >= self.reps_per_set:
                self.sets += 1
                self.reps = 0
                self.resting = True
                self.rest_start_time = time.time()

        return rep_completed
