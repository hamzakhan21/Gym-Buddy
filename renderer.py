"""
renderer.py
All OpenCV drawing lives here: the pose skeleton overlay, the styled HUD
(reps, sets, stage badge, progress bar, warnings, radial rest countdown),
and the in-app exercise-switch menu. Pure OpenCV + numpy - no extra
dependencies.
"""

import cv2
import numpy as np
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# ---- Color palette (BGR) ---------------------------------------------------
COLOR_ACCENT = (0, 140, 255)     # orange
COLOR_ACCENT2 = (255, 200, 0)    # cyan-ish
COLOR_TEXT = (240, 240, 240)
COLOR_MUTED = (150, 150, 150)
COLOR_WARN = (0, 70, 255)
COLOR_UP = (0, 210, 90)
COLOR_DOWN = (60, 130, 255)
COLOR_REST = (0, 210, 90)
COLOR_PANEL = (24, 24, 28)

_gradient_cache = {}


def _horizontal_gradient(width, height, color_left, color_right):
    """Cheap horizontal gradient bar built with numpy (cached per size/colors)."""
    key = (width, height, color_left, color_right)
    if key in _gradient_cache:
        return _gradient_cache[key]
    t = np.linspace(0, 1, width, dtype=np.float32).reshape(1, width, 1)
    left = np.array(color_left, dtype=np.float32).reshape(1, 1, 3)
    right = np.array(color_right, dtype=np.float32).reshape(1, 1, 3)
    row = (left * (1 - t) + right * t).astype(np.uint8)
    grad = np.repeat(row, height, axis=0)
    _gradient_cache[key] = grad
    return grad


def draw_skeleton(frame, pose_landmarks):
    mp_drawing.draw_landmarks(
        frame, pose_landmarks, mp_pose.POSE_CONNECTIONS,
        mp_drawing.DrawingSpec(color=COLOR_ACCENT2, thickness=2, circle_radius=3),
        mp_drawing.DrawingSpec(color=(230, 230, 230), thickness=2, circle_radius=2),
    )


def _progress_bar(frame, x, y, w, h, fraction, color):
    fraction = max(0.0, min(1.0, fraction))
    cv2.rectangle(frame, (x, y), (x + w, y + h), (55, 55, 55), -1)
    fill_w = int(w * fraction)
    if fill_w > 0:
        cv2.rectangle(frame, (x, y), (x + fill_w, y + h), color, -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (90, 90, 90), 1)


def draw_hud(frame, exercise_name, side_label, reps, sets, reps_per_set,
             stage, angle, warnings, paused, resting, rest_remaining, rest_total, fps):
    h, w = frame.shape[:2]

    # --- Top gradient bar -----------------------------------------------
    bar_h = 110
    grad = _horizontal_gradient(w, bar_h, (35, 20, 10), (12, 12, 12))
    band = frame[0:bar_h, 0:w]
    blended = cv2.addWeighted(grad, 0.85, band, 0.15, 0)
    frame[0:bar_h, 0:w] = blended

    cv2.putText(frame, exercise_name.upper(), (20, 32),
                cv2.FONT_HERSHEY_DUPLEX, 0.85, COLOR_ACCENT, 2)
    cv2.putText(frame, f"Arm: {side_label}", (20, 58),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_MUTED, 1)

    # Stage badge, top-right
    stage_color = COLOR_UP if stage == 'up' else COLOR_DOWN
    stage_text = (stage or '--').upper()
    (tw, th), _ = cv2.getTextSize(stage_text, cv2.FONT_HERSHEY_DUPLEX, 0.8, 2)
    badge_x2 = w - 20
    badge_x1 = badge_x2 - tw - 24
    cv2.rectangle(frame, (badge_x1, 12), (badge_x2, 12 + th + 16), stage_color, -1)
    cv2.putText(frame, stage_text, (badge_x1 + 12, 12 + th + 6),
                cv2.FONT_HERSHEY_DUPLEX, 0.8, (10, 10, 10), 2)

    if angle is not None:
        cv2.putText(frame, f"{angle:5.1f} deg", (w - 140, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_MUTED, 1)
    cv2.putText(frame, f"{fps:4.1f} fps", (w - 140, 88),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_MUTED, 1)

    # Reps (with progress bar) + sets
    cv2.putText(frame, f"Reps {reps}/{reps_per_set}", (20, 88),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLOR_TEXT, 2)
    _progress_bar(frame, 205, 72, 150, 16, reps / max(1, reps_per_set), COLOR_ACCENT2)
    cv2.putText(frame, f"Sets: {sets}", (375, 88),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLOR_TEXT, 2)

    # --- Form warnings -----------------------------------------------------
    y = bar_h + 30
    for warn in warnings:
        (tw2, th2), _ = cv2.getTextSize(warn, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (12, y - th2 - 8), (12 + tw2 + 45, y + 8), (0, 0, 0), -1)
        cv2.putText(frame, f"! {warn}", (24, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, COLOR_WARN, 2)
        y += 34

    if resting:
        _draw_rest_overlay(frame, rest_remaining, rest_total)

    if paused:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        cv2.putText(frame, "PAUSED", (w // 2 - 95, h // 2 - 10),
                    cv2.FONT_HERSHEY_DUPLEX, 1.1, COLOR_TEXT, 2)
        cv2.putText(frame, "press 'p' to resume", (w // 2 - 115, h // 2 + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_MUTED, 1)

    _draw_controls_hint(frame)


def _draw_rest_overlay(frame, remaining, total):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    cx, cy, r = w // 2, h // 2, 70
    fraction = 0.0 if total <= 0 else max(0.0, min(1.0, remaining / total))
    cv2.circle(frame, (cx, cy), r, (55, 55, 55), 6)
    end_angle = -90 + int(360 * fraction)
    cv2.ellipse(frame, (cx, cy), (r, r), 0, -90, end_angle, COLOR_REST, 8)
    cv2.putText(frame, f"{remaining:0.0f}", (cx - 28, cy + 15),
                cv2.FONT_HERSHEY_DUPLEX, 1.4, COLOR_TEXT, 3)
    cv2.putText(frame, "SET COMPLETE - REST", (cx - 150, cy - r - 25),
                cv2.FONT_HERSHEY_DUPLEX, 0.75, COLOR_REST, 2)


def _draw_controls_hint(frame):
    h, w = frame.shape[:2]
    cv2.putText(frame, "q quit   r reset   p pause   f fullscreen   m menu",
                (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_MUTED, 1)


def draw_no_person_warning(frame):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h // 2 - 40), (w, h // 2 + 10), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    cv2.putText(frame, "No person detected - step into frame", (30, h // 2 - 5),
                cv2.FONT_HERSHEY_DUPLEX, 0.75, COLOR_WARN, 2)


def draw_exercise_menu(frame, exercise_items, current_key):
    """
    exercise_items: list of (number_key:str, internal_name:str, display_name:str)
    """
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    panel_w = 440
    panel_h = 90 + 48 * len(exercise_items)
    x0, y0 = (w - panel_w) // 2, (h - panel_h) // 2
    cv2.rectangle(frame, (x0, y0), (x0 + panel_w, y0 + panel_h), COLOR_PANEL, -1)
    cv2.rectangle(frame, (x0, y0), (x0 + panel_w, y0 + panel_h), COLOR_ACCENT, 2)
    cv2.putText(frame, "SELECT EXERCISE", (x0 + 24, y0 + 40),
                cv2.FONT_HERSHEY_DUPLEX, 0.75, COLOR_ACCENT, 2)

    y = y0 + 80
    for num_key, internal_name, display_name in exercise_items:
        is_current = internal_name == current_key
        color = COLOR_UP if is_current else COLOR_TEXT
        marker = ">" if is_current else " "
        cv2.putText(frame, f"[{num_key}] {marker} {display_name}", (x0 + 30, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        y += 48

    cv2.putText(frame, "press a number to switch  -  'm' to close",
                (x0 + 24, y0 + panel_h - 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_MUTED, 1)