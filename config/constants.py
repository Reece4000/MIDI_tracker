note_base_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-', 'OFF']
track_names = ["1", "2", "3", "4", "5", "6", "7", "8"]

center_y_cursor = True

start_bpm = 170
start_len = 64
start_lpb = 32
start_swing = 0

track_count = 8
track_length = 64
timeline_length = max_patterns = 1000

start_note = 60
start_vel = 80
max_ccs = 12
max_polyphony = 4
note_off = [-1, -1, -1, -1]
empty = [None, None, None, None]
empty_components = [[None, None, None], [None, None, None], [None, None, None], [None, None, None]]

page_map = {"song": 0, "phrase": 1, "master": 2, "pattern": 3, "detail": 4}

master_component_mapping = {
    'SPD': {'Name': 'Speed Up',
            'Abbreviation': '>',
            'Color': (255, 255, 50)},
    'SLW': {'Name': 'Slow Down',
            'Abbreviation': '<>>',
            'Color': (255, 255, 50)},
    'TRA': {'Name': 'Global Transpose',
            'Abbreviation': 'T',
            'Color': (255, 255, 50)},
    'SNC': {'Name': 'Sync Playheads',
            'Abbreviation': 'S',
            'Color': (50, 255, 50)},
    'LOO': {'Name': 'Loop/Repeat',
            'Abbreviation': 'L',
            'Color': (255, 50, 50)},
    'REV': {'Name': 'Reverse Tracks',
            'Abbreviation': 'R',
            'Color': (255, 50, 50)},
    'MUT': {'Name': 'Mute Tracks',
            'Abbreviation': 'M',
            'Color': (255, 50, 50)}
}

FOLLOW_MASTER = 0
FOLLOW_PATTERN = 1
