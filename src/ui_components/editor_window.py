from src.ui_components.view_component import ViewComponent
from src.ui_components.gui_elements import KeyHints
from config import display, themeing, events
from config.render_map import *
from config.pages import *

from src.ui_components.editor_panes.master_step_edit_page import MasterStepPage
from src.ui_components.editor_panes.step_edit_page import StepPage
from src.ui_components.editor_panes.track_edit_page import TrackPage
from src.ui_components.editor_panes.pattern_edit_page import PatternPage
from src.ui_components.editor_panes.phrase_edit_page import PhrasePage


class EditorWindow(ViewComponent):
    def __init__(self, tracker):
        super().__init__(tracker)
        self.previous_page = PATTERN
        self.x_pos = display.editor_window_x  # 966

        self.y_pos = 2
        self.title_h = 28
        self.w = 250
        self.h = 600

        self.curr_page = 0
        page_h_closed = 35

        self.master_step_page = MasterStepPage(self.x_pos, 0, self.tracker)
        self.midi_step_page = StepPage(self.x_pos, 0, self.tracker)

        self.pages = [self.midi_step_page,
                      TrackPage(self.x_pos, page_h_closed, self.tracker),
                      PatternPage(self.x_pos, page_h_closed * 2, self.tracker),
                      PhrasePage(self.x_pos, page_h_closed * 3, self.tracker)]
        self.pages[self.curr_page].active = 1
        self.open_page(self.curr_page)
        self.key_hints = KeyHints()

        self.tracker.event_bus.subscribe(events.EDITOR_WINDOW_STATE_CHANGED, self.flag_state_change)
        self.tracker.event_bus.subscribe(events.ON_PATTERN_TRACK, self.set_step_page_to_pattern)
        self.tracker.event_bus.subscribe(events.ON_MASTER_TRACK, self.set_step_page_to_master)

    def update_step_page(self):
        if self.curr_page == STEP_EDIT:
            self.open_page(STEP_EDIT)
            self.flag_state_change()

    def set_step_page_to_pattern(self):
        self.pages[STEP_EDIT].active = 0
        self.pages[STEP_EDIT] = self.midi_step_page
        self.pages[STEP_EDIT].previous_render = {}
        self.update_step_page()

    def set_step_page_to_master(self):
        self.pages[STEP_EDIT].active = 0
        self.pages[STEP_EDIT] = self.master_step_page
        self.pages[STEP_EDIT].previous_render = {}
        self.update_step_page()

    def open_page(self, page_index, increment=None):
        if increment is not None:
            page_index = (self.curr_page + increment) % 4

        for i, page in enumerate(self.pages):
            page.to_render = {k: [] for k in page.to_render.keys()}
            if i == page_index:
                page.active = 1
                page.h_actual = page.h_open
                page.y_actual = page.y
                page.draw_bg()

            else:
                page.active = 0
                page.h_actual = page.h_closed
                if i > page_index:
                    page.y_actual = (page.y + 495) - 35
                else:
                    page.y_actual = page.y
            page.update_view(self.tracker, self.active)

        self.curr_page = page_index

    def seek(self, xy, expand_selection=False):
        pass  # make this so that it moves to the next table in whatever page & direction
        """
        y = xy[1]
        if y != 0:
            self.open_page(None, y)
        """

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
        print(self.curr_page)
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

    def move_alt_cursor(self, x, y):
        self.tracker.pages[self.previous_page].move_cursor(x, y)
        if self.previous_page in {MASTER, PATTERN}:
            self.tracker.pages[self.previous_page].flag_state_change()

    def render_key_hints(self):
        render_queue = self.tracker.renderer.render_queue
        items = [[" U ", " D ", " L ", " R "], ["PLY", "ADD", "SEL", "DEL"]]
        elems_to_render = self.key_hints.check_for_state_change(items)
        if elems_to_render:
            render_queue.extendleft(elems_to_render)

    def update_view(self):
        for page in self.pages:
            page.update_view(self.tracker, self.active)
        self.render_key_hints()
        self.state_changed = False
