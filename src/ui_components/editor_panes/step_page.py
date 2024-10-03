from src.ui_components.editor_panes.menu_page import MenuPage
from src.utils import midi_to_note
from config.render_map import *
from config.pages import PATTERN
from config import themeing


class StepPage(MenuPage):
    def __init__(self, x, y, tracker):
        super().__init__(x, y, "STEP", tracker)
        self.clipboard = {"note": None, "component": None, "value": None}
        self.image = self.tracker.renderer.load_image(r"resources\editor_panes\step_page.png")
        self.title_bg_selected = themeing.STEP_TITLE_SELECTED
        self.title_bg_unselected = themeing.STEP_TITLE_UNSELECTED

        self.notes_y = [self.y + 66, self.y + 88, self.y + 110, self.y + 132]
        self.note_x, self.vel_x = self.x + 72, self.x + 127
        self.note_w, self.vel_w = 50, 41

        self.components_y = [188, 210, 232, 254]
        self.components_x, self.components_p1_x, self.components_p2_x = self.x + 53, self.x + 111, self.x + 159
        self.components_w, self.components_p1_w, self.components_p2_w = 49, 39, 39

        self.cc_y = [308, 330, 352, 374, 401, 423, 445, 467]
        self.cc_x1, self.cc_val_x1, self.cc_x2, self.cc_val_x2 = self.x + 22, self.x + 80, self.x + 131, self.x + 189
        self.cc_control_w, self.cc_val_w = 51, 42

    def move_cursor(self, x, y):
        def get_max_x(curs_y):
            return 3 if curs_y > 7 else 2 if curs_y > 3 else 1

        if x != 0:
            self.cursor_x = max(min(get_max_x(self.cursor_y), self.cursor_x + x), 0)
        if y != 0:
            self.cursor_y = (self.cursor_y + y) % 16
            self.cursor_x = max(min(get_max_x(self.cursor_y), self.cursor_x), 0)

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
            if self.cursor_x in [0, 2]:
                ccs = self.tracker.channel_ccs[sel_track_index]
                cc_control_index = self.cursor_y if self.cursor_x == 2 else self.cursor_y - 8
                if ccs[cc_control_index] is not None:
                    self.tracker.last_cc = ccs[cc_control_index]
                else:
                    cc_to_insert = self.tracker.last_cc
                    self.tracker.update_channel_ccs(sel_track_index, cc_control_index, cc_to_insert)
            if self.cursor_x in [1, 3]:
                cc_val_index = self.cursor_y if self.cursor_x == 3 else self.cursor_y - 8
                if step.ccs[cc_val_index] is not None:
                    self.tracker.last_cc_val = step.ccs[self.cursor_y - 8]
                else:
                    step.update_cc(cc_val_index, self.tracker.last_cc_val)
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

    def handle_copy(self):
        if self.cursor_y < 4:
            step = self.tracker.get_selected_step()
            if self.cursor_x == 0:
                self.clipboard["note"] = step.notes[self.cursor_y]
            elif self.cursor_x == 1:
                self.clipboard["value"] = step.velocities[self.cursor_y]
        elif 4 <= self.cursor_y < 8:
            step = self.tracker.get_selected_step()
            if self.cursor_x == 0:
                self.clipboard["component"] = step.components[self.cursor_y - 4]
            else:
                self.clipboard["value"] = step.components[self.cursor_y - 4]
        elif self.cursor_y >= 8:
            sel_track_index = self.tracker.pages[PATTERN].cursor_x
            if self.cursor_x in [0, 2]:
                cc_index = self.cursor_y if self.cursor_x == 2 else self.cursor_y - 8
                self.clipboard["value"] = self.tracker.channel_ccs[sel_track_index][cc_index]
            elif self.cursor_x in [1, 3]:
                cc_index = self.cursor_y - 8
                self.clipboard["value"] = self.tracker.get_selected_step().ccs[cc_index]

    def handle_param_adjust(self, increment, axis=False):
        step = self.tracker.get_selected_step()
        if self.cursor_y < 4:
            self.adjust_note(step, self.cursor_y, increment, preview=(not axis))
        elif 4 <= self.cursor_y < 8:
            self.adjust_component(step, self.cursor_y - 4, increment, preview=(not axis))
        elif self.cursor_y >= 8:
            cc_index = self.cursor_y - 8 if self.cursor_x in [0, 1] else self.cursor_y
            self.adjust_cc(step, cc_index, increment, preview=(not axis))

    def adjust_note(self, step, note_index, increment, preview=True):
        if step.notes[note_index] is not None:
            if self.cursor_x == 0:
                new_note = max(min(131, step.notes[note_index] + increment), 0)
                self.tracker.last_note = step.update_note(note_index, new_note)
            elif self.cursor_x == 1:
                increment = 10 if increment == 12 else (-10 if increment == -12 else increment)
                new_vel = max(min(127, step.velocities[note_index] + increment), 0)
                self.tracker.last_vel = step.update_velocity(note_index, new_vel)
        if preview:
            self.tracker.preview_step(notes_only=True)

    def adjust_component(self, step, component_index, increment, preview=True):
        pass

    def adjust_cc(self, step, cc_index, increment, preview=True):
        sel_track_index = self.tracker.pages[PATTERN].cursor_x
        increment = 10 if increment == 12 else (-10 if increment == -12 else increment)
        if self.cursor_x in [0, 2]:
            current_cc = self.tracker.channel_ccs[sel_track_index][cc_index]
            if current_cc is not None:
                new = max(min(127, current_cc + increment), 1)
                self.tracker.update_channel_ccs(sel_track_index, cc_index, new)
        elif self.cursor_x in [1, 3]:
            if step.ccs[cc_index] is not None:
                new_cc_val = max(min(127, step.ccs[cc_index] + increment), 0)
                self.tracker.last_cc_val = step.update_cc(cc_index, new_cc_val)
            else:
                step.update_cc(cc_index, self.tracker.last_cc_val)
            self.tracker.midi_handler.send_cc(sel_track_index, cc_index + 1, self.tracker.last_cc_val)

        if preview:
            self.tracker.preview_step(notes_only=True)

    def draw_notes(self, step, sel_table, is_active):
        for i, note in enumerate(step.notes):

            note_text = midi_to_note(note) if note is not None else "---"

            if sel_table == 0 and self.cursor_y == i and self.cursor_x == 0:
                text_col = themeing.BLACK
                bg_col = themeing.CURSOR_COLOR if is_active else themeing.CURSOR_COLOR_ALT
            else:
                if note_text == "OFF":
                    bg_col, text_col = self.bg, themeing.NOTE_OFF_COLOR
                else:
                    bg_col, text_col = self.bg, themeing.NOTE_COLOR

            self.to_render[(i, 0)] = [[RECT, bg_col, self.note_x - 3, self.notes_y[i], self.note_w, self.cell_h, 0],
                                      [TEXT, "textbox_font", text_col, note_text, self.note_x + 11, self.notes_y[i], 0]]

            if note_text == "OFF":
                vel_text = ""
            else:
                vel_text = f'{step.velocities[i]: >3}' if step.velocities[i] is not None else "---"

            if sel_table == 0 and self.cursor_y == i and self.cursor_x == 1:
                text_col = themeing.BLACK
                bg_col = themeing.CURSOR_COLOR if is_active else themeing.CURSOR_COLOR_ALT
            else:
                bg_col, text_col = self.bg, themeing.VELOCITY_COLOR

            self.to_render[(i, 1)] = [[RECT, bg_col, self.vel_x, self.notes_y[i], self.vel_w, self.cell_h, 0],
                                      [TEXT, "textbox_font", text_col, vel_text, self.vel_x + 9, self.notes_y[i], 0]]

    def draw_components(self, step, sel_table, is_active):
        for i, component in enumerate(step.components):
            if component is None:
                component_text = component_p1_text = component_p2_text = "---"
            else:
                component_text = f"{component[i][0]}"
                component_p1_text = f"{component[i][1]}"
                component_p2_text = f"{component[i][2]}"

            if sel_table == 1 and self.cursor_y == i + 4 and self.cursor_x == 0:
                text_col = themeing.BLACK
                bg_col = themeing.CURSOR_COLOR if is_active else themeing.CURSOR_COLOR_ALT
            else:
                bg_col, text_col = self.bg, themeing.COMPONENT_COLOR

            self.to_render[(i + 4, 0)] = [[RECT, bg_col, self.components_x - 3, self.components_y[i], 52, 16, 0],
                                          [TEXT, "textbox_font", text_col, component_text,
                                           self.components_x + 11, self.components_y[i], 0]]

            if sel_table == 1 and self.cursor_y == i + 4 and self.cursor_x == 1:
                text_col = themeing.BLACK
                bg_col = themeing.CURSOR_COLOR if is_active else themeing.CURSOR_COLOR_ALT
            else:
                bg_col, text_col = self.bg, themeing.COMPONENT_PARAM1_COLOR

            self.to_render[(i + 4, 1)] = [[RECT, bg_col, self.components_p1_x - 3, self.components_y[i], 42, 16, 0],
                                          [TEXT, "textbox_font", text_col, component_p1_text,
                                           self.components_p1_x + 6, self.components_y[i], 0]]

            if sel_table == 1 and self.cursor_y == i + 4 and self.cursor_x == 2:
                text_col = themeing.BLACK
                bg_col = themeing.CURSOR_COLOR if is_active else themeing.CURSOR_COLOR_ALT
            else:
                bg_col, text_col = self.bg, themeing.COMPONENT_PARAM2_COLOR

            self.to_render[(i + 4, 2)] = [[RECT, bg_col, self.components_p2_x - 3, self.components_y[i], 42, 16, 0],
                                          [TEXT, "textbox_font", text_col, component_p2_text,
                                           self.components_p2_x + 6, self.components_y[i], 0]]

    def draw_ccs(self, step, sel_table, is_active, channel_ccs):
        def get_colors(sel_table, is_active, i, x, is_control=True):
            cell_selected = sel_table == 2 and self.cursor_y == i and self.cursor_x == x
            if cell_selected:
                text_col = themeing.BLACK
                bg_col = themeing.CURSOR_COLOR if is_active else themeing.CURSOR_COLOR_ALT
            else:
                bg_col, text_col = self.bg, themeing.CC_CONTROL_COLOR if is_control else themeing.CC_VALUE_COLOR
            return text_col, bg_col

        for i in range(8):
            cc_control_text_left = f"{channel_ccs[i]:0>3}" if channel_ccs is not None else "---"
            cc_value_text_left = f"{step.ccs[i]:0>3}" if step.ccs[i] is not None else "---"
            cc_control_text_right = f"{channel_ccs[i + 8]:0>3}" if channel_ccs is not None else "---"
            cc_value_text_right = f"{step.ccs[i + 8]:0>3}" if step.ccs[i + 8] is not None else "---"

            text_col, bg_col = get_colors(sel_table, is_active, i + 8, 0)
            self.to_render[(i + 8, 0)] = [[RECT, bg_col, self.cc_x1 - 3, self.cc_y[i],
                                           self.cc_control_w, self.cell_h, 0],
                                          [TEXT, "textbox_font", text_col, cc_control_text_left,
                                           self.cc_x1 + 11, self.cc_y[i], 0]]

            text_col, bg_col = get_colors(sel_table, is_active, i + 8, 1, is_control=False)
            self.to_render[(i + 8, 1)] = [[RECT, bg_col, self.cc_val_x1 - 3, self.cc_y[i],
                                           self.cc_val_w, self.cell_h, 0],
                                          [TEXT, "textbox_font", text_col, cc_value_text_left,
                                           self.cc_val_x1 + 6, self.cc_y[i], 0]]

            text_col, bg_col = get_colors(sel_table, is_active, i + 8, 2)
            self.to_render[(i + 8, 2)] = [[RECT, bg_col, self.cc_x2 - 3, self.cc_y[i],
                                           self.cc_control_w, self.cell_h, 0],
                                          [TEXT, "textbox_font", text_col, cc_control_text_right,
                                           self.cc_x2 + 11, self.cc_y[i], 0]]

            text_col, bg_col = get_colors(sel_table, is_active, i + 8, 3, is_control=False)
            self.to_render[(i + 8, 3)] = [[RECT, bg_col, self.cc_val_x2 - 3, self.cc_y[i],
                                           self.cc_val_w, self.cell_h, 0],
                                          [TEXT, "textbox_font", text_col, cc_value_text_right,
                                           self.cc_val_x2 + 6, self.cc_y[i], 0]]

    def update_view(self, tracker, editor_active):
        step = tracker.get_selected_step()
        if step is None:
            # set cells to empty or n/a here
            pass

        step_index = tracker.pages[PATTERN].cursor_y
        self.title = f"{self.name} {step_index}"
        super().update_view(tracker, editor_active)

        if self.active:
            sel_table = 2 if self.cursor_y > 7 else 1 if self.cursor_y > 3 else 0
            self.draw_notes(step, sel_table, editor_active)
            self.draw_components(step, sel_table, editor_active)

            curr_track = tracker.get_selected_track()
            channel_ccs = tracker.channel_ccs[curr_track.channel] if curr_track is not None else None
            self.draw_ccs(step, sel_table, editor_active, channel_ccs)

        self.check_redraw(tracker.renderer.render_queue)
