from config import constants, display, themeing, events
from config.render_map import *
from config.pages import *

from src.ui_components.view_component import ViewComponent
from src.ui_components.gui_elements import TimelineCell, TimelineArrow


class TimelinePage(ViewComponent):
    def __init__(self, tracker):
        super().__init__(tracker)

        self.page_active_coords = display.timeline_page_border
        self.previous_page = PATTERN
        self.paste_presses = 0
        self.pages = [PhraseTrack(parent_page=self, y=display.timeline_area_y + 16),
                      SongTrack(parent_page=self, y=display.timeline_area_y + 64)]

        for event in [events.TIMELINE_STATE_CHANGED, events.ALL_STATES_CHANGED]:
            self.tracker.event_bus.subscribe(event, self.flag_state_change)

    def toggle_active(self):
        self.active = not self.active
        color = themeing.LINE_16_HL_BG if not self.active else themeing.CURSOR_COLOR
        self.tracker.renderer.render_queue.appendleft([RECT, color, *self.page_active_coords])
        self.pages[self.cursor_y].active = self.active

    def flag_state_change(self, *args):
        self.state_changed = True

    def move_cursor(self, x, y, expand_selection=False):
        self.paste_presses = 0
        if y != 0:
            self.switch_timeline_page(y)
        if x != 0:
            self.pages[self.cursor_y].move_cursor(x, 0, expand_selection)
            self.tracker.event_bus.publish(events.ALL_STATES_CHANGED)

    def handle_select(self):
        self.pages[self.cursor_y].handle_select()

    def handle_delete(self, remove_steps):
        self.pages[self.cursor_y].handle_delete(remove_steps)

    def handle_insert(self):
        self.pages[self.cursor_y].handle_insert()

    def handle_param_adjust(self, increment, axis=False):
        self.pages[self.cursor_y].handle_param_adjust(increment, axis)

    def move_in_place(self, x, y):
        self.pages[self.cursor_y].move_in_place(x, y)

    def handle_copy(self):
        self.paste_presses = 0
        self.pages[self.cursor_y].handle_copy()

    def handle_paste(self):
        self.pages[self.cursor_y].handle_paste()
        self.paste_presses += 1

    def switch_timeline_page(self, y):
        self.paste_presses = 0
        self.pages[self.cursor_y].active = False
        self.cursor_y = max(0, min(1, self.cursor_y + y))
        self.pages[self.cursor_y].active = True
        self.flag_state_change()
        self.tracker.event_bus.publish(events.TIMELINE_STATE_CHANGED)

    def initialise_view(self):
        render_queue = self.tracker.renderer.render_queue
        for i, page in enumerate(self.pages):
            outline_color = themeing.BLACK
            color = themeing.SONG_LABEL_COLOR if i == 1 else themeing.PHRASE_LABEL_COLOR
            x = self.page_active_coords[0] + 6
            render_queue.appendleft([RECT, color, x, page.y_pos - 4, 852, 28, 0])
            render_queue.appendleft([RECT, outline_color, x, page.y_pos - 4, 852, 28, 1])
            text_x = x + 32 - len(page.type) * 4
            render_queue.appendleft([TEXT, "tracker_timeline_font", themeing.WHITE,
                                     page.type.upper(), text_x, page.y_pos + 1, 0])

    def get_timeline_step_state(self, song, phrase, page, x):
        mid = page.num_cells - 1
        cursor_pos = page.cursor_x
        offset = -min(mid, page.cursor_x) if page.cursor_x <= mid else -mid
        if page.cursor_x > constants.timeline_length - mid:
            offset -= mid - (constants.timeline_length - cursor_pos)

        step_index = cursor_pos + x + offset
        if page.type == "song":
            step_num = song[step_index]
        else:
            if phrase is not None:
                step_num = phrase[step_index]
            else:
                step_num = None

        if step_index < 0 or step_index >= constants.timeline_length:
            text, text_color = None, None
        else:
            if page.type == "song":
                condition = (step_index == self.tracker.song_playhead and self.tracker.is_playing)
            elif page.type == "phrase":
                condition = (step_index == self.tracker.phrase_playhead and self.tracker.is_playing and
                             self.pages[TIMELINE_SONG].cursor_x == self.tracker.song_playhead)
            else:
                condition = False

            text_color = themeing.PLAYHEAD_COLOR if condition else themeing.BG_PTN
            text = f"{step_num:0>3}" if step_num is not None else ' - - '

        bg, cursor = page.cells[x].get_colors(step_index, cursor_pos, x, page.active)

        return [text, text_color, cursor, bg]

    def update_view(self):
        render_queue = self.tracker.renderer.render_queue
        song = self.tracker.song
        phrase = self.tracker.get_selected_phrase()
        for page in self.pages:
            for x in range(page.num_cells):
                cell = page.cells[x]
                state = self.get_timeline_step_state(song, phrase, page, x)

                if cell.dirtied(state):
                    cell.draw(render_queue)


class TimelineTrack:
    def __init__(self, parent_page, y):
        self.parent_page = parent_page
        self.tracker = parent_page.tracker
        self.y_pos = y
        self.num_cells = display.num_timeline_cells
        self.cursor_x = 0
        self.cursor_w = 0
        self.type = None
        self.clipboard = []
        self.active = False


class SongTrack(TimelineTrack):
    def __init__(self, parent_page, y):
        super().__init__(parent_page, y)
        self.type = "song"
        self.cells = [TimelineCell(61, y, self.type) for y in range(self.num_cells)]

    def handle_select(self):
        pass

    def handle_delete(self, remove_steps):
        pass

    def handle_insert(self):
        pass

    def handle_param_adjust(self, increment, axis=False):
        self.tracker.adjust_song_step(self.cursor_x, increment)
        self.tracker.event_bus.publish(events.ALL_STATES_CHANGED)

    def move_cursor(self, x, y, expand_selection=False):
        prev_x = self.cursor_x
        self.cursor_x = max(0, min(constants.timeline_length - 1, self.cursor_x + x))
        self.cursor_w += self.cursor_x - prev_x if expand_selection else 0

    def move_in_place(self, x, y):
        pass

    def handle_copy(self):
        pass

    def handle_paste(self):
        pass

    def handle_duplicate(self):
        pass


class PhraseTrack(TimelineTrack):
    def __init__(self, parent_page, y):
        super().__init__(parent_page, y)
        self.last_phrase_num = 0
        self.type = "phrase"
        self.cells = [TimelineCell(13, y, self.type) for y in range(self.num_cells)]

    def handle_select(self):
        selected_phrase = self.tracker.get_selected_phrase()
        if selected_phrase[self.cursor_x] is None:
            selected_phrase[self.cursor_x] = self.last_phrase_num
        else:
            self.last_phrase_num = selected_phrase[self.cursor_x]

    def handle_delete(self, remove_steps):
        pass

    def handle_insert(self):
        pass

    def handle_param_adjust(self, increment, axis=False):
        num = self.tracker.adjust_phrase_step(self.cursor_x, increment)
        if num is not None:
            self.last_phrase_num = num

    def move_cursor(self, x, y, expand_selection=False):
        prev_x = self.cursor_x
        self.cursor_x = max(0, min(constants.timeline_length - 1, self.cursor_x + x))
        self.cursor_w += self.cursor_x - prev_x if expand_selection else 0
        self.tracker.event_bus.publish(events.ALL_STATES_CHANGED)

    def move_in_place(self, x, y):
        pass

    def handle_copy(self):
        self.clipboard = [self.tracker.get_selected_pattern(num=True)]

    def handle_paste(self):
        if self.clipboard[0] is None:
            return
        selected_phrase = self.tracker.get_selected_phrase()
        if self.parent_page.paste_presses == 0:
            selected_phrase[self.cursor_x] = self.clipboard[0]
            self.last_phrase_num = self.clipboard[0]
        elif self.parent_page.paste_presses == 1:
            clipboard_pattern = self.tracker.pattern_pool[self.clipboard[0]]
            new_pattern_num = self.tracker.clone_pattern(clipboard_pattern)
            selected_phrase[self.cursor_x] = new_pattern_num
            self.last_phrase_num = new_pattern_num

        self.tracker.event_bus.publish(events.ALL_STATES_CHANGED)

