# Constants for the display
MENU_HEIGHT = 50  # Height for the top menu area
TRACK_INFO_HEIGHT = 20  # Height for track numbers

note_base_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-', 'OFF']

BG_COLOR = (20, 30, 30)
BG_TASKPANE = (30, 50, 50)
BG_SHADOW = (22, 32, 32)
BG_DARKER = (12, 24, 24)
LINE_4_HL_BG = (0, 45, 40)
LINE_8_HL_BG = (25, 38, 38)
LINE_16_HL_BG = (35, 50, 50)
LINE_NO_HL = (0, 40, 36)
LINE_COLOR = (255, 255, 255)
CURSOR_COLOR = (230, 203, 0)
CURSOR_COLOR_ALT = (186, 107, 73)
PLAYHEAD_COLOR = (0, 255, 0)
PLAYHEAD_COLOR_ALT = (180, 255, 180)
FONT_SIZE = 11

# Tracker settings
bpm = 120
track_count = 8
track_length = 64
row_h = 20
col_w = 102
start_x = 110
tr_offset_x = 29
start_y = 0
pattern_line_len = -5 + (col_w + 18) * track_count

play_x, play_y = 100, 15

midi_label_offset = int(col_w * 0.69)
song_playhead_offset = int(col_w * 1.6)
phrase_playhead_offset = int(col_w * 0.8)

# GUI WINDOW
WIDTH, HEIGHT = ((col_w+21) * track_count), 754

