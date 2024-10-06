
from config.render_map import *
from config.themeing import *
from src.utils import get_polygon_coords

FPS = 60

# 1280 x 720 #
left_pane = [RECT, TIMELINE_BG, 0, 0, 150, 720, 0]
play_pause_circle = [CIRCLE, TIMELINE_BG_HL, (40, 5), 35, 0]
play_icon = [POLYGON, TIMELINE_BG, get_polygon_coords(53, 25, 20, 30), 0]
pause_icon1 = [RECT, TIMELINE_BG, 78, 25, 10, 30, 0]
pause_icon2 = [RECT, TIMELINE_BG, 93, 25, 10, 30, 0]
options_button = [RECT, TIMELINE_BG_HL, 0, 0, 150, 28, 0]

# MAIN DIMS
block_size = 7
row_h = 19
cell_y_offset = 1
visible_rows = 32
center_y = visible_rows // 2
col_w = 84
menu_height = 28
pattern_area_height = visible_rows * row_h
timeline_offset = row_h * 3 + 5
num_timeline_cells = 24
timeline_cell_w = 30
timeline_cell_h = 24
display_w, display_h = 1180, 714  # 1220, 706

# TIMELINE
timeline_area_y = menu_height + pattern_area_height + 12
timeline_area_height = num_timeline_cells * row_h
timeline_width = 40

# timeline arrows
x1, x2, y1, y2 = 14, 50, (row_h * 12 + 9), (row_h * 32 + 19)
inc = 6
song_arrow_upper = get_polygon_coords(x1, y1, 12, -inc)
phrase_arrow_upper = get_polygon_coords(x2, y1, 12, -inc)
song_arrow_lower =   get_polygon_coords(x1, y2, 12, inc)
phrase_arrow_lower = get_polygon_coords(x2, y2, 12, inc)

x_row_labels = timeline_width + 114
row_labels_w = 28

cursor_arrow_w = 6
cursor_arrow_h = 4
cursor_arrow_b = 2

# PATTERN COLUMNS
separator = 7
master_track_x_position = x_row_labels - (col_w + separator * 2)
track_x_positions = [
    x_row_labels + row_labels_w + separator,
    x_row_labels + row_labels_w + separator + (col_w + separator),
    x_row_labels + row_labels_w + separator + (col_w*2 + separator*2),
    x_row_labels + row_labels_w + separator + (col_w*3 + separator*3),
    x_row_labels + row_labels_w + separator + (col_w*4 + separator*4),
    x_row_labels + row_labels_w + separator + (col_w*5 + separator*5),
    x_row_labels + row_labels_w + separator + (col_w*6 + separator*6),
    x_row_labels + row_labels_w + separator + (col_w*7 + separator*7)
]

editor_window_x = track_x_positions[-1] + 100

pattern_area_width = track_x_positions[7] - 20

cell_offs = 10
cell_text_offs = 2

play_x, play_y = 15, 12


detail_window_replace_bg_h = 580
detail_window_title_h = 36

timeline_page_border = (timeline_width + 11, timeline_area_y - 2, 868, 64, 1)
song_page_border = (4, timeline_area_y-1, timeline_cell_w+4, timeline_area_height+2, 1)
phrase_page_border = (41, timeline_area_y-1, timeline_cell_w+4, timeline_area_height+2, 1)
master_page_border = (timeline_width + 12, 1, 93, menu_height + pattern_area_height + 3, 1)
pattern_page_border = (timeline_width + 145, 1, 730, menu_height + pattern_area_height + 3, 1)
