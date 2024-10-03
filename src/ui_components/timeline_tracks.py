from config import constants, display, themeing, events
from config.render_map import *
from config.pages import *

from src.ui_components.view_component import ViewComponent
from src.ui_components.gui_elements import TimelineCell, TimelineArrow


class TimelineTrack(ViewComponent):
    def __init__(self, tracker):
        super().__init__(tracker)
        self.num_rows = display.num_timeline_rows
        self.type = None
        self.timeline_arrows = None
        self.cells = None

        self.tracker.event_bus.subscribe(events.TIMELINE_STATE_CHANGED, self.flag_state_change)

    def move_cursor(self, x, y, expand_selection=False):
        prev_y = self.cursor_y
        if y != 0:
            max_len = constants.timeline_length - 1
            self.cursor_y = max(0, min(max_len, self.cursor_y + y))

        if expand_selection:
            self.cursor_h += self.cursor_y - prev_y
        else:
            self.cursor_h = 0

        self.tracker.event_bus.publish(events.EDITOR_WINDOW_STATE_CHANGED)
        self.flag_state_change()

    def draw_arrows(self, render_queue):
        assert self.timeline_arrows is not None
        timeline_length = self.tracker.timeline_length
        mid = display.num_timeline_rows // 2 - 1
        for i, arrow in enumerate(self.timeline_arrows):
            cond = (mid < self.cursor_y < timeline_length - mid)
            if arrow.dirtied([cond]):
                col = themeing.CURSOR_COLOR if cond else themeing.TIMELINE_BG
                render_queue.appendleft([POLYGON, col, arrow.points, 1])

    def get_timeline_step_state(self, y):
        assert self.type is not None
        mid = display.num_timeline_rows // 2 - 1
        cursor_pos = self.cursor_y
        offset = -min(mid, self.cursor_y) if self.cursor_y <= mid else -mid
        if self.cursor_y > constants.timeline_length - mid:
            offset -= mid - (constants.timeline_length - cursor_pos)

        step_index = cursor_pos + y + offset
        if self.type == "song":
            step_num = self.tracker.song_pool[step_index]
        else:
            step_num = self.tracker.cursor_phrase[step_index]

        if step_index < 0 or step_index >= constants.timeline_length:
            text, text_color = None, None
        else:
            if self.type == "song":
                condition = (step_index == self.tracker.song_playhead and self.tracker.is_playing)
            elif self.type == "phrase":
                condition = (step_index == self.tracker.phrase_playhead and self.tracker.is_playing and
                             self.tracker.pages[SONG].cursor_y == self.tracker.song_playhead)
            else:
                condition = False

            text_color = themeing.PLAYHEAD_COLOR if condition else themeing.WHITE
            text = f"{step_num:0>3}" if step_num is not None else ' - - '

        bg = themeing.BG_SHADOW if not y % 2 else themeing.TIMELINE_BG_HL
        if self.active and step_index == cursor_pos:
            cursor = themeing.CURSOR_COLOR
        elif step_index == cursor_pos:
            cursor = themeing.CURSOR_COLOR_ALT
        else:
            cursor = themeing.BLACK

        return [text, text_color, cursor, bg]

    def draw_track(self, render_queue):
        assert self.cells is not None

        for y in range(self.num_rows):
            cell = self.cells[y]
            state = self.get_timeline_step_state(y)

            if cell.dirtied(state):
                text, text_color, cursor, bg = state
                x, y = cell.x_screen, cell.y_screen
                w, h = display.timeline_cell_w, display.timeline_cell_h
                render_queue.appendleft([RECT, cursor, x - 2, y + 1, w, h, 1])
                render_queue.appendleft([RECT, bg, x, y + 3, w - 4, h - 4, 0])
                if text is not None:
                    render_queue.appendleft([TEXT, "tracker_timeline_font", text_color, text, x + 1, y + 2, 0])
    
    def handle_param_adjust(self, increment, axis=False):
        self.tracker.event_bus.publish(events.ALL_STATES_CHANGED)
        self.state_changed = True

    def update_view(self):
        if not self.state_changed:
            return

        render_queue = self.tracker.renderer.render_queue
        self.draw_arrows(render_queue)
        self.draw_track(render_queue)

        self.state_changed = False


class SongTrack(TimelineTrack):
    def __init__(self, tracker):
        super().__init__(tracker)
        self.page_active_coords = display.song_page_border
        self.type = "song"
        self.cells = [TimelineCell(10, y) for y in range(display.num_timeline_rows)]
        self.timeline_arrows = [TimelineArrow(display.song_arrow_upper),
                                TimelineArrow(display.song_arrow_lower)]
        self.update_view()

    def handle_select(self):
        pass

    def handle_delete(self, remove_steps):
        pass

    def handle_insert(self):
        pass

    def handle_param_adjust(self, increment, axis=False):
        super().handle_param_adjust(increment)
        self.tracker.update_song_step(self.cursor_y, increment)

    def move_cursor(self, x, y, expand_selection=False):
        self.tracker.event_bus.publish(events.ALL_STATES_CHANGED)
        super().move_cursor(x, y, expand_selection)
        self.tracker.set_current_phrase(self.tracker.song_pool[self.cursor_y])

    def move_in_place(self, x, y):
        pass

    def handle_copy(self):
        pass

    def handle_paste(self):
        pass

    def handle_duplicate(self):
        pass


class PhraseTrack(TimelineTrack):
    def __init__(self, tracker):
        super().__init__(tracker)
        self.page_active_coords = display.phrase_page_border
        self.type = "phrase"
        self.cells = [TimelineCell(47, y) for y in range(display.num_timeline_rows)]
        self.timeline_arrows = [TimelineArrow(display.phrase_arrow_upper),
                                TimelineArrow(display.phrase_arrow_lower)]

        self.update_view()
        
    def handle_select(self):
        pass

    def handle_delete(self, remove_steps):
        pass

    def handle_insert(self):
        pass

    def handle_param_adjust(self, increment):
        super().handle_param_adjust(increment)
        self.tracker.update_phrase_step(self.cursor_y, increment)

    def move_cursor(self, x, y, expand_selection=False):
        self.tracker.event_bus.publish(events.ALL_STATES_CHANGED)
        super().move_cursor(x, y, expand_selection)
        self.tracker.set_cursor_pattern(self.tracker.cursor_phrase[self.cursor_y])

    def move_in_place(self, x, y):
        pass

    def handle_copy(self):
        pass

    def handle_paste(self):
        pass

    def handle_duplicate(self):
        pass
