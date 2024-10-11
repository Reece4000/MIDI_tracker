from config import events
from config.render_map import *
from config.pages import *
from config import themeing
from config.constants import master_component_mapping
from src.utils import get_increment
from src.steps import EMPTY_MIDI_STEP
from src.ui_components.editor_panes.menu_page import MenuPage


class MasterStepPage(MenuPage):
    def __init__(self, x, y, tracker):
        super().__init__(x, y, "MASTER STEP", tracker)
        self.cursor_x_trackmask = 0
        self.clipboard = {"component": None, "value": None}
        self.image = self.tracker.renderer.load_image(r"resources\editor_panes\master_step_page.png")
        self.components_page_image = self.tracker.renderer.load_image(r"resources\editor_panes\master_components.png")
        self.title_bg_selected = themeing.STEP_TITLE_SELECTED
        self.title_bg_unselected = themeing.STEP_TITLE_UNSELECTED
        self.last_component = 0
        self.box = (self.x + 12, 119, 95, self.cell_h)
        self.tr_box = (self.x + 54, 154, 18, 18)

    def move_cursor(self, x, y):
        if x != 0:
            if self.cursor_y in {0, 2, 4, 6}:
                self.cursor_x = max(min(2, self.cursor_x + x), 0)
            else:
                self.cursor_x_trackmask = max(min(7, self.cursor_x_trackmask + x), 0)

        if y != 0:
            self.cursor_y = (self.cursor_y + y) % 8

    def handle_select(self):
        component_index = 0 if self.cursor_y == 0 else self.cursor_y // 2
        master_step = self.tracker.get_selected_master_step()
        if self.cursor_y in {0, 2, 4, 6}:
            if self.cursor_x == 0:
                master_step.add_component(self.last_component, index=component_index)
        else:
            if master_step.empty or master_step.components[component_index] is None:
                return
            track_mask = master_step.component_track_masks[component_index]
            track_mask[self.cursor_x_trackmask] = not track_mask[self.cursor_x_trackmask]



    def handle_delete(self, remove_steps):
        pass

    def handle_insert(self):
        pass

    def handle_copy(self):
        pass

    def handle_param_adjust(self, increment, axis=False):
        if self.cursor_y in {0, 2, 4, 6} and self.cursor_x == 0:
            master_step = self.tracker.get_selected_master_step()
            index = 0 if self.cursor_y == 0 else self.cursor_y // 2
            curr_component = master_step.components[index]
            new_component = curr_component + 1 if increment > 0 else curr_component - 1
            new_component = max(0, min(15, new_component))
            master_step.add_component(new_component, index=index)
            self.last_component = new_component

    def adjust_component(self, step, component_index, increment, preview=True):
        pass

    def update_view(self, tracker, editor_active):
        selected_pattern = tracker.get_selected_pattern()
        step = tracker.get_selected_master_step()

        if step is None:
            return

        selected = (themeing.CURSOR_COLOR, themeing.BLACK)
        unselected = (self.bg, themeing.WHITE)

        m = master_component_mapping
        if self.active and selected_pattern is not None:
            for i in range(4):
                if step.empty:
                    component = None
                    component_x_val = None
                    component_y_val = None
                    track_mask = None
                else:
                    component = step.components[i]
                    component_x_val = step.component_x_vals[i]
                    component_y_val = step.component_y_vals[i]
                    track_mask = step.component_track_masks[i]
                x, y, w, h = self.box
                y += (i * 91)

                # render component boxes
                clr = selected if self.cursor_x == 0 and self.cursor_y == i * 2 else unselected
                text = "---" if component is None else m[component]["name"]
                self.to_render[i] = [[RECT, clr[0], x, y, w, h, 0],
                                     [TEXT, "textbox_font", clr[1], text, x + 4, y, 0]]

                clr = selected if self.cursor_x == 1 and self.cursor_y == i * 2 else unselected
                text = "---" if component_x_val is None else f"{component_x_val:>02}"
                self.to_render[i + 4] = [[RECT, clr[0], x + 103, y, w - 40, h, 0],
                                         [TEXT, "textbox_font", clr[1], text, x + 107, y, 0]]

                clr = selected if self.cursor_x == 2 and self.cursor_y == i * 2 else unselected
                text = "---" if component_y_val is None else f"{component_y_val:>02}"
                self.to_render[i + 8] = [[RECT, clr[0], x + 165, y, w - 40, h, 0],
                                         [TEXT, "textbox_font", clr[1], text, x + 169, y, 0]]

                # render track mask boxes
                y = self.tr_box[1] + (i * 91)
                w, h = self.tr_box[2], self.tr_box[3]
                for j in range(8):
                    x = self.tr_box[0] + (j * 23)
                    clr = selected if self.cursor_x_trackmask == j and self.cursor_y == (i * 2 + 1) else unselected
                    self.to_render[(i, j)] = [[RECT, clr[0], x, y, w, h, 0]]
                    if track_mask is not None and track_mask[j]:
                        self.to_render[(i, j)].append([RECT, clr[1], x + 6, y + 6, w - 12, h - 12, 0])

        step_index = tracker.pages[MASTER].cursor_y
        self.title = f"{self.name} {step_index}"
        super().update_view(tracker, editor_active)
        self.check_redraw(tracker.renderer.render_queue)
