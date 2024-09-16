# MAIN DIMS
block_size = 7
row_h = 21
visible_rows = 32
col_w = 84
menu_height = 28
pattern_area_height = visible_rows * row_h
timeline_offset = row_h * 3 + 5
num_timeline_rows = 20
timeline_cell_w = 30
timeline_cell_h = 19
display_w, display_h = 1220, 706

# TIMELINE
timeline_area_height = num_timeline_rows * row_h
timeline_width = 80

# timeline arrows
x1, x2 = 14, 50
y1, y2 = row_h * 12 + 2, row_h * 32 + 12
inc = 6
song_arrow_upper =   ( (x1, y1),  (x1 + inc, y1 - inc),  (x1 + inc * 2, y1) )
phrase_arrow_upper = ( (x2, y1),  (x2 + inc, y1 - inc),  (x2 + inc * 2, y1) )
song_arrow_lower =   ( (x1, y2),  (x1 + inc, y2 + inc),  (x1 + inc * 2, y2) )
phrase_arrow_lower = ( (x2, y2),  (x2 + inc, y2 + inc),  (x2 + inc * 2, y2) )

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

pattern_area_width = track_x_positions[7] - 20

cell_offs = 10
cell_text_offs = 2

play_x, play_y = 21, 190


detail_window_replace_bg_h = 580
detail_window_title_h = 36