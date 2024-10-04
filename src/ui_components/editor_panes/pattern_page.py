from src.ui_components.editor_panes.menu_page import MenuPage
from config.render_map import *
from config import themeing, scales, events
from config.pages import *
from src.utils import get_increment


class PatternPage(MenuPage):
    def __init__(self, x, y, tracker):
        super().__init__(x, y, "PATTERN", tracker)
        self.image = self.image = self.tracker.renderer.load_image(r"resources\editor_panes\pattern_page.png")
        self.cursor_x = 0
        self.cursor_y = 0
        self.title_bg_selected = themeing.PATTERN_TITLE_SELECTED
        self.title_bg_unselected = themeing.PATTERN_TITLE_UNSELECTED

        self.textbox_x = self.x + 133
        self.text_cell_w = 78
        self.textbox_y_positions = [164, 186, 208, 230, 252]
        self.table_cell_w = 28

        self.pattern_table_x = self.x + 58
        self.pattern_table_y = 359

    def move_cursor(self, x, y):
        if y != 0:
            self.cursor_y = (self.cursor_y + y) % 13
            if self.cursor_y < 5 and self.cursor_x > 0:
                self.cursor_x = 0
        if x != 0 and self.cursor_y >= 5:
            self.cursor_x = (self.cursor_x + x) % 5

    def handle_param_adjust(self, increment, axis=False):
        tracker = self.tracker
        cursor_pattern = tracker.cursor_pattern
        if self.active:
            if self.cursor_y == 0:
                tracker.adjust_bpm(get_increment(increment, "bpm"))
            elif self.cursor_y == 1:
                cursor_pattern.loops += increment
            elif self.cursor_y == 2:
                cursor_pattern.adjust_swing(get_increment(increment, "swing"))
            elif self.cursor_y == 3:
                cursor_pattern.adjust_transpose(get_increment(increment, "note"))
            elif self.cursor_y == 4:
                cursor_pattern.adjust_scale(increment)

            elif self.cursor_y >= 5:
                track_index = self.cursor_y - 5
                track = cursor_pattern.midi_tracks[track_index]
                if self.cursor_x == 0:
                    track.adjust_transpose(get_increment(increment, "note"))
                elif self.cursor_x == 1:
                    track.adjust_length(get_increment(increment, "length"))
                elif self.cursor_x == 2:
                    track.adjust_lpb(get_increment(increment, "lpb"))
                elif self.cursor_x == 3:
                    track.handle_mute(send_note_offs=tracker.is_playing)
                elif self.cursor_x == 4:
                    track.handle_solo()
                tracker.pages[PATTERN].state_changed[track_index] = 1

    def update_view(self, tracker, editor_active):
        cursor_pattern = tracker.cursor_pattern
        pattern_num = cursor_pattern.num

        if self.active:
            bpm = str(cursor_pattern.bpm)
            loops = str(cursor_pattern.loops)
            swing = str(cursor_pattern.swing)
            transpose = str(cursor_pattern.transpose)
            scale_mode = scales.SCALES[cursor_pattern.scale]["name"]

            textbox_items = [bpm, loops, swing, transpose, scale_mode]

            for i, item in enumerate(textbox_items):
                assert i < 5
                x_position = int((self.textbox_x + 40) - (len(item) * 4))
                if i == self.cursor_y:
                    text_color, bg_color = themeing.BLACK, themeing.CURSOR_COLOR
                else:
                    text_color, bg_color = themeing.WHITE, self.bg

                self.to_render[i] = [[RECT, bg_color, self.textbox_x, self.textbox_y_positions[i],
                                      self.text_cell_w, self.cell_h, 0],
                                     [TEXT, "textbox_font", text_color, item,
                                      x_position, self.textbox_y_positions[i] - 1, 0]]

            for i, track in enumerate(cursor_pattern.midi_tracks):
                items = [
                    str(track.transpose),
                    str(track.length),
                    str(track.lpb),
                    "Y" if track.is_muted else "N",
                    "Y" if track.is_soloed else "N"
                ]
                for j, item in enumerate(items):
                    x_pos = self.pattern_table_x + (j * 33)
                    y_pos = self.pattern_table_y + (i * 21)
                    if i >= 4:
                        y_pos += 4
                    text_x_pos = (x_pos + 14) - (len(item) * 4)
                    if j == self.cursor_x and i == self.cursor_y - 5:
                        text_color, bg_color = themeing.BLACK, themeing.CURSOR_COLOR
                    else:
                        text_color, bg_color = themeing.WHITE, self.bg

                    self.to_render[(i, j)] = [[RECT, bg_color, x_pos, y_pos, self.table_cell_w, self.cell_h, 0],
                                              [TEXT, "textbox_font", text_color, item, text_x_pos, y_pos - 1, 0]]

        self.title = f"{self.name} {pattern_num}"
        super().update_view(tracker, editor_active)

        self.check_redraw(tracker.renderer.render_queue)
