"""
main.py
Real-time dumbbell exercise rep/set counter.

Run with:
    python main.py
    python main.py --exercise bicep_curl --reps-per-set 10 --arm auto

Controls (while the video window is focused):
    q  -  quit
    r  -  reset rep/set counts
    p  -  pause / resume
    f  -  toggle fullscreen
    m  -  open/close the in-app exercise-switch menu (then press 1/2/3/... )
"""

import argparse
import time

import cv2
import mediapipe as mp

from exercises import get_exercise, EXERCISES
from pose_utils import get_landmark, to_pixel, calculate_angle, joint_visibility
from rep_counter import ArmRepCounter
from form_checker import FormChecker
import renderer

mp_pose = mp.solutions.pose

VISIBILITY_THRESHOLD = 0.5   # below this, a landmark is treated as "not visible"
ARM_SWITCH_MARGIN = 0.10     # hysteresis: how much better the other arm must be to switch

# Menu entries, in a fixed order, keyed to number keys '1', '2', '3', ...
EXERCISE_MENU_ITEMS = [
    (str(i + 1), name, cfg.name) for i, (name, cfg) in enumerate(EXERCISES.items())
]


def parse_args():
    p = argparse.ArgumentParser(description="Real-time dumbbell exercise rep/set counter")
    p.add_argument('--exercise', default='bicep_curl',
                    choices=list(EXERCISES.keys()),
                    help="Which exercise to track at startup (default: bicep_curl). "
                         "You can also switch exercises live by pressing 'm' in the app.")
    p.add_argument('--reps-per-set', type=int, default=10)
    p.add_argument('--rest-seconds', type=int, default=30)
    p.add_argument('--arm', default='auto', choices=['auto', 'left', 'right', 'both'],
                    help="'auto' = whichever arm is more clearly visible; "
                         "'both' = independent left+right counters shown side by side")
    p.add_argument('--camera', type=int, default=0, help="Webcam index")
    p.add_argument('--smoothing-window', type=int, default=5,
                    help="Frames to moving-average the joint angle over (noise reduction)")
    p.add_argument('--min-detection-confidence', type=float, default=0.6)
    p.add_argument('--min-tracking-confidence', type=float, default=0.6)
    p.add_argument('--windowed', action='store_true',
                    help="Start in a normal resizable window instead of fullscreen "
                         "(press 'f' anytime to toggle either way)")
    return p.parse_args()


def build_state(cfg, args):
    """Create fresh counters + form checkers for the given exercise config."""
    if args.arm == 'both':
        counters = {
            'LEFT': ArmRepCounter(cfg, args.reps_per_set, args.rest_seconds, args.smoothing_window),
            'RIGHT': ArmRepCounter(cfg, args.reps_per_set, args.rest_seconds, args.smoothing_window),
        }
        form_checkers = {'LEFT': FormChecker(), 'RIGHT': FormChecker()}
    else:
        counters = {'AUTO': ArmRepCounter(cfg, args.reps_per_set, args.rest_seconds, args.smoothing_window)}
        form_checkers = {'AUTO': FormChecker()}
    return counters, form_checkers


def pick_side(landmarks, joint_names, current_side):
    """Choose LEFT or RIGHT based on landmark visibility, with hysteresis
    so the tracked arm doesn't flicker back and forth every frame."""
    left_vis = joint_visibility(landmarks, 'LEFT', joint_names)
    right_vis = joint_visibility(landmarks, 'RIGHT', joint_names)

    if current_side is None:
        return ('LEFT' if left_vis >= right_vis else 'RIGHT'), max(left_vis, right_vis)

    if current_side == 'LEFT':
        if right_vis > left_vis + ARM_SWITCH_MARGIN:
            return 'RIGHT', right_vis
        return 'LEFT', left_vis
    else:
        if left_vis > right_vis + ARM_SWITCH_MARGIN:
            return 'LEFT', left_vis
        return 'RIGHT', right_vis


def angle_for_side(landmarks, side, joint_triplet, frame_shape):
    a = to_pixel(get_landmark(landmarks, side, joint_triplet[0]), frame_shape)
    b = to_pixel(get_landmark(landmarks, side, joint_triplet[1]), frame_shape)
    c = to_pixel(get_landmark(landmarks, side, joint_triplet[2]), frame_shape)
    return calculate_angle(a, b, c)


def main():
    args = parse_args()
    current_exercise_name = args.exercise
    cfg = get_exercise(current_exercise_name)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"ERROR: could not open camera index {args.camera}")
        return

    pose = mp_pose.Pose(min_detection_confidence=args.min_detection_confidence,
                         min_tracking_confidence=args.min_tracking_confidence)

    counters, form_checkers = build_state(cfg, args)
    active_side = None if args.arm == 'auto' else args.arm.upper()

    paused = False
    menu_open = False
    fullscreen = not args.windowed
    session_start = time.time()
    prev_time = time.time()

    window_name = 'Dumbbell Rep Counter'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(
        window_name, cv2.WND_PROP_FULLSCREEN,
        cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL,
    )

    print("Controls:  q quit   r reset   p pause   f fullscreen   m exercise menu")

    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                print("WARNING: failed to read frame from camera.")
                break

            frame = cv2.flip(frame, 1)  # mirror for a natural self-view
            now = time.time()
            fps = 1.0 / max(1e-6, now - prev_time)
            prev_time = now

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                for c in counters.values():
                    c.reset()
                for f in form_checkers.values():
                    f.reset()
                print("Counts reset.")
            elif key == ord('p'):
                if not menu_open:
                    paused = not paused
            elif key == ord('f'):
                fullscreen = not fullscreen
                cv2.setWindowProperty(
                    window_name, cv2.WND_PROP_FULLSCREEN,
                    cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL,
                )
            elif key == ord('m'):
                menu_open = not menu_open
            elif menu_open and ord('1') <= key <= ord('9'):
                idx = key - ord('1')
                if 0 <= idx < len(EXERCISE_MENU_ITEMS):
                    _, new_name, display_name = EXERCISE_MENU_ITEMS[idx]
                    if new_name != current_exercise_name:
                        current_exercise_name = new_name
                        cfg = get_exercise(current_exercise_name)
                        counters, form_checkers = build_state(cfg, args)
                        active_side = None if args.arm == 'auto' else args.arm.upper()
                        print(f"Switched exercise to: {display_name}")
                    menu_open = False

            warnings = []
            angle_display = None
            side_label = args.arm

            if menu_open:
                # Keep showing the live feed behind the menu, but skip
                # detection/counting entirely while the menu is open.
                renderer.draw_exercise_menu(frame, EXERCISE_MENU_ITEMS, current_exercise_name)
                cv2.imshow(window_name, frame)
                continue

            if not paused:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False
                results = pose.process(rgb)

                if results.pose_landmarks is None:
                    # Person left the frame / not detected: show a warning,
                    # do NOT update counters (avoids false counts / crashes).
                    renderer.draw_no_person_warning(frame)
                else:
                    landmarks = results.pose_landmarks.landmark
                    renderer.draw_skeleton(frame, results.pose_landmarks)

                    if args.arm == 'both':
                        for side in ('LEFT', 'RIGHT'):
                            vis = joint_visibility(landmarks, side, cfg.joint_triplet)
                            if vis < VISIBILITY_THRESHOLD:
                                warnings.append(f"{side.title()} arm not clearly visible")
                                continue
                            angle = angle_for_side(landmarks, side, cfg.joint_triplet, frame.shape)
                            counters[side].update(angle)

                            hip = to_pixel(get_landmark(landmarks, side, cfg.hip_reference_joint), frame.shape)
                            elbow = to_pixel(get_landmark(landmarks, side, cfg.elbow_drift_joint), frame.shape)
                            shoulder = to_pixel(get_landmark(landmarks, side, 'SHOULDER'), frame.shape)
                            if form_checkers[side].check_elbow_drift(elbow, hip, shoulder):
                                warnings.append(f"{side.title()}: elbow drifting from torso")
                            if form_checkers[side].check_torso_sway(shoulder, frame.shape[0]):
                                warnings.append(f"{side.title()}: excessive body swing")
                        side_label = "Both arms"

                    else:
                        active_side, vis = pick_side(landmarks, cfg.joint_triplet, active_side)
                        if vis < VISIBILITY_THRESHOLD:
                            warnings.append("Arm not clearly visible - step back / face camera")
                        else:
                            angle = angle_for_side(landmarks, active_side, cfg.joint_triplet, frame.shape)
                            angle_display = angle
                            counters['AUTO'].update(angle)

                            hip = to_pixel(get_landmark(landmarks, active_side, cfg.hip_reference_joint), frame.shape)
                            elbow = to_pixel(get_landmark(landmarks, active_side, cfg.elbow_drift_joint), frame.shape)
                            shoulder = to_pixel(get_landmark(landmarks, active_side, 'SHOULDER'), frame.shape)
                            if form_checkers['AUTO'].check_elbow_drift(elbow, hip, shoulder):
                                warnings.append("Elbow drifting from torso - keep it pinned")
                            if form_checkers['AUTO'].check_torso_sway(shoulder, frame.shape[0]):
                                warnings.append("Excessive body swing - slow down, avoid momentum")
                        side_label = active_side.title() if active_side else "--"

            if args.arm == 'both':
                l, r = counters['LEFT'], counters['RIGHT']
                renderer.draw_hud(frame, cfg.name, "Left", l.reps, l.sets, args.reps_per_set,
                                   l.stage, None, warnings, paused, l.resting,
                                   l.rest_time_remaining(), l.rest_seconds, fps)
                cv2.putText(frame,
                            f"Right - Reps: {r.reps}/{args.reps_per_set}  Sets: {r.sets}  "
                            f"Stage: {r.stage or '--'}",
                            (15, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
            else:
                c = counters['AUTO']
                renderer.draw_hud(frame, cfg.name, side_label, c.reps, c.sets,
                                   args.reps_per_set, c.stage, angle_display,
                                   warnings, paused, c.resting, c.rest_time_remaining(),
                                   c.rest_seconds, fps)

            cv2.imshow(window_name, frame)

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        pose.close()
        print_summary(counters, session_start, args, current_exercise_name)


def print_summary(counters, session_start, args, exercise_name):
    duration = time.time() - session_start
    mins, secs = divmod(int(duration), 60)
    print("\n===== Session Summary =====")
    print(f"Exercise (at exit): {exercise_name}")
    print(f"Duration: {mins}m {secs}s")
    if args.arm == 'both':
        for side in ('LEFT', 'RIGHT'):
            c = counters[side]
            print(f"{side.title()} arm - Sets completed: {c.sets}, "
                  f"Reps in current set: {c.reps}, Total reps: {c.total_reps_all_sets}")
    else:
        c = counters['AUTO']
        print(f"Sets completed: {c.sets}")
        print(f"Reps in current (incomplete) set: {c.reps}")
        print(f"Total reps: {c.total_reps_all_sets}")
    print("============================\n")


if __name__ == '__main__':
    main()