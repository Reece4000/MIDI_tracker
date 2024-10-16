from src.ui_components.editor_panes.menu_page import MenuPage
from config.render_map import *
from config.pages import *
from config import themeing, scales
from config import events
from src.utils import get_increment

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


class TrackPage(MenuPage):
    def __init__(self, x, y, tracker):
        super().__init__(x, y, "TRACK", tracker)
        self.image = self.image = self.tracker.renderer.load_image(r"resources\editor_panes\track_page.png")
        self.cursor_x = 0
        self.cursor_y = 0
        self.title_bg_selected = themeing.TRACK_TITLE_SELECTED
        self.title_bg_unselected = themeing.TRACK_TITLE_UNSELECTED

        self.textbox_x = self.x + 129
        self.cell_w = 78

        self.y_positions = [199, 224, 248, 273, 312, 337, 362, 386]

    def move_cursor(self, x, y):
        if y != 0:
            self.cursor_y = (self.cursor_y + y) % 8

    def handle_param_adjust(self, increment, axis=False):
        tracker = self.tracker
        curr_track = tracker.get_selected_track()
        track_index = tracker.pages[PATTERN].cursor_x
        if self.active:
            if self.cursor_y == 0:
                curr_track.adjust_channel(get_increment(increment, "channel"))
            if self.cursor_y == 1:
                curr_track.adjust_length(get_increment(increment, "length"))
            elif self.cursor_y == 2:
                curr_track.adjust_lpb(get_increment(increment, "lpb"))
            elif self.cursor_y == 3:
                curr_track.adjust_swing(get_increment(increment, "swing"))
            elif self.cursor_y == 4:
                curr_track.adjust_transpose(get_increment(increment, "note"))
            elif self.cursor_y == 5:
                curr_track.adjust_scale(get_increment(increment, "scale"))
            elif self.cursor_y == 6:
                curr_track.handle_mute(send_note_offs=tracker.is_playing)
            elif self.cursor_y == 7:
                curr_track.handle_solo()
            tracker.pages[PATTERN].state_changed[track_index] = 1

    def update_view(self, tracker, editor_active):
        curr_track = tracker.get_selected_track()

        if self.active and curr_track is not None:
            midi_channel = str(curr_track.channel + 1)
            length = str(curr_track.length)
            lpb = str(curr_track.lpb)
            if curr_track.swing >= 0:
                swing = str(curr_track.swing)
            else:
                swing = "PATTERN"
            root_note = NOTES[curr_track.transpose % 12]
            pitch_transpose = f"{curr_track.transpose} ({root_note})"
            if curr_track.transpose > 0:
                pitch_transpose = "+" + pitch_transpose
            scale_mode = scales.SCALES[curr_track.scale]["name"]
            is_muted = "N" if not curr_track.is_muted else "Y"
            is_soloed = "N" if not curr_track.is_soloed else "Y"

            textbox_items = [midi_channel, length, lpb, swing, pitch_transpose, scale_mode, is_muted, is_soloed]

            for i, item in enumerate(textbox_items):
                assert i < 8
                x_position = int((self.textbox_x + 40) - (len(item) * 4))
                if i == self.cursor_y:
                    text_color = themeing.BLACK
                    bg_color = themeing.CURSOR_COLOR if editor_active else themeing.CURSOR_COLOR_ALT
                else:
                    text_color, bg_color = themeing.WHITE, self.bg

                self.to_render[i] = [[RECT, bg_color, self.textbox_x, self.y_positions[i],
                                      self.cell_w, self.cell_h, 0],
                                     [TEXT, "textbox_font", text_color, item,
                                      x_position, self.y_positions[i] - 1, 0]]

        self.title = f"{self.name} {tracker.pages[PATTERN].cursor_x + 1}"
        super().update_view(tracker, editor_active)

        self.check_redraw(tracker.renderer.render_queue)
