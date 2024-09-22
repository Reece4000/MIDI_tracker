from src.ui_components.view_component import ViewComponent
from src.gui_elements import KeyHints, TextBox, Button
from config import constants, display, themeing, events
from config.render_map import *
from config.pages import *
from src.utils import midi_to_note



class EditorWindow(ViewComponent):
    def __init__(self, tracker):
        super().__init__(tracker)
        self.previous_page = PATTERN
        self.x_pos = display.track_x_positions[7] + 100
        self.y_pos = 2
        self.title_h = 28
        self.w = 250
        self.h = 702

        self.title = TextBox(self.x_pos, self.y_pos, self.w, 28, "Editor", "zoom_font",
                             themeing.BG_SEP, themeing.BG_COLOR)

        self.key_hints = KeyHints()
        self.tracker.event_bus.subscribe(events.DETAIL_WINDOW_STATE_CHANGED, self.flag_state_change)

    def handle_select(self):
        step = self.tracker.get_selected_step()
        sel_track_index = self.tracker.pages[PATTERN].cursor_x
        if self.cursor_y < 4:
            if self.cursor_x == 0:
                if step.notes[self.cursor_y] is None:
                    step.add_note(self.cursor_y, self.tracker.last_note, self.tracker.last_vel)
                else:
                    if step.notes[self.cursor_y] != -1:
                        self.tracker.last_note = step.notes[self.cursor_y]
            elif self.cursor_x == 1:
                if step.velocities[self.cursor_y] is not None:
                    if step.notes[self.cursor_y] != -1:
                        self.tracker.last_vel = step.velocities[self.cursor_y]
        elif self.cursor_y >= 8:
            cc_index = self.cursor_y - 8
            ccs = self.tracker.channel_ccs[sel_track_index]
            if self.cursor_x == 0:
                if ccs[cc_index] is not None:
                    self.tracker.last_cc = ccs[cc_index]
                else:
                    cc_to_insert = self.tracker.last_cc
                    while cc_to_insert in self.tracker.channel_ccs[sel_track_index]:
                        cc_to_insert += 1
                        if cc_to_insert == 127:
                            cc_to_insert = 1
                    self.tracker.update_channel_ccs(sel_track_index, cc_index, cc_to_insert)
            if self.cursor_x == 1:
                if step.ccs[self.cursor_y - 8] is not None:
                    self.tracker.last_cc_val = step.ccs[self.cursor_y - 8]
                else:
                    step.update_cc(self.cursor_y - 8, self.tracker.last_cc_val)
        return 1

    def handle_delete(self, remove_steps):
        step = self.tracker.get_selected_step()
        sel_track_index = self.tracker.pages[PATTERN].cursor_x
        if self.cursor_y < 4:
            if self.cursor_x == 0:
                if step.notes[self.cursor_y] is not None:
                    step.update_note(self.cursor_y, None)
                    step.update_velocity(self.cursor_y, None)
                else:
                    step.update_note(self.cursor_y, -1)
                    step.update_velocity(self.cursor_y, 0)
            elif self.cursor_x == 1:
                if step.velocities[self.cursor_y] is not None:
                    step.update_velocity(self.cursor_y, 0)

        elif self.cursor_y >= 8:
            cc_index = self.cursor_y - 8
            if self.cursor_x == 0:
                self.tracker.update_channel_ccs(sel_track_index, cc_index, None)
            elif self.cursor_x == 1:
                if step.ccs[cc_index] > 0:
                    step.update_cc(cc_index, 0)
                else:
                    step.update_cc(cc_index, None)

    def handle_insert(self):
        pass

    def adjust_note(self, step, note_index, increment):
        if step.notes[note_index] is not None:
            if self.cursor_x == 0:
                new_note = max(min(131, step.notes[note_index] + increment), 0)
                self.tracker.last_note = step.update_note(note_index, new_note)
            elif self.cursor_x == 1:
                increment = 10 if increment == 12 else (-10 if increment == -12 else increment)
                new_vel = max(min(99, step.velocities[note_index] + increment), 0)
                self.tracker.last_vel = step.update_velocity(note_index, new_vel)
        self.tracker.preview_step()

    def adjust_component(self, step, component_index, increment):
        self.tracker.preview_step()

    def adjust_cc(self, step, cc_index, increment):
        sel_track_index = self.tracker.pages[PATTERN].cursor_x
        increment = 10 if increment == 12 else (-10 if increment == -12 else increment)
        if self.cursor_x == 0:
            current_cc = self.tracker.channel_ccs[sel_track_index][cc_index]
            if current_cc is not None:
                new = max(min(127, current_cc + increment), 1)
                while new in self.tracker.channel_ccs[sel_track_index]:
                    if increment == -10 or increment == 10:
                        increment //= 10
                    new = max(min(127, new + increment), 1)
                    if new == 1 or new == 127:
                        return
                self.tracker.update_channel_ccs(sel_track_index, cc_index, new)
        elif self.cursor_x == 1:
            if step.ccs[cc_index] is not None:
                new_cc_val = max(min(127, step.ccs[cc_index] + increment), 0)
                self.tracker.last_cc_val = step.update_cc(cc_index, new_cc_val)
            else:
                step.update_cc(cc_index, self.tracker.last_cc_val)
        self.tracker.preview_step()

    def handle_param_adjust(self, increment):
        step = self.tracker.get_selected_step()
        if self.cursor_y < 4:
            self.adjust_note(step, self.cursor_y, increment)
        elif 4 <= self.cursor_y < 8:
            self.adjust_component(step, self.cursor_y - 4, increment)
        elif self.cursor_y >= 8:
            self.adjust_cc(step, self.cursor_y - 8, increment)

    def move_in_place(self, x, y):
        pass

    def handle_copy(self):
        pass

    def handle_paste(self):
        pass

    def move_cursor(self, x, y, expand_selection=False):
        if self.active:
            print("editor window active")
        def get_max_x(curs_y):
            if curs_y > 7:
                return 2
            elif curs_y > 3:
                return 3
            else:
                return 2

        if x != 0:
            self.cursor_x = max(min(get_max_x(self.cursor_y), self.cursor_x + x), 0)
        if y != 0:
            self.cursor_y = (self.cursor_y + y) % 16
        self.cursor_x %= get_max_x(self.cursor_y)
        self.flag_state_change()

    def render_key_hints(self):
        render_queue = self.tracker.renderer.render_queue
        items = [[" U ", " D ", " L ", " R "], ["PLY", "ADD", "SEL", "DEL"]]
        elems_to_render = self.key_hints.check_for_state_change(items)
        if elems_to_render:
            render_queue.extendleft(elems_to_render)

    def update_view(self):
        if not self.state_changed:
            return

        if not self.active and self.tracker.page != PATTERN:
            return

        render_queue = self.tracker.renderer.render_queue

        color = themeing.CURSOR_COLOR if self.active else themeing.LINE_16_HL_BG
        render_queue.appendleft([RECT, color, self.x_pos, self.y_pos, self.w, self.h, 2])
        render_queue.appendleft([RECT, themeing.BG_COLOR, self.x_pos + 2, self.y_pos + 2,
                                 self.w - 4, display.detail_window_replace_bg_h, 0])

        if self.previous_page == PATTERN:
            track = self.tracker.get_selected_track()
            step = self.tracker.get_selected_step(track)

            render_queue.appendleft([RECT, themeing.LINE_16_HL_BG, self.x_pos + 2, self.y_pos + 2,
                                     self.w - 4, display.detail_window_title_h, 0])

            cursor_x = self.tracker.pages[PATTERN].cursor_x
            cursor_y = self.tracker.pages[PATTERN].cursor_y
            tr = f"{cursor_x}"
            cursor_col = themeing.CURSOR_COLOR if self.tracker.page == EDITOR else themeing.BG_SEP
            text = f"TRK:{tr} STP:{cursor_y}" if step is not None else f"TRK:{tr} STP:--"
            render_queue.appendleft([TEXT, "zoom_font", cursor_col, text, self.x_pos + 12, self.y_pos + 2, 0])

            start_y = 44
            x_pos = self.x_pos + 6
            if not track.is_master:
                if step is not None:
                    render_queue.appendleft([TEXT, "zoom_font", (100, 255, 100), "Notes:", x_pos + 4, start_y, 0])
                    for i, note in enumerate(step.notes):
                        y = start_y + 30 + (29 * i)
                        if note is not None:
                            note_text = midi_to_note(note)
                            vel_text = f'{step.velocities[i]:0>2}'
                        else:
                            note_text = "---"
                            vel_text = "--"
                        render_queue.appendleft([TEXT, "zoom_font", (100, 255, 100), note_text, x_pos + 4, y + 2, 0])
                        render_queue.appendleft([TEXT, "zoom_font", (255, 150, 150), vel_text, x_pos + 77, y + 2, 0])
                        if self.cursor_y == i and self.cursor_x == 0:  # on note
                            render_queue.appendleft([RECT, cursor_col, x_pos, y + 4, 56, 30, 2])
                        elif self.cursor_y == i and self.cursor_x == 1:  # on vel
                            render_queue.appendleft([RECT, cursor_col, x_pos + 70, y + 4, 48, 30, 2])

                    render_queue.appendleft(
                        [TEXT, "zoom_font", (150, 255, 255), "Commands:", x_pos + 4, start_y + (29 * 4) + 36, 0])
                    for i, component in enumerate(step.components):
                        y = start_y + (29 * i) + 184
                        if component is not None:
                            elems = component
                        else:
                            elems = ["---", "--", "--"]

                        render_queue.appendleft([TEXT, "zoom_font", (150, 255, 255), elems[0], x_pos + 4, y, 0])
                        render_queue.appendleft([TEXT, "zoom_font", (255, 150, 255), elems[1], x_pos + 77, y, 0])
                        render_queue.appendleft([TEXT, "zoom_font", (255, 255, 150), elems[2], x_pos + 134, y, 0])

                        if self.cursor_y == i + 4 and self.cursor_x == 0:  # on component
                            render_queue.appendleft([RECT, cursor_col, x_pos, y + 2, 56, 30, 2])
                        elif self.cursor_y == i + 4 and self.cursor_x == 1:  # on p1
                            render_queue.appendleft([RECT, cursor_col, x_pos + 70, y + 2, 48, 30, 2])
                        elif self.cursor_y == i + 4 and self.cursor_x == 2:  # on p2
                            render_queue.appendleft([RECT, cursor_col, x_pos + 127, y + 2, 48, 30, 2])

                    y = start_y + 306

                    track_ccs = self.tracker.channel_ccs[cursor_x]

                    for i in range(8):

                        cc = f"{track_ccs[i]:0>3}" if track_ccs[i] is not None else "---"
                        val = f"{step.ccs[i]:0>3}" if step.ccs[i] is not None else "---"

                        cc_color, val_col = (255, 255, 80), (255, 180, 255)

                        render_queue.appendleft(
                            [TEXT, "tracker_font", (200, 200, 255), f"CC:", x_pos + 8, y + (26 * i) + 13, 0])

                        render_queue.appendleft(
                            [TEXT, "zoom_font", cc_color, f"{cc}", x_pos + 52, y + (26 * i) + 4, 0])
                        render_queue.appendleft(
                            [TEXT, "zoom_font", val_col, f"{val}", x_pos + 120, y + (26 * i) + 4, 0])

                        if self.cursor_y == i + 8:  # col 1
                            if self.cursor_x == 0:
                                render_queue.appendleft([RECT, cursor_col, x_pos + 48, y + (26 * i) + 4, 56, 30, 2])
                            elif self.cursor_x == 1:
                                render_queue.appendleft([RECT, cursor_col, x_pos + 117, y + (26 * i) + 4, 56, 30, 2])

                    p_x, p_y = x_pos + 192, y + 90
                    render_queue.appendleft(
                        [POLYGON, themeing.WHITE, ((p_x, p_y), (p_x + 5, p_y - 5), (p_x + 10, p_y)), 0])
                    render_queue.appendleft(
                        [POLYGON, themeing.WHITE, ((p_x, p_y + 20), (p_x + 5, p_y + 25), (p_x + 10, p_y + 20)), 0])

            self.render_key_hints()

        self.state_changed = False
