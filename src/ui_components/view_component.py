from config import events, constants, display, render_map, themeing


class ViewComponent:
    def __init__(self, tracker):
        self.tracker = tracker
        self.page_active_coords = None
        self.cursor_x = self.cursor_y = self.cursor_w = self.cursor_h = 0
        self.active = False
        self.state_changed = True
        self.clipboard = []
        self.selected_rows = self.get_selected_rows()
        self.selected_tracks = self.get_selected_tracks()
        self.tracker.event_bus.subscribe(events.ALL_STATES_CHANGED, self.flag_state_change)

    def toggle_active(self):
        self.active = not self.active
        if self.page_active_coords is not None:
            color = themeing.LINE_16_HL_BG if not self.active else themeing.CURSOR_COLOR
            self.tracker.renderer.render_queue.appendleft([render_map.RECT, color, *self.page_active_coords])
        self.flag_state_change()

    def flag_state_change(self):
        self.selected_rows = self.get_selected_rows()
        self.state_changed = True

    def handle_select(self):
        pass

    def handle_delete(self, remove_steps):
        pass

    def handle_insert(self):
        pass

    def handle_param_adjust(self, increment, axis=False):
        pass

    def move_in_place(self, x, y):
        pass

    def handle_copy(self):
        pass

    def handle_paste(self):
        pass

    def move_cursor(self, x, y, expand_selection=False):
        pass


    def handle_duplicate(self):
        pass

    def update_view(self):
        pass

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



