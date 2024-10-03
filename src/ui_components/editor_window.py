from src.ui_components.view_component import ViewComponent
from src.ui_components.gui_elements import KeyHints
from config import display, themeing, events
from config.render_map import *
from config.pages import *
from src.utils import midi_to_note


class MenuPage:
    def __init__(self, x, y, name, tracker):
        self.clipboard = []
        self.tracker = tracker
        self.cursor_x = 0
        self.cursor_y = 0
        self.cell_h = 16
        self.x = x
        self.y = y + 4
        self.y_actual = y
        self.w = 250
        self.h_closed = 35
        self.h_open = 495
        self.h_actual = self.h_closed
        self.active = 0  # closed
        self.name = name
        self.y_offset = 0
        self.h_offset = 0
        self.to_render = {}
        self.previous_render = {}

    def update_view(self, tracker, is_active):
        pass

    def move_cursor(self, x, y):
        pass

    def handle_select(self):
        pass

    def handle_delete(self, remove_steps):
        pass

    def handle_insert(self):
        pass

    def handle_param_adjust(self, increment):
        pass

    def move_in_place(self, x, y):
        pass

    def handle_copy(self):
        pass

    def handle_paste(self):
        pass


class StepPage(MenuPage):
    def __init__(self, x, y, tracker):
        super().__init__(x, y, "STEP", tracker)
        self.clipboard = {"note": None, "component": None, "value": None}
        self.image = self.tracker.renderer.load_image(r"resources\editor_panes\step_page.png")
        self.bg = themeing.BG_TASKPANE
        self.title = f"{self.name} 0"
        self.cursor_x = 0
        self.cursor_y = 0

        self.note_color = (90, 255, 100)
        self.velocity_color = (190, 90, 100)
        self.components_color = (100, 100, 190)
        self.component_p1_color = (50, 190, 190)
        self.component_p2_color = (190, 50, 190)
        self.cc_control_color = (255, 210, 80)
        self.cc_value_color = (70, 200, 180)

        self.note_x = self.x + 72
        self.note_w = 50
        self.vel_x = self.x + 127
        self.vel_w = 41
        self.notes_y = [self.y_actual + 70, self.y_actual + 92, self.y_actual + 114, self.y_actual + 136]

        self.components_x = 1019
        self.components_w = 49
        self.components_p1_x = 1077
        self.components_p1_w = 39
        self.components_p2_x = 1125
        self.components_p2_w = 39
        self.components_y = [188, 210, 232, 254]

        self.cc_control_x1 = 988
        self.cc_val_x1 = 1046
        self.cc_control_x2 = 1097
        self.cc_val_x2 = 1155
        self.cc_control_w = 51
        self.cc_val_w = 42
        self.cc_y = [307, 329, 351, 373, 401, 422, 444, 467]

    def check_redraw(self, render_queue):
        for key, items in self.to_render.items():
            if key in self.previous_render:
                if items != self.previous_render[key]:
                    for item in items:
                        render_queue.appendleft(item)
            else:
                for item in items:
                    render_queue.appendleft(item)

        self.previous_render = self.to_render
        self.to_render = {k: [] for k in self.to_render.keys()}

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
                bg_col, text_col = self.bg, self.note_color

            self.to_render[(i, 0)] = [[RECT, bg_col, self.note_x - 3, self.notes_y[i], self.note_w, self.cell_h, 0],
                                      [TEXT, "textbox_font", text_col, note_text, self.note_x + 11, self.notes_y[i], 0]]

            vel_text = f'{step.velocities[i]: >3}' if step.velocities[i] is not None else "---"

            if sel_table == 0 and self.cursor_y == i and self.cursor_x == 1:
                text_col = themeing.BLACK
                bg_col = themeing.CURSOR_COLOR if is_active else themeing.CURSOR_COLOR_ALT
            else:
                bg_col, text_col = self.bg, self.velocity_color

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
                bg_col, text_col = self.bg, self.components_color

            self.to_render[(i + 4, 0)] = [[RECT, bg_col, self.components_x - 3, self.components_y[i], 52, 16, 0],
                                          [TEXT, "textbox_font", text_col, component_text,
                                           self.components_x + 11, self.components_y[i], 0]]

            if sel_table == 1 and self.cursor_y == i + 4 and self.cursor_x == 1:
                text_col = themeing.BLACK
                bg_col = themeing.CURSOR_COLOR if is_active else themeing.CURSOR_COLOR_ALT
            else:
                bg_col, text_col = self.bg, self.component_p1_color

            self.to_render[(i + 4, 1)] = [[RECT, bg_col, self.components_p1_x - 3, self.components_y[i], 42, 16, 0],
                                          [TEXT, "textbox_font", text_col, component_p1_text,
                                           self.components_p1_x + 6, self.components_y[i], 0]]

            if sel_table == 1 and self.cursor_y == i + 4 and self.cursor_x == 2:
                text_col = themeing.BLACK
                bg_col = themeing.CURSOR_COLOR if is_active else themeing.CURSOR_COLOR_ALT
            else:
                bg_col, text_col = self.bg, self.component_p2_color

            self.to_render[(i + 4, 2)] = [[RECT, bg_col, self.components_p2_x - 3, self.components_y[i], 42, 16, 0],
                                          [TEXT, "textbox_font", text_col, component_p2_text,
                                           self.components_p2_x + 6, self.components_y[i], 0]]

    def draw_ccs(self, step, sel_table, is_active, channel_ccs):
        def get_colors(sel_table, is_active, i, x, is_control=True):
            if sel_table == 2 and self.cursor_y == i and self.cursor_x == x:
                text_col = themeing.BLACK
                bg_col = themeing.CURSOR_COLOR if is_active else themeing.CURSOR_COLOR_ALT
            else:
                bg_col, text_col = self.bg, self.cc_control_color if is_control else self.cc_value_color
            return text_col, bg_col

        for i in range(8):
            cc_control_text_left = f"{channel_ccs[i]:0>3}" if channel_ccs is not None else "---"
            cc_value_text_left = f"{step.ccs[i]:0>3}" if step.ccs[i] is not None else "---"
            cc_control_text_right = f"{channel_ccs[i + 8]:0>3}" if channel_ccs is not None else "---"
            cc_value_text_right = f"{step.ccs[i + 8]:0>3}" if step.ccs[i + 8] is not None else "---"

            text_col, bg_col = get_colors(sel_table, is_active, i + 8, 0)
            self.to_render[(i + 8, 0)] = [[RECT, bg_col, self.cc_control_x1 - 3, self.cc_y[i],
                                           self.cc_control_w, self.cell_h, 0],
                                          [TEXT, "textbox_font", text_col, cc_control_text_left,
                                           self.cc_control_x1 + 11, self.cc_y[i], 0]]

            text_col, bg_col = get_colors(sel_table, is_active, i + 8, 1, is_control=False)
            self.to_render[(i + 8, 1)] = [[RECT, bg_col, self.cc_val_x1 - 3, self.cc_y[i],
                                           self.cc_val_w, self.cell_h, 0],
                                          [TEXT, "textbox_font", text_col, cc_value_text_left,
                                           self.cc_val_x1 + 6, self.cc_y[i], 0]]

            text_col, bg_col = get_colors(sel_table, is_active, i + 8, 2)
            self.to_render[(i + 8, 2)] = [[RECT, bg_col, self.cc_control_x2 - 3, self.cc_y[i],
                                           self.cc_control_w, self.cell_h, 0],
                                          [TEXT, "textbox_font", text_col, cc_control_text_right,
                                           self.cc_control_x2 + 11, self.cc_y[i], 0]]

            text_col, bg_col = get_colors(sel_table, is_active, i + 8, 3, is_control=False)
            self.to_render[(i + 8, 3)] = [[RECT, bg_col, self.cc_val_x2 - 3, self.cc_y[i],
                                           self.cc_val_w, self.cell_h, 0],
                                          [TEXT, "textbox_font", text_col, cc_value_text_right,
                                           self.cc_val_x2 + 6, self.cc_y[i], 0]]

    def update_view(self, tracker, is_active):
        step = tracker.get_selected_step()
        if step is None:
            # set cells to empty or n/a here
            return

        step_index = tracker.pages[PATTERN].cursor_y
        self.title = f"{self.name} {step_index}"
        if is_active:
            title_color = themeing.CURSOR_COLOR
            self.to_render[0] = [[RECT, themeing.CURSOR_COLOR, self.x,
                                  self.y_actual, self.w, self.h_actual, 2]]
        else:
            title_color = themeing.WHITE
            self.to_render[0] = [[RECT, themeing.BG_TASKPANE_HL, self.x,
                                  self.y_actual, self.w, self.h_actual, 2]]

        self.to_render[1] = [[RECT, themeing.BG_TASKPANE, self.x + 2,
                              self.y_actual + 2, self.w - 4, self.h_closed - 4, 0],
                             [TEXT, "tracker_font", title_color, self.title,
                              self.x + 6, self.y_actual + 8, 0]]

        sel_table = 2 if self.cursor_y > 7 else 1 if self.cursor_y > 3 else 0
        self.draw_notes(step, sel_table, is_active)
        self.draw_components(step, sel_table, is_active)

        curr_track = tracker.get_selected_track()
        channel_ccs = tracker.channel_ccs[curr_track.channel] if curr_track is not None else None
        self.draw_ccs(step, sel_table, is_active, channel_ccs)

        self.check_redraw(tracker.renderer.render_queue)


class TrackPage(MenuPage):
    def __init__(self, x, y, tracker):
        super().__init__(x, y, "TRACK", tracker)
        self.image = self.image = self.tracker.renderer.load_image(r"resources\editor_panes\track_page.png")
        self.cursor_x = 0
        self.cursor_y = 0


class PatternPage(MenuPage):
    def __init__(self, x, y, tracker):
        super().__init__(x, y, "PATTERN", tracker)
        self.image = self.image = self.tracker.renderer.load_image(r"resources\editor_panes\pattern_page.png")
        self.cursor_x = 0
        self.cursor_y = 0


class PhrasePage(MenuPage):
    def __init__(self, x, y, tracker):
        super().__init__(x, y, "PHRASE", tracker)
        self.image = self.image = self.tracker.renderer.load_image(r"resources\editor_panes\phrase_page.png")
        self.cursor_x = 0
        self.cursor_y = 0


class EditorWindow(ViewComponent):
    def __init__(self, tracker):
        super().__init__(tracker)
        self.previous_page = PATTERN
        self.x_pos = display.editor_window_x  # 966

        self.y_pos = 2
        self.title_h = 28
        self.w = 250
        self.h = 600

        self.tracker.event_bus.subscribe(events.EDITOR_WINDOW_STATE_CHANGED, self.flag_state_change)

        self.curr_page = 0
        page_h_closed = 35
        self.pages = [StepPage(self.x_pos, 0, self.tracker),
                      TrackPage(self.x_pos, page_h_closed, self.tracker),
                      PatternPage(self.x_pos, page_h_closed * 2, self.tracker),
                      PhrasePage(self.x_pos, page_h_closed * 3, self.tracker)]
        self.pages[self.curr_page].active = 1
        self.open_page(self.curr_page)
        self.key_hints = KeyHints()

    def open_page(self, page_index, increment=None):
        if increment is not None:
            page_index = (self.curr_page + increment) % 4

        for i, page in enumerate(self.pages):
            if i == page_index:
                page.active = 1
                page.h_actual = page.h_open
                page.y_actual = page.y

            else:
                page.active = 0
                page.h_actual = page.h_closed
                if i > page_index:
                    page.y_actual = (page.y + 495) - 35
                else:
                    page.y_actual = page.y

        self.curr_page = page_index
        self.update_page_view()
        self.pages[self.curr_page].update_view(self.tracker, self.active)

    def update_page_view(self):
        render_queue = self.tracker.renderer.render_queue
        for page in self.pages:
            if page.active:
                render_queue.appendleft([IMAGE, page.image, page.x, page.y_actual, 0])
                if self.active:
                    outline, txt_col = themeing.CURSOR_COLOR, themeing.CURSOR_COLOR
                else:
                    outline, txt_col = themeing.BG_TASKPANE_HL, themeing.WHITE
            else:
                bg, outline, txt_col = themeing.BG_COLOR, themeing.BG_TASKPANE, themeing.WHITE
                render_queue.appendleft([RECT, bg, page.x, page.y_actual, page.w, page.h_actual, 0])

            render_queue.appendleft([RECT, outline, page.x, page.y_actual, page.w, page.h_actual, 2])
            render_queue.appendleft([TEXT, "tracker_font", txt_col, page.name, page.x + 6, page.y_actual + 8, 0])

    def handle_select(self):
        self.pages[self.curr_page].handle_select()
        self.flag_state_change()

    def handle_delete(self, remove_steps):
        self.pages[self.curr_page].handle_delete(remove_steps)
        self.flag_state_change()

    def handle_insert(self):
        self.pages[self.curr_page].handle_insert()
        self.flag_state_change()

    def handle_param_adjust(self, increment, axis=False):
        self.pages[self.curr_page].handle_param_adjust(increment, axis)
        self.flag_state_change()

    def move_in_place(self, x, y):
        self.pages[self.curr_page].move_in_place(x, y)
        self.flag_state_change()

    def handle_copy(self):
        self.pages[self.curr_page].handle_copy()
        self.flag_state_change()

    def handle_paste(self):
        self.pages[self.curr_page].handle_paste()
        self.flag_state_change()

    def move_cursor(self, x, y, expand_selection=False):
        self.pages[self.curr_page].move_cursor(x, y)
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

        self.pages[self.curr_page].update_view(self.tracker, self.active)
        self.render_key_hints()
        self.state_changed = False
