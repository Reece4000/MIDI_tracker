from config.pages import *
from config import constants, display, events, render_map, themeing
from config.constants import FOLLOW_MASTER, FOLLOW_PATTERN
from src.gui_elements import PatternCell, TrackBox
from src.ui_components.view_component import ViewComponent
from src.utils import timing_decorator


def get_pattern_index(y_screen, y_pattern):
    if not constants.center_y_cursor:
        return y_pattern + (y_screen // display.visible_rows) * display.visible_rows
    else:
        return (y_pattern - display.center_y) + y_screen


class PatternEditor(ViewComponent):

    def __init__(self, tracker, row_number_cells):
        super().__init__(tracker)

        self.active = True  # start on pattern
        self.page_active_coords = display.pattern_page_border
        self.master_track_view = None  # need to share some state variables with the master
        self.y_anchor = FOLLOW_PATTERN
        self.state_changed = [1] * 8

        self.track_boxes = [TrackBox(x, parent=self) for x in range(constants.track_count)]
        self.cells = [[PatternCell(x, y, parent=self) for y in range(display.visible_rows)] for x in range(constants.track_count)]
        self.row_number_cells = row_number_cells

        self.tracker.event_bus.subscribe(events.NOTE_PLAYED, self.note_played)
        self.tracker.event_bus.subscribe(events.PATTERN_TRACK_STATE_CHANGED, self.flag_track_state_change)
        self.tracker.event_bus.subscribe(events.ALL_STATES_CHANGED, self.flag_state_change)

    def note_played(self, track_index):
        self.track_boxes[track_index].highlight = 255

    def flag_track_state_change(self, x):
        self.state_changed[x] = 1

    def flag_state_change(self):
        self.selected_rows = self.get_selected_rows()
        self.selected_tracks = self.get_selected_tracks()
        self.state_changed = [1] * 8
        if not self.master_track_view.state_changed:
            self.master_track_view.state_changed = True

    def handle_select(self):
        step = self.tracker.cursor_pattern.midi_tracks[self.cursor_x].steps[self.cursor_y]
        x, y, w, h = self.get_selection_coords()
        if w == 0 and h == 0:
            if step.notes == constants.empty:
                self.add_note(step, 0)
            else:
                if step.notes[0] != -1 and step.notes[0] is not None:
                    self.tracker.last_note, self.tracker.last_vel = step.notes[0], step.velocities[0]
            self.tracker.preview_step()

    def add_note(self, step, position, note=None, vel=None):
        if note is None:
            note = self.tracker.last_note
        else:
            self.tracker.last_note = note

        if vel is None:
            vel = self.tracker.last_vel
        else:
            self.tracker.last_vel = vel

        step.update_note(position, note)
        step.update_velocity(position, vel)

    def handle_delete(self, remove_steps):
        x, y, w, h = self.get_selection_coords()

        for track_index in range(w + 1):
            track = self.tracker.cursor_pattern.midi_tracks[x + track_index]
            if self.cursor_y >= track.length:
                continue

            steps_to_remove = []

            for row in range(h + 1):
                step = track.steps[y + row]
                if remove_steps:
                    steps_to_remove.append(y + row)
                elif not step.has_data():
                    if h == 0:
                        step.all_notes_off()
                else:
                    step.clear()

            if remove_steps:
                track.remove_steps(steps_to_remove)
                if self.cursor_y >= track.length:
                    self.cursor_y = track.length - 1
                if y + h >= track.length:
                    self.cursor_h = (y + h) - track.length

    def handle_insert(self):
        x, y, w, h = self.get_selection_coords()
        for track in range(w + 1):
            track = self.tracker.cursor_pattern.midi_tracks[x + track]
            track.insert_steps(self.cursor_y, h + 1)
            track.length = len(track.steps)
            track.length_in_ticks = track.length * (96 // track.lpb)

    def handle_param_adjust(self, increment):
        self.pattern_transpose(increment)

    def update_vel(self, val, preview=True):
        if val == 0:
            return
        x, y, w, h = self.get_selection_coords()
        for track in range(w + 1):
            for row in range(h + 1):
                step = self.tracker.cursor_pattern.midi_tracks[x + track].steps[y + row]
                for i in range(constants.max_polyphony):
                    curr_vel = step.velocities[i]
                    if curr_vel is not None:
                        if val > 0:
                            new_vel = min(127, int(curr_vel) + val)
                        else:
                            new_vel = max(0, int(curr_vel) + val)

                        self.tracker.last_vel = step.update_velocity(i, new_vel)

                    if preview and w == 0 and h == 0:  # only preview if single cell
                        self.tracker.preview_step()

    def pattern_transpose(self, increment):
        n = self.tracker.last_note
        x, y, w, h = self.get_selection_coords()
        for track_index in range(w + 1):
            track = self.tracker.cursor_pattern.midi_tracks[x + track_index]
            for row in range(h + 1):
                step = track.steps[y + row]
                n = step.transpose(increment)

        if w == 0 and h == 0:  # only preview if single cell
            self.tracker.preview_step()
        if n is not None and n != -1:
            self.tracker.last_note = n

    def move_in_place(self, x, y):
        xpos, ypos, w, h = self.get_selection_coords()
        tracks = self.tracker.cursor_pattern.midi_tracks
        sel_track = tracks[self.cursor_x]

        if y > 0:  # Moving down
            add = (-self.cursor_h if self.cursor_h < 0 else 0)
            if self.cursor_y + add >= sel_track.length - 1:
                return
            for track_index in range(w + 1):
                tr = tracks[xpos + track_index]
                for row in reversed(range(h + 1)):
                    pos = ypos + row
                    if pos + y < len(tr.steps):
                        tr.steps[pos], tr.steps[pos + y] = tr.steps[pos + y], tr.steps[pos]

            if self.cursor_y + y >= sel_track.length:
                self.cursor_y = sel_track.length - 1
            else:
                self.cursor_y += y

        elif y < 0:  # Moving up
            add = (0 if self.cursor_h < 0 else -self.cursor_h)
            if self.cursor_y + add <= 0:
                return
            for track_index in range(w + 1):
                tr = tracks[xpos + track_index]
                for row in range(h + 1):
                    pos = ypos + row
                    if tr.length > pos + y >= 0:
                        try:
                            tr.steps[pos], tr.steps[pos + y] = tr.steps[pos + y], tr.steps[pos]
                        except Exception as e:
                            print(f"Error; move in place: {e}", self.cursor_y, pos, pos + y)

            self.cursor_y = 0 if self.cursor_y + y < 0 else self.cursor_y + y
            if self.cursor_y + y >= sel_track.length:
                self.cursor_y = sel_track.length - 1

        if x > 0:  # Moving right
            for track_index in reversed(range(w + 1)):
                add = (-self.cursor_w if self.cursor_w < 0 else 0)
                if self.cursor_x + add >= len(tracks) - 1:
                    return
                else:
                    inc = 0 if self.cursor_h > 0 else -self.cursor_h
                    if self.cursor_y + inc >= tracks[self.cursor_x + x].length:
                        return
                curr_tr = tracks[xpos + track_index]
                nxt_tr = tracks[xpos + track_index + x]
                for row in range(h + 1):
                    pos = ypos + row
                    if pos < len(curr_tr.steps) and pos < len(nxt_tr.steps):
                        curr_tr.steps[pos], nxt_tr.steps[pos] = nxt_tr.steps[pos], curr_tr.steps[pos]
            self.cursor_x += x

        elif x < 0:  # Moving left
            add = (0 if self.cursor_w < 0 else -self.cursor_w)
            if self.cursor_x + add <= 0:
                return
            elif self.cursor_y + (0 if self.cursor_h > 0 else -self.cursor_h) >= tracks[self.cursor_x + x].length:
                return
            for tr_index in range(w + 1):
                curr_tr = tracks[xpos + tr_index]
                prev_tr = tracks[xpos + tr_index + x]
                for row in range(h + 1):
                    pos = ypos + row
                    if pos < len(curr_tr.steps) and pos < len(prev_tr.steps):
                        curr_tr.steps[pos], prev_tr.steps[pos] = prev_tr.steps[pos], curr_tr.steps[pos]
            self.cursor_x += x

        self.flag_state_change()

    def handle_copy(self):
        x, y, w, h = self.get_selection_coords()
        self.clipboard = [
            [
                self.tracker.cursor_pattern.midi_tracks[x + track].steps[y + row]
                for row in range(h + 1)
            ]
            for track in range(w + 1)
        ]

    def handle_paste(self):
        if not self.clipboard:
            return
        sel_track = self.tracker.get_selected_track()
        max_x = min(len(self.clipboard), constants.track_count - self.cursor_x)
        max_y = min(len(self.clipboard[0]), sel_track.length - self.cursor_y)
        for x in range(max_x):
            track = self.tracker.cursor_pattern.midi_tracks[self.cursor_x + x]
            for y in range(max_y):
                step = track.steps[self.cursor_y + y]
                clipboard_step = self.clipboard[x][y]

                # Copy notes, velocities, and components directly
                step.notes[:] = clipboard_step.notes
                step.velocities[:] = clipboard_step.velocities
                step.components[:] = clipboard_step.components
                step.state_changed = True
                step.clear_display_cache()

    def move_cursor(self, x, y, expand_selection=False):
        prev_x, prev_y = self.cursor_x, self.cursor_y
        if x != 0:
            self.cursor_x = max(min(constants.track_count - 1, self.cursor_x + x), 0)

        if y != 0:
            max_len = self.tracker.cursor_pattern.midi_tracks[self.cursor_x].length - 1
            self.cursor_y = max(0, min(max_len, self.cursor_y + y))

        if expand_selection and not (self.tracker.is_playing and self.tracker.follow_playhead):
            self.cursor_w += self.cursor_x - prev_x
            self.cursor_h += self.cursor_y - prev_y

        if not expand_selection:
            self.cursor_w, self.cursor_h = 0, 0

        self.flag_state_change()
        self.tracker.event_bus.publish(events.DETAIL_WINDOW_STATE_CHANGED)

    def get_selection_coords(self):
        xs, ys = self.cursor_w, self.cursor_h
        y_cursor = self.cursor_y
        x = self.cursor_x - xs if xs > 0 else self.cursor_x
        y = y_cursor - ys if ys > 0 else y_cursor
        h = max((y_cursor - ys), y_cursor) - min((y_cursor - ys), y_cursor)
        w = max((self.cursor_x - xs), self.cursor_x) - min((self.cursor_x - xs), self.cursor_x)

        return x, y, w, h

    def get_selected_tracks(self):
        x, xs = self.cursor_x, self.cursor_w
        x = x - xs if xs > 0 else x
        w = max((x - xs), x) - min((x - xs), x) + 1
        return [i for i in range(x, x + w)]

    def get_selected_rows(self):
        y, ys = self.cursor_y, self.cursor_h
        y = y - ys if ys > 0 else y
        h = max((y - ys), y) - min((y - ys), y) + 1
        return [i for i in range(y, y + h)]

    def handle_duplicate(self):
        self.master_track_view.state_changed = True
        x, y, w, h = self.get_selection_coords()
        self.state_changed = [1] * 8
        for track in range(w + 1):
            track = self.tracker.cursor_pattern.midi_tracks[x + track]
            for row in range(h + 1):
                orig_step = track.steps[y + row]
                if y + row + (h + 1) < self.tracker.cursor_pattern.midi_tracks[self.cursor_x].length:
                    dupe_step = track.steps[y + row + (h + 1)]
                    dupe_step.flag_state_change()
                    dupe_step.notes[:] = orig_step.notes
                    dupe_step.velocities[:] = orig_step.velocities
                    dupe_step.components[:] = orig_step.components

        # update cursor_y and h
        max_len = self.tracker.cursor_pattern.midi_tracks[self.cursor_x].length
        if self.cursor_h < 0:
            if not self.cursor_y + (h + 1) * 2 < max_len:
                print("Cond 1.1", self.cursor_y, self.cursor_h, max_len, h)
                if self.cursor_y + h + 1 < max_len:
                    self.cursor_y += h + 1
                    self.cursor_h = -1 * (max_len - 1 - self.cursor_y)
                else:
                    self.cursor_y = max_len - 1
                    self.cursor_h = 0
            else:
                print("Cond 1.2", self.cursor_y, self.cursor_h, max_len, h)
                self.cursor_y += h + 1

        elif self.cursor_y + h + 1 < max_len:
            print("Cond 2", self.cursor_y, self.cursor_h, max_len, h)
            self.cursor_y += h + 1

        elif self.cursor_y + h >= max_len - 1:
            print("Cond 3", self.cursor_y, self.cursor_h, max_len, h)
            self.cursor_y = max_len - 1
            self.cursor_h = max_len - 1 - self.cursor_y

        else:
            # think the above should cover all cases but just in case
            print(f"Duplication issue: {self.cursor_y}, {self.cursor_h}"
                  f", {self.tracker.cursor_pattern.length}, {h}")

    def seek(self, opt, expand_selection):
        self.state_changed[self.cursor_x] = 1
        self.master_track_view.state_changed = True
        delta_x, delta_y = 0, 0
        if opt == 'left':
            delta_x = 0 - self.cursor_x
            for x in range(self.cursor_x, 0):
                self.state_changed[x] = 1
            self.cursor_x = 0

        elif opt == 'right':
            delta_x = constants.track_count - 1 - self.cursor_x
            for x in range(self.cursor_x + 1, constants.track_count - 1):
                self.state_changed[x] = 1
            self.cursor_x = constants.track_count - 1

        elif opt == 'up':
            if self.cursor_y > 0:
                self.cursor_y -= 1
                delta_y -= 1
                track = self.tracker.cursor_pattern.midi_tracks[self.cursor_x]
                while track.steps[self.cursor_y].note is None:
                    if self.cursor_y == 0:
                        break
                    delta_y -= 1
                    self.cursor_y -= 1

        elif opt == 'down':
            if self.cursor_y < self.tracker.cursor_pattern.midi_tracks[self.cursor_x].length - 1:
                self.cursor_y, delta_y = self.cursor_y + 1, 1
                track = self.tracker.cursor_pattern.midi_tracks[self.cursor_x]
                while not track.steps[self.cursor_y].has_data():
                    if self.cursor_y == self.tracker.cursor_pattern.midi_tracks[self.cursor_x].length - 1:
                        break
                    self.cursor_y += 1
                    delta_y += 1

        if expand_selection and not (self.tracker.is_playing and self.tracker.follow_playhead):
            self.cursor_w += delta_x
            self.cursor_h += delta_y

    def update_y_anchor(self, current_page_index):
        if current_page_index == PATTERN:
            self.y_anchor = self.master_track_view.y_anchor = FOLLOW_PATTERN
        elif current_page_index == MASTER:
            self.y_anchor = self.master_track_view.y_anchor = FOLLOW_MASTER

    def update_row_number_view(self, pattern, y_cursor, render_queue):
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
            master_track = pattern.master_track
            master_len = master_track.length
            if self.tracker.on_playing_pattern:
                playhead_step = master_track.step_pos

        for row_number_cell in self.row_number_cells:
            step_index = get_pattern_index(y_cursor, row_number_cell.y)
            row_number_cell.check_for_state_change(n_steps, step_index, self.selected_rows,
                                                   master_len, playhead_step, render_queue)

    def update_pattern_view(self, pattern, render_queue):
        assert self.master_track_view is not None

        y = self.master_track_view.cursor_y if self.y_anchor == FOLLOW_MASTER else self.cursor_y

        for x, column in enumerate(self.cells):
            track = None if pattern is None else pattern.midi_tracks[x]
            if track is not None and self.tracker.on_playing_pattern:
                playhead_step = track.step_pos
            else:
                playhead_step = None

            for cell in column:
                step_index = get_pattern_index(y, cell.y)
                if self.state_changed[x] or track is None:
                    re_render = True
                elif 0 <= step_index <  track.length:
                    re_render = track.steps[step_index].state_changed
                    # set flag to false here so that we don't have to redo the conditional
                    track.steps[step_index].state_changed = False
                else:
                    re_render = False

                if re_render:
                    cell.check_for_state_change(pattern, step_index, track, x, playhead_step, render_queue)

    def update_view(self):
        pattern = self.tracker.cursor_pattern
        render_queue = self.tracker.renderer.render_queue

        self.update_row_number_view(pattern, self.cursor_y, render_queue)
        self.update_pattern_view(pattern, render_queue)
        for index, track_box in enumerate(self.track_boxes):
            track_box.check_for_state_change(index, self.tracker.page, pattern, self.selected_tracks, render_queue)

        self.state_changed = [0] * 8



