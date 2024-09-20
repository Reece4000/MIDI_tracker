import pygame
from collections import deque
from src.gui_elements import *
from src.utils import timing_decorator, midi_to_note
from config import constants, display, themeing, events
from config.render_map import *
import time

class DetailWindow:
    def __init__(self):
        self.x_pos = display.track_x_positions[7] + 100
        self.y_pos = 2
        self.w = 250
        self.h = 702


class Renderer:
    def __init__(self, tracker):
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((display.display_w, display.display_h))
        self.screen_w, self.screen_h = display.display_w, display.display_h
        self.center_y = (self.screen_h + display.menu_height) // 2
        self.tracker = tracker
        self.fullscreen = False
        self.fonts = {
            "tracker_info_font": pygame.font.Font(r'resources\fonts\pixel\PixelOperatorMonoHB8.ttf', 8),
            "tracker_MIDI_out_font": pygame.font.Font(r'resources\fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
            "track_display_font": pygame.font.Font(r'resources\fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
            "options_font": pygame.font.Font(r'resources\fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
            "tracker_font": pygame.font.Font(r'resources\fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
            "tracker_font_bold": pygame.font.Font(r'resources\fonts\Code 7x5.ttf', 16),
            "tracker_font_small": pygame.font.Font(r'resources\fonts\pixel\PixelOperatorMonoHB.ttf', 8),
            "tracker_row_label_font": pygame.font.Font(r'resources\fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
            "tracker_timeline_font": pygame.font.Font(r'resources\fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
            "param_display": pygame.font.Font(r'resources\fonts\Code 7x5.ttf', 8),
            "zoom_font": pygame.font.Font(r'resources\fonts\pixel\PixelOperatorMono-Bold.ttf', 32),
        }

        # self.detail_window = DetailWindow()
        # self.cells = [[PatternCell(x, y) for y in range(display.visible_rows)] for x in range(constants.track_count)]
        # self.row_number_cells = [RowNumberCell(y) for y in range(display.visible_rows)]
        # self.song_cells = [TimelineCell(10, y) for y in range(display.num_timeline_rows)]
        # self.phrase_cells = [TimelineCell(47, y) for y in range(display.num_timeline_rows)]
        # self.track_boxes = [TrackBox(x) for x in range(constants.track_count)]
        # self.play_pause_icon = PlayPause()
        # self.timeline_arrows = [TimelineArrow(display.song_arrow_upper),  # song upper
        #                         TimelineArrow(display.phrase_arrow_upper),  # phrase upper
        #                         TimelineArrow(display.song_arrow_lower),  # song lower
        #                         TimelineArrow(display.phrase_arrow_lower)]  # phrase lower

        # self.options_button = OptionsButton()
        # self.pattern_info_text = PatternInfoText()
        # self.controller_image = pygame.image.load(r"resources\grey-gaming-or-game-console-20055.png")
        # self.key_hints = KeyHints(pygame.image.load(r"resources\controller.svg"))
        self.page_switch_cursor = PageSwitchMarkers()

        self.text_cache = {}
        self.pane_cache = {}
        self.render_queue = deque()
        self.dirty_rects = []
        self.render_cycle = 0

        self.pattern_state_changed = True
        self.song_track_state_changed = True
        self.phrase_track_state_changed = True

        # https://www.iconpacks.net
        icon = pygame.image.load(r"resources/black-gameplay-symbol-20172.svg")
        pygame.display.set_icon(icon)

        pygame.display.set_caption("GAMT")

        self.tracker.event_bus.subscribe(events.FULLSCREEN, self.toggle_fullscreen)
        # self.initial_draw()

    def quit(self):
        self.render_queue = None
        self.pane_cache = None
        self.text_cache = None
        pygame.quit()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        pygame.display.quit()
        pygame.display.init()
        if self.fullscreen:
            self.screen = pygame.display.set_mode((display.display_w, display.display_h), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((display.display_w, display.display_h))

        self.tracker.event_bus.publish(events.TRACKER_INITIALISED)
        self.tracker.event_bus.publish(events.ALL_STATES_CHANGED)
        self.initialise()


    # @timing_decorator
    def show_opt(self):
        pass
        # self.options_window.show(self.state.pattern_cursor_x, self.center_y, self.state.page)

    # @keep_time
    def render_element_from_queue(self):
        e = self.render_queue.pop()

        try:
            if e[0] == FILL:
                self.screen.fill(e[1])

            elif e[0] == LINE:
                color, start, end, width = e[1], e[2], e[3], e[4]
                l = pygame.draw.line(self.screen, color, start, end, width)
                self.dirty_rects.append(l)

            elif e[0] == PANE:
                color, x, y, w, h, alpha = e[1], e[2], e[3], e[4], e[5], e[6]
                key = (color, x, y, w, h)
                if key not in self.pane_cache:
                    s = pygame.Surface((w, h))
                    s.set_alpha(alpha)
                    s.fill(color)
                    pane = s
                else:
                    pane = self.pane_cache[key]

                self.screen.blit(pane, (x, y))

            elif e[0] == RECT:
                color, x, y, w, h, b = e[1], e[2], e[3], e[4], e[5], e[6]
                try:
                    r = pygame.draw.rect(self.screen, color, (x, y, w, h), b)
                    self.dirty_rects.append(r)
                except:
                    print("error adding rect: ", color, x, y, w, h, b)

            elif e[0] == TEXT:
                font, color, text, x, y, antialias = e[1], e[2], e[3], e[4], e[5], e[6]
                key = (font, color, text, x, y)

                if key not in self.text_cache:
                    rendered_text = self.fonts[font].render(text, antialias, color)
                    self.text_cache[key] = rendered_text
                else:
                    rendered_text = self.text_cache[key]

                self.screen.blit(rendered_text, (x, y))

            elif e[0] == CIRCLE:
                color, center, radius, width = e[1], e[2], e[3], e[4]
                c = pygame.draw.circle(self.screen, color, center, radius, width)
                self.dirty_rects.append(c)

            elif e[0] == POLYGON:
                color, points, b = e[1], e[2], e[3]
                p = pygame.draw.polygon(self.screen, color, points, b)
                self.dirty_rects.append(p)

            elif e[0] == "user input":
                pass
                # prompt, font, color = e[1], e[2], e[3]
                # user_input = UserInput(prompt)
                # user_input.get_text(self.screen, self.fonts[font], color)
                # return user_input.inputted_text

            elif e[0] == IMAGE:
                self.screen.blit(e[1], (e[2], e[3]))
        except IndexError:
            print(e)

    def initialise(self):
        # main bg
        self.render_queue.appendleft([RECT, themeing.BG_PTN, 0, 0, self.screen_w, self.screen_h, 0])
        # timeline bg
        self.render_queue.appendleft([RECT, themeing.TIMELINE_BG, -1, 0, display.timeline_width, self.screen_h, 0])

        grad = 90
        r, g, b = themeing.TIMELINE_BG
        for i in range(grad):
            block, color = i * 3, (r + grad, g + grad, b + grad)
            self.render_queue.appendleft([RECT, color, 0, block - 5, display.timeline_width - 1, block, 0])
            r, g, b = r - 1, g - 1, b - 1

        # self.render_queue.extendleft(self.play_pause_icon.initialise())
        # self.render_queue.extendleft(self.options_button.initialise())
        # self.render_queue.extendleft(self.pattern_info_text.initialise())

        # win = self.detail_window
        # x = win.x_pos
        # y = win.y_pos

        # self.render_queue.appendleft([RECT, themeing.BG_SEP, x, y, win.w, win.h, 2])
        # self.render_queue.appendleft([RECT, themeing.BG_COLOR, x + 2, y + 2, win.w - 4, win.h - 4, 0])
        # self.render_queue.appendleft([RECT, themeing.LINE_16_HL_BG, x + 2, y + 2, 242, 36, 0])

        self.render_queue.extendleft(self.page_switch_cursor.initialise())

    def get_text_width(self, font, color, text, x, y):
        key = (font, color, text, x, y)
        if key not in self.text_cache:
            rendered_text = self.fonts[font].render(text, False, color)
            self.text_cache[key] = rendered_text
        else:
            rendered_text = self.text_cache[key]
        return rendered_text.get_width()

    def user_input(self, prompt, font, color):
        pass
        # self.rq.appendleft(["user input", prompt, font, color])
        # user_input = UserInput(prompt)
        # user_input.get_text(self.screen, self.fonts[font], color)
        # return user_input.inputted_text

    @timing_decorator
    def update_screen(self):
        pygame.display.update(self.dirty_rects)
        self.dirty_rects = []
        self.render_cycle += 1

    def process_queue(self):
        while self.render_queue:
            self.render_element_from_queue()

    @timing_decorator
    def draw(self):
        # print("render start", self.state.sequencer.ticks)
        self.render_row_numbers()
        self.render_pattern()
        self.render_timeline_tracks()
        self.render_info_pane()
        self.render_info_bar()
        self.render_key_hints()
        self.render_detail_window()

        # if self.options_window.active:
        #     self.show_opt()

        # print(len(self.rq))
        while self.render_queue:
            self.render_element_from_queue()

        self.update_screen()
        # print("render stop", self.state.sequencer.ticks)

    def set_state_changed_flags(self, flags):
        for flag in flags:
            setattr(self, f"{flag}_state_changed", True)

    def draw_page_switch_cursor(self, page, x):
        elems_to_render = self.page_switch_cursor.update(page, x)
        if elems_to_render:
            self.render_queue.extendleft(elems_to_render)

    def render_key_hints(self):
        items = [[" U ", " D ", " L ", " R "], ["PLY", "ADD", "SEL", "DEL"]]
        elems_to_render = self.key_hints.check_for_state_change(items)
        if elems_to_render:
            self.render_queue.extendleft(elems_to_render)

    def render_detail_window(self):
        cursor_x = self.state.pattern_cursor["x"]
        cursor_y = self.state.pattern_cursor["y"]
        cursor_pattern = self.state.cursor_pattern

        if not self.state.view_changed["detail window"]:
            return

        win = self.detail_window
        if self.state.page == 4:
            self.render_queue.appendleft([RECT, themeing.CURSOR_COLOR, win.x_pos, win.y_pos, win.w, win.h, 2])
        else:
            self.render_queue.appendleft([RECT, themeing.LINE_16_HL_BG, win.x_pos, win.y_pos, win.w, win.h, 2])

        self.render_queue.appendleft([RECT, themeing.BG_COLOR, win.x_pos + 2, win.y_pos + 2,
                                      win.w - 4, display.detail_window_replace_bg_h, 0])
        zoom_x, zoom_y = self.state.detail_window_x, self.state.detail_window_y
        track = cursor_pattern.tracks[cursor_x]
        if cursor_y < track.length:
            step = track.steps[cursor_y]
        else:
            step = None

        self.render_queue.appendleft([RECT, themeing.LINE_16_HL_BG, win.x_pos + 2, win.y_pos + 2,
                                      win.w - 4, display.detail_window_title_h, 0])

        tr = "M" if cursor_x == 0 else f"{cursor_x}"
        cursor_col = themeing.CURSOR_COLOR if self.state.page == 4 else themeing.BG_SEP
        text = f"TRK:{tr} STP:{cursor_y}" if step is not None else f"TRK:{tr} STP:--"
        self.render_queue.appendleft([TEXT, "zoom_font", cursor_col, text, win.x_pos + 12, win.y_pos + 2, 0])

        start_y = 44
        x_pos = win.x_pos + 6
        if not track.is_master:
            if step is not None:
                self.render_queue.appendleft([TEXT, "zoom_font", (100, 255, 100), "Notes:", x_pos + 4, start_y, 0])
                for i, note in enumerate(step.notes):
                    y = start_y + 30 + (29 * i)
                    if note is not None:
                        note_text = midi_to_note(note)
                        vel_text = f'{step.velocities[i]:0>2}'
                    else:
                        note_text = "---"
                        vel_text = "--"
                    self.render_queue.appendleft([TEXT, "zoom_font", (100, 255, 100), note_text, x_pos + 4, y + 2, 0])
                    self.render_queue.appendleft([TEXT, "zoom_font", (255, 150, 150), vel_text, x_pos + 77, y + 2, 0])
                    if self.state.detail_window_y == i and zoom_x == 0:  # on note
                        self.render_queue.appendleft([RECT, cursor_col, x_pos, y + 4, 56, 30, 2])
                    elif self.state.detail_window_y == i and self.state.detail_window_x == 1:  # on vel
                        self.render_queue.appendleft([RECT, cursor_col, x_pos + 70, y + 4, 48, 30, 2])

                self.render_queue.appendleft(
                    [TEXT, "zoom_font", (150, 255, 255), "Commands:", x_pos + 4, start_y + (29 * 4) + 36, 0])
                for i, component in enumerate(step.components):
                    y = start_y + (29 * i) + 184
                    if component is not None:
                        elems = component
                    else:
                        elems = ["---", "--", "--"]

                    self.render_queue.appendleft([TEXT, "zoom_font", (150, 255, 255), elems[0], x_pos + 4, y, 0])
                    self.render_queue.appendleft([TEXT, "zoom_font", (255, 150, 255), elems[1], x_pos + 77, y, 0])
                    self.render_queue.appendleft([TEXT, "zoom_font", (255, 255, 150), elems[2], x_pos + 134, y, 0])

                    if self.state.detail_window_y == i + 4 and self.state.detail_window_x == 0:  # on component
                        self.render_queue.appendleft([RECT, cursor_col, x_pos, y + 2, 56, 30, 2])
                    elif self.state.detail_window_y == i + 4 and self.state.detail_window_x == 1:  # on p1
                        self.render_queue.appendleft([RECT, cursor_col, x_pos + 70, y + 2, 48, 30, 2])
                    elif self.state.detail_window_y == i + 4 and self.state.detail_window_x == 2:  # on p2
                        self.render_queue.appendleft([RECT, cursor_col, x_pos + 127, y + 2, 48, 30, 2])

                y = start_y + 306

                if cursor_x > 0:
                    track_ccs = self.state.channel_ccs[cursor_x - 1]
                else:
                    track_ccs = []

                for i in range(8):

                    cc = f"{track_ccs[i]:0>3}" if track_ccs[i] is not None else "---"
                    val = f"{step.ccs[i]:0>3}" if step.ccs[i] is not None else "---"

                    cc_color, val_col = (255, 255, 80), (255, 180, 255)

                    self.render_queue.appendleft(
                        [TEXT, "tracker_font", (200, 200, 255), f"CC:", x_pos + 8, y + (26 * i) + 13, 0])

                    self.render_queue.appendleft([TEXT, "zoom_font", cc_color, f"{cc}", x_pos + 52, y + (26 * i) + 4, 0])
                    self.render_queue.appendleft([TEXT, "zoom_font", val_col, f"{val}", x_pos + 120, y + (26 * i) + 4, 0])

                    if self.state.detail_window_y == i + 8:  # col 1
                        if self.state.detail_window_x == 0:
                            self.render_queue.appendleft([RECT, cursor_col, x_pos + 48, y + (26 * i) + 4, 56, 30, 2])
                        elif self.state.detail_window_x == 1:
                            self.render_queue.appendleft([RECT, cursor_col, x_pos + 117, y + (26 * i) + 4, 56, 30, 2])

                p_x, p_y = x_pos + 192, y + 90
                self.render_queue.appendleft([POLYGON, themeing.WHITE, ((p_x, p_y), (p_x + 5, p_y - 5), (p_x + 10, p_y)), 0])
                self.render_queue.appendleft(
                    [POLYGON, themeing.WHITE, ((p_x, p_y + 20), (p_x + 5, p_y + 25), (p_x + 10, p_y + 20)), 0])

        self.state.view_changed["detail window"] = False

    @staticmethod
    def get_pattern_index(y_screen, y_pattern):
        return (y_pattern - display.visible_rows // 2) + y_screen

    @timing_decorator
    def render_row_numbers(self):
        playhead_step = None
        n_steps = 0
        master_len = 0

        if self.state.cursor_pattern is not None:
            try:
                n_steps = max(track.length for track in self.state.cursor_pattern.tracks)
            except AttributeError as e:
                print(e, "Attribute error, def render_row_numbers()", self.state.cursor_pattern)
            master_track = self.state.cursor_pattern.master_track
            master_len = master_track.length
            if self.state.on_playing_pattern:
                playhead_step = master_track.step_pos

        y_cursor = self.state.master_cursor["y"] if self.state.page == 2 else self.state.pattern_cursor["y"]
        for row_number_cell in self.row_number_cells:
            step_index = self.get_pattern_index(y_cursor, row_number_cell.y)
            elems_to_render = row_number_cell.check_for_state_change(n_steps, step_index, self.state.selected_rows,
                                                                     master_len, playhead_step)
            if elems_to_render:
                self.render_queue.extendleft(elems_to_render)

    # @timing_decorator
    def render_info_bar(self):
        play_pause = self.play_pause_icon.check_for_state_change(self.state.pulse, self.state.is_playing)
        opt = self.options_button.check_for_state_change(self.state.mouse_x, self.state.mouse_y)
        pattern_text = self.pattern_info_text.check_for_state_change(self.state.cursor_pattern)

        for e in [play_pause, pattern_text, opt]:
            if e:
                self.render_queue.extendleft(e)

    @timing_decorator
    def render_info_pane(self):
        for index, track_box in enumerate(self.track_boxes):
            track_box.check_for_state_change(index, self.state.page, self.state.cursor_pattern, self.state.selected_tracks,
                                             self.state.pulse, self.state.last_note_pulses, self, self.render_queue)

    @timing_decorator
    def render_pattern(self):
        cursor_y = self.state.master_cursor["y"] if self.state.page == 2 else self.state.pattern_cursor["y"]
        cursor_pattern = self.state.cursor_pattern
        on_playing_pattern = self.state.on_playing_pattern

        for x, t in enumerate(self.cells):
            track = None if cursor_pattern is None else cursor_pattern.tracks[x]
            playhead_step = track.step_pos if on_playing_pattern else None
            for y, cell in enumerate(t):
                step_index = self.get_pattern_index(cursor_y, y)
                if self.state.view_changed["pattern tracks"][x]:
                    step_state_changed = True
                else:
                    if track is None:
                        step_state_changed = True
                    else:
                        if 0 <= step_index < track.length:
                            step_state_changed = track.steps[step_index].state_changed
                            track.steps[step_index].state_changed = False
                        else:
                            step_state_changed = True
                if step_state_changed:
                    cell.check_for_state_change(cursor_pattern, self.state.selected_rows, self.state.selected_tracks,
                                                self.state.page, self.state.pattern_cursor["x"], step_index, track,
                                                x, playhead_step, self.render_queue)

        self.pattern_state_changed = False

    def draw_timeline_arrows(self, song_cursor, phrase_cursor):
        num_dirties = 0
        timeline_length = self.state.timeline_length
        mid = display.num_timeline_rows // 2 - 1
        for i, arrow in enumerate(self.timeline_arrows):
            cursor = song_cursor if i in [0, 2] else phrase_cursor
            cond = (mid < cursor < timeline_length - mid)

            if arrow.dirtied([cond]):
                num_dirties += 1
                col = themeing.CURSOR_COLOR if cond else themeing.TIMELINE_BG
                print("adding", col, song_cursor, phrase_cursor)
                self.render_queue.appendleft([POLYGON, col, arrow.points, 1])

        return num_dirties

    # @timing_decorator
    def render_timeline_tracks(self):
        if not self.song_track_state_changed and not self.phrase_track_state_changed:
            return

        song_cursor = self.state.song_cursor["y"]
        phrase_cursor = self.state.phrase_cursor["y"]

        num_dirties = self.draw_timeline_arrows(song_cursor, phrase_cursor)
        for y in range(display.num_timeline_rows):
            cell_states = []
            if self.song_track_state_changed:
                song_cell = self.song_cells[y]
                song_step_state = self.get_timeline_step_state(y, "song")
                cell_states.append((song_cell, song_step_state))
            if self.phrase_track_state_changed:
                phrase_cell = self.phrase_cells[y]
                phrase_step_state = self.get_timeline_step_state(y, "phrase")
                cell_states.append((phrase_cell, phrase_step_state))

            for item in cell_states:
                cell, cell_state = item[0], item[1]
                if cell.dirtied(cell_state):
                    num_dirties += 1
                    text, text_color, cursor, bg = cell_state
                    x, y = cell.x_screen, cell.y_screen + display.timeline_offset
                    self.render_queue.appendleft(
                        [RECT, cursor, x - 2, y + 1, display.timeline_cell_w, display.timeline_cell_h, 1])
                    self.render_queue.appendleft(
                        [RECT, bg, x, y + 3, display.timeline_cell_w - 4, display.timeline_cell_h - 4, 0])
                    if text is not None:
                        self.render_queue.appendleft([TEXT, "tracker_timeline_font", text_color, text, x + 1, y + 2, 0])

        self.song_track_state_changed = self.phrase_track_state_changed = False

    def get_timeline_step_state(self, y, track_type):

        song_cursor = self.state.song_cursor["y"]
        phrase_cursor = self.state.phrase_cursor["y"]
        song_playhead = self.state.song_playhead
        phrase_playhead = self.state.phrase_playhead
        page = self.state.page
        song_steps = self.state.song_pool
        cursor_phrase = self.state.cursor_phrase
        is_playing = self.state.is_playing

        mid = display.num_timeline_rows // 2 - 1
        cursor_pos = song_cursor if track_type == "song" else phrase_cursor
        offset = -min(mid, cursor_pos) if cursor_pos <= mid else -mid
        if cursor_pos > constants.timeline_length - mid:
            offset -= mid - (constants.timeline_length - cursor_pos)

        step_index = cursor_pos + y + offset
        if track_type == "song":
            step_num = song_steps[step_index]
        else:
            step_num = cursor_phrase[step_index]

        if step_index < 0 or step_index >= constants.timeline_length:
            text, text_color = None, None
        else:
            if track_type == "song":
                condition = (step_index == song_playhead and is_playing)
            else:
                condition = (step_index == phrase_playhead and is_playing) and (song_playhead == song_cursor)

            text_color = themeing.PLAYHEAD_COLOR if condition else themeing.WHITE
            text = f"{step_num:0>3}" if step_num is not None else ' - - '

        bg = themeing.BG_SHADOW if not y % 2 else themeing.TIMELINE_BG_HL
        page_check = 0 if track_type == "song" else 1
        if page == page_check and step_index == cursor_pos:
            cursor = themeing.CURSOR_COLOR
        elif step_index == cursor_pos:
            cursor = themeing.CURSOR_COLOR_ALT
        else:
            cursor = themeing.BLACK

        return [text, text_color, cursor, bg]


