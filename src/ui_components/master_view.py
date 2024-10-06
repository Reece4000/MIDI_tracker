from config import display, events
from config.constants import FOLLOW_PATTERN
from src.ui_components.gui_elements import PatternCell, TrackBox
from src.ui_components.view_component import ViewComponent
from src.ui_components.pattern_view import get_pattern_index


# for the master components, in the detail window show the different parameters available

# e.g:
# REVERSE: (is reversed: boolean) track 1, track 2 ...
# SYNCHRONISE: (is synchronised: boolean) track 1, track 2 ...
# REPEAT STEP (is repeating: boolean, num repeats: integer)

class MasterTrack(ViewComponent):
    def __init__(self, tracker, row_number_cells):
        super().__init__(tracker)
        self.page_active_coords = display.master_page_border
        self.track_box = TrackBox(0, parent=self, master=True)
        self.cells = [PatternCell(0, y, parent=self, master=True) for y in range(display.visible_rows)]
        self.y_anchor = FOLLOW_PATTERN
        self.row_number_cells = row_number_cells
        self.selected_tracks = [0]
        self.selected_rows = self.get_selected_rows()
        self.pattern_view = None  # need to share some state variables with the pattern

    def flag_state_change(self):
        super().flag_state_change()
        self.pattern_view.state_changed = [1, 1, 1, 1, 1, 1, 1, 1]

    def move_in_place(self, x, y):
        xpos, ypos, w, h = self.get_selection_coords()
        selected_pattern = self.tracker.get_selected_pattern()
        track = selected_pattern.master_track

        if y > 0:  # Moving down
            add = (-self.cursor_h if self.cursor_h < 0 else 0)
            if self.cursor_y + add >= track.length - 1:
                return
            for row in reversed(range(h + 1)):
                pos = ypos + row
                if pos + y < len(track.steps):
                    track.steps[pos], track.steps[pos + y] = track.steps[pos + y], track.steps[pos]

            if self.cursor_y + y >= track.length:
                self.cursor_y = track.length - 1
            else:
                self.cursor_y += y

        elif y < 0:  # Moving up
            add = (0 if self.cursor_h < 0 else -self.cursor_h)
            if self.cursor_y + add <= 0:
                return
            for row in range(h + 1):
                pos = ypos + row
                if track.length > pos + y >= 0:
                    try:
                        track.steps[pos], track.steps[pos + y] = track.steps[pos + y], track.steps[pos]
                    except Exception as e:
                        print(f"Error; move in place: {e}", self.cursor_y, pos, pos + y)

            self.cursor_y = 0 if self.cursor_y + y < 0 else self.cursor_y + y
            if self.cursor_y + y >= track.length:
                self.cursor_y = track.length - 1

        self.flag_state_change()

    def move_cursor(self, x, y, expand_selection=False):
        prev_y = self.cursor_y
        selected_pattern = self.tracker.get_selected_pattern()
        if y != 0:
            max_len = selected_pattern.master_track.length - 1
            self.cursor_y = max(0, min(max_len, self.cursor_y + y))

        if expand_selection and not (self.tracker.is_playing and self.tracker.follow_playhead):
            self.cursor_h += self.cursor_y - prev_y

        if not expand_selection:
            self.cursor_h = 0

        # print(self.cursor_y, self.cursor_x)

        self.selected_rows = self.get_selected_rows()
        self.flag_state_change()
        self.tracker.event_bus.publish(events.EDITOR_WINDOW_STATE_CHANGED)

    def update_row_number_view(self, pattern, render_queue):
        if not self.active:
            return
        playhead_step = None
        n_steps = 0
        master_len = 0
        if pattern is not None:
            try:
                n_steps = max(track.length for track in pattern.tracks)
            except AttributeError as e:
                print(e, "Attribute error, def render_row_numbers()", pattern)
            master_len = pattern.master_track.length
            if self.tracker.on_playing_pattern:
                playhead_step = pattern.master_track.step_pos

        for row_number_cell in self.row_number_cells:
            step_index = get_pattern_index(self.cursor_y, row_number_cell.y)
            row_number_cell.check_for_state_change(n_steps, step_index, self.selected_rows,
                                                   master_len, playhead_step, render_queue)

    def update_pattern_view(self, pattern, render_queue):
        assert self.pattern_view is not None

        y = self.pattern_view.cursor_y if self.y_anchor == FOLLOW_PATTERN else self.cursor_y

        track = None if pattern is None else pattern.master_track
        for cell in self.cells:
            if track is not None:
                playhead_step = track.step_pos if self.tracker.on_playing_pattern else None
            else:
                playhead_step = None

            step_index = get_pattern_index(y, cell.y)
            if self.state_changed or track is None:
                re_render = True
            elif 0 <= step_index < track.length:
                re_render = track.steps[step_index].state_changed
                # set flag to false here so that we don't have to redo the conditional
                track.steps[step_index].state_changed = False
            else:
                re_render = False

            if re_render:
                cell.check_for_state_change(pattern, step_index, track, 0, playhead_step, render_queue)

    def update_view(self):
        pattern = self.tracker.get_selected_pattern()
        render_queue = self.tracker.renderer.render_queue

        self.update_row_number_view(pattern, render_queue)
        self.update_pattern_view(pattern, render_queue)
        self.track_box.check_for_state_change(0, self.tracker.page, pattern, self.selected_tracks, render_queue)

        self.state_changed = False

