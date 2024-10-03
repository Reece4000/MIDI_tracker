from config import themeing
from config.render_map import *


class MenuPage:
    def __init__(self, x, y, name, tracker):
        self.title_bg_selected = themeing.BG_COLOR
        self.title_bg_unselected = themeing.BG_SHADOW
        self.tracker = tracker
        self.image = None
        self.bg = themeing.BG_TASKPANE
        self.cell_h = 16
        self.x = x
        self.y = y + 4
        self.y_actual = y
        self.w = 250
        self.h_closed = 35
        self.h_open = 495
        self.h_actual = self.h_closed
        self.y_offset = 0
        self.h_offset = 0

        self.cursor_x = 0
        self.cursor_y = 0
        self.active = 0  # closed
        self.name = name
        self.title = name
        self.clipboard = []

        self.to_render = {}
        self.previous_render = {}

    def draw_bg(self):
        if self.image is not None:
            bg = [IMAGE, self.image, self.x, self.y_actual, 0]
            self.tracker.renderer.render_queue.appendleft(bg)

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

    def update_view(self, tracker, editor_active):
        title_bg = self.title_bg_selected if self.active else self.title_bg_unselected
        if self.active and editor_active:
            title_color = outline_color = themeing.CURSOR_COLOR
        else:
            title_color, outline_color = themeing.WHITE, themeing.DARK

        self.to_render[100] = [[RECT, title_bg, self.x + 1, self.y_actual, self.w - 2, self.h_closed, 0],
                               [TEXT, "textbox_font", title_color, self.title, self.x + 6, self.y_actual + 8, 0],
                               [RECT, outline_color, self.x, self.y_actual, self.w, self.h_actual, 1]]

    def move_cursor(self, x, y):
        pass

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
