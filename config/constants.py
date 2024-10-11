note_base_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-', 'OFF']
track_names = ["1", "2", "3", "4", "5", "6", "7", "8"]

center_y_cursor = True

start_bpm = 170
start_len = 32
start_lpb = 4
start_swing = 0

track_count = 8
master_track_length = 64
track_length = 64
timeline_length = max_patterns = 1000

start_note = 60
start_vel = 80
start_cc = 1
start_cc_val = 64
max_ccs = 16
max_polyphony = 4

note_off = [-1, -1, -1, -1]
zeroes = [0, 0, 0, 0]
empty = [None] * 4
empty_sixteen = [None] * 16

track_mask = [0, 0, 0, 0, 0, 0, 0, 0]

page_map = {"song": 0, "phrase": 1, "master": 2, "pattern": 3, "detail": 4}

master_component_mapping = {
    0: {"name": "REVERSE",
        "color": (255, 50, 50),
        "abbreviation": "REV",
        "step display": "R",
        "description": "Reverse the playhead direction of selected tracks",
        "x": None,
        "y": None},

    1: {"name": "MASTER SYNC",
        "color": (50, 255, 50),
        "abbreviation": "SYNC",
        "step display": "S",
        "description": "Sync the selected tracks' playheads to the master track",
        "x": None,
        "y": None},

    2: {"name": "SPEED UP",
        "color": (50, 50, 255),
        "abbreviation": "SPD",
        "step display": ">",
        "description": "Increase the LPB of the selected tracks (x = absolute value, y = proportional).",
        "x": 0,
        "y": 0},

    3: {"name": "SLOW DOWN",
        "color": (50, 50, 255),
        "abbreviation": "SLW",
        "step display": "<",
        "description": "Reduce the LPB of the selected tracks (x = absolute value, y = proportional)",
        "x": 0,
        "y": 0},

    4: {"name": "TRANSPOSE",
        "color": (50, 50, 255),
        "abbreviation": "TRSP",
        "step display": "T",
        "description": "Transpose the selected tracks by x semitones",
        "x": 0,
        "y": None},

    5: {"name": "STEP REPEAT",
        "color": (50, 50, 255),
        "abbreviation": "REP",
        "step display": "L",
        "description": "Repeat the current step x times for selected tracks",
        "x": 0,
        "y": None},

    6: {"name": "STEP HOLD",
        "color": (50, 50, 255),
        "abbreviation": "HOLD",
        "step display": "H",
        "description": "Hold the current step for x steps for selected tracks",
        "x": 0,
        "y": None},

    7: {"name": "JUMP TO",
        "color": (50, 50, 255),
        "abbreviation": "JUMP",
        "step display": "J",
        "description": "Jump to step x in the selected tracks (set x to -1 for a random step). If x > than the length of the track, the playhead will loop back to the start.",
        "x": 0,
        "y": None},

    8: {"name": "MUTE TRACKS",
        "color": (50, 50, 255),
        "abbreviation": "MUTE",
        "step display": "M",
        "description": "Mute the selected tracks; any unselected tracks will be un-muted if already muted",
        "x": None,
        "y": None},

    9: {"name": "SOLO TRACKS",
        "color": (50, 50, 255),
        "abbreviation": "SOLO",
        "step display": "S",
        "description": "Solo the selected tracks; any unselected tracks will be un-soloed if already soloed",
        "x": None,
        "y": None},

    10: {"name": "RANDOMISE",
         "color": (50, 50, 255),
         "abbreviation": "RAND",
         "step display": "R",
         "description": "Randomise any inputted notes/velocities/ccs of the current step in the selected tracks. x = 0 for notes, 1 for velocities, 2 for ccs. The y parameter specifies the range of randomisation.",
         "x": 0,
         "y": 0},

    11: {"name": "RAMP",
         "color": (50, 50, 255),
         "abbreviation": "RAMP",
         "step display": "R",
         "description": "With each successive step, increase or decrease the note/velocity/cc value by y. x = 0 for notes, 1 for velocities, 2 for ccs.",
         "x": 0,
         "y": 0},

    12: {"name": "RETRIGGER",
         "color": (50, 50, 255),
         "abbreviation": "RET",
         "step display": "T",
         "description": "Continuous retrigger of the current step for all selected tracks. x = number of ticks between retriggers, y = velocity fade-in/out",
         "x": None,
         "y": None},

    13: {"name": "PROBABILITY",
         "color": (50, 50, 255),
         "abbreviation": "PROB",
         "step display": "P",
         "description": "Assign a probability of x% to play the current step in the selected tracks",
         "x": 0,
         "y": None},

    14: {"name": "SKIP",
         "color": (50, 50, 255),
         "abbreviation": "SKIP",
         "step display": "S",
         "description": "Skip the playhead forward/backwards by x steps in the selected tracks, y = probability of skipping",
         "x": 0,
         "y": 0},

    15: {"name": "CLEAR",
         "color": (50, 50, 255),
         "abbreviation": "CLR",
         "step display": "C",
         "description": "Clear any component-induced modifications for all selected tracks",
         "x": None,
         "y": None}
}

INCREMENTS = {
    "bpm": {
        "large": 10,
        "small": 1
    },
    "note": {
        "large": 12,
        "small": 1
    },
    "velocity": {
        "large": 10,
        "small": 1
    },
    "cc": {
        "large": 10,
        "small": 1
    },
    "swing": {
        "large": 4,
        "small": 1
    },
    "scale": {
        "large": 4,
        "small": 1
    },
    "channel": {
        "large": 10,
        "small": 1
    },
    "lpb": {
        "large": 4,
        "small": 1
    },
    "length": {
        "large": 16,
        "small": 1
    }
}

FOLLOW_MASTER = 0
FOLLOW_PATTERN = 1
