"""
exercises.py
Declarative exercise definitions. Each exercise says which three joints
define the tracked angle (vertex = middle joint), and what angle range
counts as "down" (start) vs "up" (contracted/top) position.

To add a new exercise, add a new ExerciseConfig entry - no other code needs
to change. This is the single place you customize when swapping from
bicep curls to shoulder press / lateral raises / etc.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class ExerciseConfig:
    name: str
    # Three joint names (as used in pose_utils) defining the tracked angle;
    # the angle is measured at the MIDDLE joint.
    joint_triplet: Tuple[str, str, str]
    down_angle: float      # angle (degrees) that defines the "down"/start position
    up_angle: float         # angle (degrees) that defines the "up"/contracted position
    direction: str           # 'decreasing' (curl-like: angle shrinks on the way up)
                             # or 'increasing' (press/raise-like: angle grows on the way up)
    elbow_drift_joint: str = 'ELBOW'   # joint used for the "drifts from torso" form check
    hip_reference_joint: str = 'HIP'


EXERCISES = {
    # Shoulder -> Elbow -> Wrist angle. Starts extended (~160-180 deg),
    # curls up to a small angle (~30-40 deg) at the top.
    'bicep_curl': ExerciseConfig(
        name='Bicep Curl',
        joint_triplet=('SHOULDER', 'ELBOW', 'WRIST'),
        down_angle=160.0,
        up_angle=40.0,
        direction='decreasing',
    ),

    # Same joints (elbow angle), but the movement is inverted: starts bent
    # near 90 deg at shoulder height, extends to near-straight overhead.
    'shoulder_press': ExerciseConfig(
        name='Shoulder Press',
        joint_triplet=('SHOULDER', 'ELBOW', 'WRIST'),
        down_angle=90.0,
        up_angle=160.0,
        direction='increasing',
    ),

    # Angle at the SHOULDER between the torso (hip->shoulder) and the upper
    # arm (shoulder->elbow). Arm starts at the side (~10-20 deg) and raises
    # out to horizontal (~80-90 deg).
    'lateral_raise': ExerciseConfig(
        name='Lateral Raise',
        joint_triplet=('HIP', 'SHOULDER', 'ELBOW'),
        down_angle=20.0,
        up_angle=80.0,
        direction='increasing',
    ),

    # Same elbow angle as the press: bottom of a push-up has a bent elbow
    # (~70-90 deg, chest near the ground), top has arms extended (~160-170
    # deg). No dumbbell needed - the pose logic is identical either way.
    # Best tracked with the camera to your SIDE (profile view) so the
    # shoulder/elbow/wrist chain stays clearly visible throughout the rep.
    'pushup': ExerciseConfig(
        name='Push-Up',
        joint_triplet=('SHOULDER', 'ELBOW', 'WRIST'),
        down_angle=90.0,
        up_angle=160.0,
        direction='increasing',
    ),
}


def get_exercise(name):
    if name not in EXERCISES:
        raise ValueError(f"Unknown exercise '{name}'. Options: {list(EXERCISES)}")
    return EXERCISES[name]