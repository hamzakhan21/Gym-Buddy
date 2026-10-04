# Calibration Guide

## Quick start
```bash
pip install -r requirements.txt
python main.py
```
Stand ~2-3 meters back so your whole upper body (shoulder, elbow, wrist, hip)
is in frame, side-on or at a slight angle to the camera works best for curls.

Useful flags:
```bash
python main.py --exercise bicep_curl --reps-per-set 12 --rest-seconds 45 --arm auto
python main.py --exercise shoulder_press --arm both
python main.py --exercise lateral_raise --camera 1
```

## 1. Tuning the up/down angle thresholds
Angles are printed live on screen ("Angle: NN.N deg"), which is the fastest
way to calibrate for your own arm length and camera position:

1. Run the program and watch the angle readout while you do a few slow reps.
2. Note the angle at full arm extension (bottom of a curl) and at full
   contraction (top of a curl).
3. Open `exercises.py` and adjust the matching `ExerciseConfig`:
   - `down_angle`: set slightly *inside* your observed extended angle
     (e.g. if you extend to 172°, set `down_angle=160` so it triggers
     reliably even if you don't lock out perfectly).
   - `up_angle`: set slightly *outside* your observed contracted angle
     (e.g. if you curl to 32°, set `up_angle=40` so a few degrees of
     phone-camera noise doesn't stop it from registering).
   - Leave a healthy gap (at least 60-80°) between `down_angle` and
     `up_angle` so partial reps / jitter can't accidentally trigger both
     states in the same rep.

If reps aren't counting: your `up_angle`/`down_angle` are probably too
strict (e.g. requiring a perfect 180° lockout you never quite reach).
If reps are counting too easily / on partial movement: tighten the gap.

## 2. Smoothing window
`--smoothing-window` (default 5) controls how many recent frames are
averaged before comparing to the thresholds.
- Increase (e.g. 7-10) if the angle readout looks jumpy/noisy on your
  webcam, or you get occasional phantom reps.
- Decrease (e.g. 3) if reps feel "laggy" / slow to register, and your
  camera feed is already stable.

## 3. Arm selection (`--arm`)
- `auto` (default): automatically tracks whichever arm has clearer
  landmark visibility, with a small hysteresis margin (`ARM_SWITCH_MARGIN`
  in `main.py`) so it doesn't flicker between arms every frame. Good for
  single-arm dumbbell curls done side-on to the camera.
- `left` / `right`: force one specific arm - useful if you always face the
  camera and want to isolate one side regardless of visibility.
- `both`: tracks left and right independently with separate rep/set
  counters (e.g. for barbell-style bilateral curls, or alternating curls
  where you want per-arm totals).

## 4. Form-check thresholds (`form_checker.py`)
- `ELBOW_DRIFT_THRESHOLD` (default 0.35): elbow-to-hip horizontal distance,
  normalized by torso length. Lower it to catch smaller amounts of elbow
  drift; raise it if you're getting false "elbow drifting" warnings on a
  normal, correct-form rep (some drift is normal - especially face-on to
  the camera, where torso-relative motion is harder to see).
- `SHOULDER_SWAY_THRESHOLD` (default 0.04): average frame-to-frame shoulder
  movement, normalized by frame height. Lower it to catch subtler
  swinging/momentum; raise it if normal breathing/weight-shift triggers
  false positives.
- `SWAY_HISTORY_LEN` (default 6): number of recent frames used to compute
  average shoulder movement. A longer window smooths out one-off jitter
  but reacts more slowly to genuine swinging.

## 5. Camera / detection confidence
`--min-detection-confidence` / `--min-tracking-confidence` (default 0.6
each) control how confident MediaPipe must be before it reports/keeps
tracking a landmark.
- Raise them (e.g. 0.7-0.8) in good, bright, uncluttered conditions for
  more reliable, less jittery tracking.
- Lower them (e.g. 0.4-0.5) in dim lighting or with a lower-quality webcam
  if the skeleton keeps disappearing, at the cost of slightly less
  reliable landmarks.

## 6. Adding a new exercise
Add an entry to the `EXERCISES` dict in `exercises.py` with:
- `joint_triplet`: the three joints defining the angle (angle is measured
  at the middle one) - e.g. `('HIP', 'SHOULDER', 'ELBOW')` for angles
  measured at the shoulder.
- `down_angle` / `up_angle` and `direction` ('decreasing' if the angle
  shrinks as you move to the "up"/contracted position, like a curl;
  'increasing' if it grows, like a press or raise).

No other file needs to change - `main.py`, `rep_counter.py`, and
`form_checker.py` are all driven by this config.
