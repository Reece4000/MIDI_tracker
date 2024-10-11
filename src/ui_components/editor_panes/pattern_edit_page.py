from src.ui_components.editor_panes.menu_page import MenuPage
from config.render_map import *
from config import themeing, scales, events
from config.pages import *
from src.utils import get_increment


NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


class PatternPage(MenuPage):
    def __init__(self, x, y, tracker):
        super().__init__(x, y, "PATTERN", tracker)
        self.image = self.image = self.tracker.renderer.load_image(r"resources\editor_panes\pattern_page.png")
        self.cursor_x = 0
        self.cursor_y = 0
        self.title_bg_selected = themeing.PATTERN_TITLE_SELECTED
        self.title_bg_unselected = themeing.PATTERN_TITLE_UNSELECTED

        self.textbox_x = self.x + 132
        self.text_cell_w = 78
        self.textbox_y_positions = [162, 184, 206, 228, 250]
        self.table_cell_w = 24

        self.master_params_xy = ((self.x + 150, 323), (self.x + 150, 344))

        self.pattern_table_x = self.x + 39
        self.pattern_table_y = 401

    def move_cursor(self, x, y):
        if y != 0:
            self.cursor_y = (self.cursor_y + y) % 13
        if x != 0 and self.cursor_y >= 5:
            self.cursor_x = (self.cursor_x + x) % 8

    def handle_param_adjust(self, increment, axis=False):
        tracker = self.tracker
        selected_pattern = tracker.get_selected_pattern()
        if self.active:
            if self.cursor_y == 0:
                tracker.adjust_bpm(get_increment(increment, "bpm"))
            elif self.cursor_y == 1:
                selected_pattern.loops += increment
            elif self.cursor_y == 2:
                selected_pattern.adjust_swing(get_increment(increment, "swing"))
            elif self.cursor_y == 3:
                selected_pattern.adjust_transpose(get_increment(increment, "note"))
            elif self.cursor_y == 4:
                selected_pattern.adjust_scale(increment)

            elif self.cursor_y in [5, 6]:
                master_track = selected_pattern.master_track
                if self.cursor_y == 5:
                    master_track.adjust_length(get_increment(increment, "length"))
                elif self.cursor_y == 6:
                    master_track.adjust_lpb(get_increment(increment, "lpb"))
                tracker.pages[MASTER].flag_state_change()

            elif self.cursor_y >= 7:
                track_index = self.cursor_x
                row_index = self.cursor_y - 7
                track = selected_pattern.midi_tracks[track_index]
                if row_index == 0:
                    track.adjust_length(get_increment(increment, "length"))
                elif row_index == 1:
                    track.adjust_lpb(get_increment(increment, "lpb"))
                elif row_index == 2:
                    track.adjust_transpose(get_increment(increment, "note"))
                elif row_index == 3:
                    track.adjust_swing(get_increment(increment, "swing"))
                elif row_index == 4:
                    track.handle_mute(send_note_offs=tracker.is_playing)
                elif row_index == 5:
                    track.handle_solo()
                tracker.pages[PATTERN].state_changed[track_index] = 1

    def update_view(self, tracker, editor_active):
        selected_pattern = tracker.get_selected_pattern()

        if self.active and selected_pattern is not None:
            bpm = str(selected_pattern.bpm)
            loops = str(selected_pattern.loops)
            swing = str(selected_pattern.swing)
            transpose = str(selected_pattern.transpose) + " (" + NOTES[selected_pattern.transpose % 12] + ")"
            if selected_pattern.transpose > 0:
                transpose = "+" + transpose
            scale_mode = scales.SCALES[selected_pattern.scale]["name"]

            textbox_items = [bpm, loops, swing, transpose, scale_mode]

            # pattern params
            for i, item in enumerate(textbox_items):
                assert i < 5
                x_position = int((self.textbox_x + 40) - (len(item) * 4))
                if i == self.cursor_y:
                    text_color = themeing.BLACK
                    bg_color = themeing.CURSOR_COLOR if editor_active else themeing.CURSOR_COLOR_ALT
                else:
                    text_color, bg_color = themeing.WHITE, self.bg

                self.to_render[i] = [[RECT, bg_color, self.textbox_x, self.textbox_y_positions[i],
                                      self.text_cell_w+2, self.cell_h, 0],
                                     [TEXT, "textbox_font", text_color, item,
                                      x_position, self.textbox_y_positions[i] - 1, 0]]

            # master track params
            master_track = selected_pattern.master_track
            master_len, master_lpb = str(master_track.length), str(master_track.lpb)
            for i, item in enumerate([master_len, master_lpb]):
                x, y = self.master_params_xy[i]
                x_position = int((x + 16) - (len(item) * 4))
                if i == self.cursor_y - 5:
                    text_color = themeing.BLACK
                    bg_color = themeing.CURSOR_COLOR if editor_active else themeing.CURSOR_COLOR_ALT
                else:
                    text_color, bg_color = themeing.WHITE, self.bg
                self.to_render[(i + 5)] = [[RECT, bg_color, x, y, self.table_cell_w + 7, self.cell_h, 0],
                                           [TEXT, "textbox_font", text_color, item, x_position, y, 0]]

            # midi track params
            for i, track in enumerate(selected_pattern.midi_tracks):
                items = [
                    str(track.length),
                    str(track.lpb),
                    str(track.transpose),
                    "P" if track.swing == -1 else str(track.swing),
                    "Y" if track.is_muted else "N",
                    "Y" if track.is_soloed else "N"
                ]
                for j, item in enumerate(items):
                    x_pos = self.pattern_table_x + (i * 25)
                    y_pos = self.pattern_table_y + (j * 21)
                    if i >= 4:
                        x_pos += 3
                    text_x_pos = (x_pos + 12) - (len(item) * 4)
                    if j == self.cursor_y - 7 and i == self.cursor_x:
                        text_color = themeing.BLACK
                        bg_color = themeing.CURSOR_COLOR if editor_active else themeing.CURSOR_COLOR_ALT
                    else:
                        text_color, bg_color = themeing.WHITE, self.bg

                    self.to_render[(i, j)] = [[RECT, bg_color, x_pos, y_pos, self.table_cell_w-1, self.cell_h + 2, 0],
                                              [TEXT, "textbox_small", text_color, item, text_x_pos, y_pos, 0]]

        if selected_pattern is not None:
            pattern_num = selected_pattern.num
        else:
            pattern_num = "N/A"

        self.title = f"{self.name} {pattern_num}"
        super().update_view(tracker, editor_active)

        self.check_redraw(tracker.renderer.render_queue)
