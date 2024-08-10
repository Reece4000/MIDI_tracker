# Constants for the display
MENU_HEIGHT = 90  # Height for the top menu area
TRACK_INFO_HEIGHT = 20  # Height for track numbers

note_base_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-', 'OFF']

BG_COLOR = (20, 30, 30)
BG_TASKPANE = (30, 50, 50)
BG_SHADOW = (16, 26, 26)
BG_DARKER = (12, 24, 24)
LINE_BG = (25, 45, 45)
LINE_8_HL_BG = (35, 55, 55)
LINE_16_HL_BG = (45, 70, 70)
LINE_COLOR = (255, 255, 255)
CURSOR_COLOR = (230, 203, 0)
CURSOR_COLOR_ALT = (186, 107, 73)
PLAYHEAD_COLOR = (0, 255, 0)
PLAYHEAD_COLOR_ALT = (180, 255, 180)
FONT_SIZE = 11

# Tracker settings
track_names = ["MASTER", "KICK", "SNARE", "HAT", "PERC", "BASS", "LEAD", "ARP", "CHORD"]
track_colors = [
    (220, 220, 220),  # White
    (255, 0, 0),  # Red
    (255, 165, 0),  # Orange
    (255, 255, 0),  # Yellow
    (0, 255, 0),  # Green
    (120, 120, 255),  # Blue
    (0, 255, 255),  # Cyan
    (200, 50, 200),  # Purple
    (255, 192, 203)  # Pink
]
bpm = 120
track_count = 9
track_length = 16
row_h = 20
col_w = 90
start_x = 110
tr_offset_x = 29
start_y = 0
pattern_line_len = -5 + (col_w + 18) * track_count

play_x, play_y = 100, 10

midi_label_offset = int(col_w * 0.78)
song_playhead_offset = int(col_w * 1.6)
phrase_playhead_offset = int(col_w * 0.8)

# GUI WINDOW
WIDTH, HEIGHT = ((col_w+18) * track_count), 750


master_component_mapping = {
    '>': 'Speed Up',
    '<': 'Slow Down',
    'U': 'Global Transpose Up',
    'D': 'Global Transpose Down',
    'S': 'Sync Playheads',
    'L': 'Loop/Repeat',
    'R': 'Reverse',
    'M': 'Mute'
}

track_component_mapping = {

}
