import traceback
from config import display, themeing, constants
from config.render_map import *
from src.utils import timing_decorator


class UiComponent:
    def __init__(self, parent=None):
        self.parent = parent
        self.state = []
        self.force = False

    def dirtied(self, new_state):
        if self.force or new_state != self.state:
            # print(f"new: {new_state}, old: {self.state}")
            self.state = new_state
            self.force = False
            return True
        return False


class TextBox:
    def __init__(self, x, y, w, h, text, text_color, bg_color):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.font = "textbox_font"
        self.force = False

        # text, font, color, bg_color
        self.state = [text, text_color, bg_color]

    def initialise(self):
        return self.update(self.text, self.state[1], self.state[2])

    def update(self, new_text, new_text_color, new_bg_color):
        if self.force:
            self.state = [new_text, new_text_color, new_bg_color]
            return [[RECT, self.state[2], self.x, self.y, self.w, self.h, 0],
                    [TEXT, self.font, self.state[1], self.state[0], self.x + 7, self.y, 0]]

        if [new_text, new_text_color, new_bg_color] != self.state:
            self.state = [new_text, new_text_color, new_bg_color]
            return [[RECT, self.state[2], self.x, self.y, self.w, self.h, 0],
                    [TEXT, self.font, self.state[1], self.state[0], self.x + 7, self.y, 0]]
        return []


class Button(UiComponent):
    def __init__(self, x, y, w, h, text, font, text_color, bg_color):
        super().__init__()
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.text = text
        self.font = font

        # text, font, color, bg_color
        self.state = [text_color, bg_color]

    def initialise(self):
        self.force = True
        return [[RECT, themeing.BG_COLOR, self.x-2, self.y-2, self.w + 4, self.h + 4, 0]]

    def check_for_state_change(self, mouse_x, mouse_y):
        elems = []
        if self.x + self.w >= mouse_x >= self.x and self.y + self.h >= mouse_y >= self.y:
            text_color, bg_color = themeing.BLACK, themeing.CURSOR_COLOR
        else:
            text_color, bg_color = themeing.WHITE, themeing.TIMELINE_BG_HL

        if self.dirtied([text_color, bg_color]):
            elems.append([RECT, bg_color, self.x, self.y, self.w, self.h, 0])
            elems.append([TEXT, self.font, text_color, self.text, self.x + 7, self.y, 0])

        return elems


class KeyHints:
    def __init__(self):
        self.x1 = display.pattern_area_width + display.timeline_width + display.col_w - 2
        self.x2 = self.x1 + 141
        self.y = display.display_h - 84

        self.img_x = display.pattern_area_width + display.timeline_width + 45
        self.img_y = display.display_h - 92

        self.current_items = None

        # self.controller_image = controller_image

    def check_for_state_change(self, items):
        elems = []
        if items != self.current_items:
            self.current_items = items

            elems.append([RECT, themeing.LINE_16_HL_BG, display.track_x_positions[7] + 100,
                          606, 250, 96, 0])

            elems.append([RECT, themeing.BG_COLOR, display.track_x_positions[7] + 102,
                          608, 246, 92, 0])

            to_render = [[ self.x1, self.y + 4, items[0][0]],         [ self.x1, self.y + 52, items[0][1]],
                         [ self.x1 - 24, self.y + 28, items[0][2]],   [ self.x1 + 24, self.y + 28, items[0][3]],

                         [self.x2, self.y + 4, items[1][0]],          [self.x2, self.y + 52, items[1][1]],
                         [self.x2 - 25, self.y + 29, items[1][2]],    [self.x2 + 25, self.y + 29, items[1][3]]]

            for itm in to_render:
                elems.append([CIRCLE, (40, 65, 65), (itm[0] + 12, itm[1] + 4), 15, 0])
                elems.append([CIRCLE, (100, 255, 255), (itm[0] + 12, itm[1] + 4), 15, 1])
                elems.append([TEXT, "tracker_info_font", themeing.WHITE, itm[2], itm[0], itm[1], 0])

            self.current_items = items

        return elems


class PageSwitchMarkers:
    def __init__(self):
        self.pattern_coords = (225, 1, 730, 704, 1)
        self.master_coords = (92, 1, 93, 704, 1)
        timeline_y = display.menu_height + display.row_h * 11 + 1
        self.song_track_coords = (4, timeline_y-2, display.timeline_cell_w+4, display.timeline_area_height+2, 1)
        self.phrase_track_coords = (41, timeline_y-2, display.timeline_cell_w+4, display.timeline_area_height+2, 1)
        self.current_coords = tuple(self.pattern_coords)

    def initialise(self):
        elems = []
        for coords in (self.pattern_coords, self.master_coords, self.song_track_coords, self.phrase_track_coords):
            elems.append([RECT, themeing.LINE_16_HL_BG, *coords])
        elems.append([RECT, themeing.CURSOR_COLOR, *self.current_coords])
        return elems

    def update(self, page, x):
        elems = []
        if self.current_coords is not None:
            elems.append([RECT, themeing.LINE_16_HL_BG, *self.current_coords])
        if page == 0:
            elems.append([RECT, themeing.CURSOR_COLOR, *self.song_track_coords])
            self.current_coords = tuple(self.song_track_coords)
        elif page == 1:
            elems.append([RECT, themeing.CURSOR_COLOR, *self.phrase_track_coords])
            self.current_coords = tuple(self.phrase_track_coords)
        elif page == 2:
            elems.append([RECT, themeing.CURSOR_COLOR, *self.master_coords])
            self.current_coords = tuple(self.master_coords)
        elif page == 3:
            elems.append([RECT, themeing.CURSOR_COLOR, *self.pattern_coords])
            self.current_coords = tuple(self.pattern_coords)
        return elems


class PlayPause:
    def __init__(self):
        self.x_screen = display.play_x + 1
        self.y_screen = display.play_y + 1
        self.h = 16
        self.w = 12
        self.play_coords = [
            (self.x_screen, self.y_screen),
            (self.x_screen + self.w, self.y_screen + self.h // 2),
            (self.x_screen, self.y_screen + self.h)
        ]

        self.pause_rect1 = (display.play_x + 19, display.play_y + 1, 6, 17, 0)
        self.pause_rect2 = (display.play_x + 27, display.play_y + 1, 6, 17, 0)

        # play color, pause color
        self.play_color = None
        self.pause_color = None



    @staticmethod
    def initialise():
        elems = []
        r, g, b = (60, 100, 100)
        w = 24
        centre = display.play_y + 9
        elems.append([CIRCLE, (r, g, b), (37, centre), w, 0])
        for i in range(w):
            elems.append([CIRCLE, (r, g, b), (37, centre), w - i, 0])
            r, g, b = r + 1, g + 1, b + 1
        return elems

    def check_for_state_change(self, current_pulse, is_playing):
        elems = []
        if is_playing:
            play_color = themeing.PLAYHEAD_COLOR_ALT if 48 > (current_pulse % 96) else themeing.PLAYHEAD_COLOR
            pause_color = themeing.PLAY_PAUSE_OFF
        else:
            play_color = themeing.PLAY_PAUSE_OFF
            pause_color = themeing.BLUE

        if play_color != self.play_color:
            elems.append([POLYGON, play_color, self.play_coords, 0])
            self.play_color = play_color

        if pause_color != self.pause_color:
            elems.append([RECT, pause_color, *self.pause_rect1])
            elems.append([RECT, pause_color, *self.pause_rect2])
            self.pause_color = pause_color

        return elems


class PatternInfoText:
    def __init__(self):
        self.x = 38
        self.y = 6
        self.w = 43
        self.sep = display.row_h
        self.color = themeing.BG_TASKPANE_HL

        # pattern num, bars, bpm, repeats, swing, scale
        self.items = [None, None, None, None, None, None]


    def initialise(self):
        elems = [[RECT, themeing.BG_TASKPANE_HL, 0, 0, 79, self.sep * 6 + 2, 0],
                 [RECT, themeing.BG_TASKPANE_HL, 0, 0, 79, self.sep * 6 + 2, 1, 0]]
        font = "tracker_info_font"
        for i, itm in enumerate(["PTN", "BAR", "BPM", "REP", "SWG", "SCA"]):
            txt_col = themeing.info_items_colors[i]
            elems.append([TEXT, font, txt_col, itm, 5, self.y + self.sep * i, 0])

        return elems

    def check_for_state_change(self, cursor_pattern):
        elems = []
        if cursor_pattern is None:
            items = ["--", "--", "--", "--", "--", "--"]
        else:
            bars = round((cursor_pattern.tracks[0].length / cursor_pattern.tracks[0].lpb) / 4, 2)
            items = [f"{cursor_pattern.num:0>3}", f"{bars}", f"{cursor_pattern.bpm}",
                     f"{cursor_pattern.loops}", f"{cursor_pattern.swing}", f"{cursor_pattern.scale}"]

        font = "param_display"
        for i, itm in enumerate(items):
            if itm != self.items[i]:
                txt_col = themeing.info_items_colors[i]
                elems.append([RECT, self.color, self.x, self.y + self.sep * i - 2, self.w - 6, self.sep - 2, 0])
                elems.append([TEXT, font, txt_col, itm, self.x + 2, self.y + self.sep * i - 1, 0])
                self.items[i] = itm

        return elems


class PatternCell(UiComponent):
    def __init__(self, x, y, parent, master=False):
        super().__init__(parent)
        self.x = x
        self.y = y
        if master:
            self.x_screen = display.master_track_x_position
        else:
            self.x_screen = display.track_x_positions[x]  # account for master track
        self.y_screen = display.menu_height + (y * display.row_h)
        self.w = display.col_w
        self.h = display.row_h - 1

        # components, line_bg_color, playhead_pos, cursor_arrows_color
        # top left cursor, top right, bottom left, bottom right
        self.state = [[], None, None, False, None, False, False, False]

    def check_for_state_change(self, pattern, step_index, track, track_index, playhead_step, render_queue):

        state = self.get_state(pattern, step_index, track, track_index, playhead_step)

        if self.dirtied(state):
            components, line_bg_color, playhead_pos, cursor_arrows_color, tl, tr, bl, br = state
            x, y, w, h = self.x_screen, self.y_screen + 2, self.w, self.h

            render_queue.appendleft([RECT, line_bg_color, x, y, w + 1, h, 0])  # cell bg

            if playhead_pos is not None:
                y_pos = y + playhead_pos
                render_queue.appendleft([LINE, themeing.PLAYHEAD_COLOR, (x, y_pos), (x + w, y_pos), 2])
            if components:
                offset = 8
                for i, (component, color) in enumerate(components):  # step_text
                    render_queue.appendleft([TEXT, "tracker_font", color, component, x + offset, y + 2, 0])
                    offset += 29

            if tl or tr or bl or br:
                self.draw_cell_cursor((tl, tr, bl, br), (x + 2, y + 1, w - 4, h - 5),
                                      cursor_arrows_color, render_queue)
            return 1
        return 0

    def get_selection_bounds(self, track_index, step_index):
        tl, tr, bl, br = 0, 0, 0, 0
        if step_index in self.parent.selected_rows and track_index in self.parent.selected_tracks:
            tl = 1 if (track_index == self.parent.selected_tracks[0] and
                       step_index == self.parent.selected_rows[0]) else 0

            tr = 1 if (track_index == self.parent.selected_tracks[-1] and
                       step_index == self.parent.selected_rows[0]) else 0

            bl = 1 if (track_index == self.parent.selected_tracks[0] and
                       step_index == self.parent.selected_rows[-1]) else 0

            br = 1 if (track_index == self.parent.selected_tracks[-1] and
                       step_index == self.parent.selected_rows[-1]) else 0

        return tl, tr, bl, br

    def get_state(self, pattern, step_index, track, track_index, playhead_step):

        tl, tr, bl, br = self.get_selection_bounds(track_index, step_index)
        step, playhead_pos, components = None, None, []

        cursor_arrows_color = themeing.CURSOR_COLOR if self.parent.active else themeing.CURSOR_COLOR_ALT

        if pattern is None or step_index < 0 or step_index >= track.length:
            line_bg_color = themeing.CURSOR_EMPTY_PTN_AREA if (tl or tr or bl or br) else themeing.BG_PTN
            step_state = (components, line_bg_color, playhead_pos, cursor_arrows_color, 0, 0, 0, 0)
        else:
            step = track.steps[step_index]
            components = step.get_display_text()
            if not step_index % track.lpb:  # beats
                line_bg_color = themeing.LINE_16_HL_BG
            elif (step_index * 2) % track.lpb < 2:  # eighth notes
                line_bg_color = themeing.LINE_8_HL_BG
            else:
                line_bg_color = themeing.LINE_BG

            line_bg_color = self.add_highlight(line_bg_color, track_index, step_index)

            if playhead_step == step_index:
                ticks, ticks_per_step = track.ticks, track.ticks_per_step
                playhead_pos = int((display.row_h-2) * ((ticks % ticks_per_step) / ticks_per_step))

            step_state = (components, line_bg_color, playhead_pos, cursor_arrows_color, tl, tr, bl, br)

        return step_state

    def add_highlight(self, line_bg_color, track_index, step_index):
        def get_color(hl):
            r, g, b = line_bg_color
            new_color = (r + hl[0], g + hl[1], b + hl[2])
            return new_color

        if self.parent.active:
            if track_index in self.parent.selected_tracks:
                line_bg_color = get_color(themeing.TRACK_SEL_FOCUSED)
                if step_index in self.parent.selected_rows:
                    line_bg_color = get_color(themeing.ROW_SEL_FOCUSED)
        else:
            if track_index in self.parent.selected_tracks:
                line_bg_color = get_color(themeing.TRACK_SEL_UNFOCUSED)
                if step_index in self.parent.selected_rows:
                    line_bg_color = get_color(themeing.ROW_SEL_UNFOCUSED)

        return line_bg_color

    @staticmethod
    def draw_cell_cursor(selection, display_coords, cursor_arrows_color, queue):
        tl, tr, bl, br = selection
        x, y, w, h = display_coords
        xt, xr, yt, yb = x, (x + w - 1), (y + 1), (y + h)
        line_horz, line_vert, b = display.cursor_arrow_w, display.cursor_arrow_h, display.cursor_arrow_b
        if tl:
            queue.appendleft([LINE, cursor_arrows_color, (xt, yt), (xt + line_horz, yt), b])
            queue.appendleft([LINE, cursor_arrows_color, (xt, yt), (xt, yt + line_vert), b])
        if tr:
            queue.appendleft([LINE, cursor_arrows_color, (xr + 1, yt), (xr + 1 - line_horz, yt), b])
            queue.appendleft([LINE, cursor_arrows_color, (xr, yt), (xr, yt + line_vert), b])
        if bl:
            queue.appendleft([LINE, cursor_arrows_color, (xt, yb), (xt + line_horz, yb), b])
            queue.appendleft([LINE, cursor_arrows_color, (xt, yb), (xt, yb - line_vert), b])
        if br:
            queue.appendleft([LINE, cursor_arrows_color, (xr + 1, yb), (xr + 1 - line_horz, yb), b])
            queue.appendleft([LINE, cursor_arrows_color, (xr, yb), (xr, yb - line_vert), b])


class TimelineCell(UiComponent):
    def __init__(self, x, y):
        super().__init__()
        self.x = 0
        self.y = y
        self.x_screen = x - 2
        self.y_screen = display.timeline_area_y + (y * display.row_h)

        # text, text color, cursor, bg
        self.state = [None, None, None, None]


class TimelineArrow(UiComponent):
    def __init__(self, points):
        super().__init__()
        self.points = points

        # visible
        self.state = [None]


class RowNumberCell(UiComponent):
    def __init__(self, y):
        super().__init__()
        self.y = y
        self.x_screen = display.x_row_labels - 3
        self.y_screen = display.menu_height + (y * display.row_h)

        # text, text color, outline color, bg
        self.state = [None, None, None, None]

    def check_for_state_change(self, num_steps, track_step_index, sel_rows, master_len, playhead_step, render_queue):
        if track_step_index < 0 or track_step_index >= num_steps:
            cell_text, text_color, outline, bg = None, None, themeing.BG_PTN, themeing.BG_PTN
        else:
            cell_text = f"{track_step_index:02}"
            if track_step_index in sel_rows:
                text_color = themeing.BLACK
            else:
                text_color = themeing.WHITE if track_step_index < master_len else themeing.ROW_NUM_EXCEEDS_MASTER_LEN
            outline = themeing.PLAYHEAD_COLOR if playhead_step == track_step_index else themeing.BLACK
            bg = themeing.CURSOR_COLOR if track_step_index in sel_rows else themeing.LINE_BG

        if self.dirtied([cell_text, text_color, outline, bg]):
            x, y = self.x_screen, self.y_screen + 1
            render_queue.appendleft([RECT, bg, x, y, display.row_labels_w, display.row_h, 0])
            render_queue.appendleft([RECT, outline, x, y, display.row_labels_w, display.row_h, 2])
            if cell_text is not None:
                offs = 5 if track_step_index < 100 else 1
                render_queue.appendleft([TEXT, "tracker_row_label_font", text_color, cell_text, x + offs, y + 2, 0])
            return 1
        return 0


class TrackBox(UiComponent):
    def __init__(self, x, parent, master=False):
        super().__init__(parent)
        self.x = x
        self.is_master = master
        if master:
            self.x_screen = display.master_track_x_position
        else:
            self.x_screen = display.track_x_positions[x] + 1
        self.y_screen = 3
        self.highlight = 0

        # text, outline_bg, main_bg, is_selected
        self.state = [None, None, None, False]

    def check_for_state_change(self, track_index, page, pattern, sel_tracks, render_queue): # curr_pulse, last_pulses
        state = self.get_state(track_index, page, pattern, sel_tracks)  # , curr_pulse, last_pulses)

        if self.dirtied(state):
            display_txt, outline_bg, bg_col, selected = state
            x, y, w, h = self.x_screen, self.y_screen, display.col_w - 1, display.menu_height - 4

            # track bg
            render_queue.appendleft([RECT, bg_col, x + 3, y + 5, w - 6, h - 8, 0])
            render_queue.appendleft([RECT, outline_bg, x, y + 2, w, h - 3, 2])

            start_x = x + display.col_w // 2  # Calculate the width of the text to center it correctly
            w = len(display_txt) * 7
            txt_col = outline_bg if not selected else (0, 0, 0)
            render_queue.appendleft([TEXT, "track_display_font", txt_col,
                                     display_txt, start_x - w // 2, 7, False, 0])

    def get_state(self, track_index, page, pattern, sel_tracks): # , curr_pulse, last_pulses):
        outline_bg = themeing.TRACKBOX_HL
        if pattern is None:
            display_txt = f"{constants.track_names[track_index]} (--/--)"
        else:
            if not self.is_master:
                track = pattern.midi_tracks[track_index]
                display_txt = f"{constants.track_names[track_index]} ({track.length}/{track.lpb})"
            else:
                track = pattern.master_track
                display_txt = f"M ({track.length}/{track.lpb})"


            if not track.is_master:  # handle coloring when notes are played, MIDI tracks only
                if not track.is_muted:
                    sel_r, sel_g, sel_b = outline_bg
                    sel_g = max(0 + self.highlight, sel_g)

                    outline_bg = (sel_r, sel_g, sel_b)
                else:
                    if track_index in sel_tracks:
                        outline_bg = themeing.TRACKBOX_OUTLINE_MUTED_SELECTED
                    else:
                        outline_bg = themeing.TRACKBOX_OUTLINE_MUTED

        selected = True if track_index in sel_tracks else False
        if selected:
            col = themeing.CURSOR_COLOR if self.parent.active else themeing.CURSOR_COLOR_ALT
        else:
            col = themeing.BG_PTN

        self.highlight -= 15

        return display_txt, outline_bg, col, selected


class OptionWindow:
    def __init__(self, renderer):
        self.renderer = renderer
        self.active = False
        self.header = None
        self.current_menu = None
        self.current_menu_page = None
        self.current_menu_item = None
        self.track_index = None
        self.menu_path = []
        self.y_path = []
        self.cursor_y = 0
        self.cursor_x = 0
        self.movement_amt = 50
        self.start_animation = 0

        self.options = {
            "Phrase": {
                0: {"Phrase": [0, ["Ins", "Clone", "D.Clone", "Dupl.", "Copy", "Paste", "Del"]]}
            },
            "Pattern": {
                0: {"Pattern": [0, ["Ins", "Clone", "Dupl.", "Copy", "Paste", "Del"]]}
            },
            "Master": {
                0: {"Master": [0, ["Length>", "LPB>", "BPM>", "Loops>"]]},
                1: {"Cmpnts": [0, ["Rev", "Sync"]]}
            },
            "Track": {
                0: {"Track": [0, ["Length>", "LPB>", "Swing>", "Scale>"]]},
                1: {"Cmpnts": [0, ["Rev", "Sync", "Spd up>", "Slw dn>"]]},
                2: {"Slw dn": [0, ["Mega", "Pussy"]],
                    "Spd up": [0, ["Mega", "Puss", "Big Puss"]]}
            },
            "Selection": {
                0: {"Selection": [0, ["Flip", "Rand", "Humnz", "Humnz", "Cmpnts>"]]},
                1: {"Cmpnts": [0, ["Rev", "Sync", "Spd up>", "Slw dn>"]]},
                2: {"Slw dn": [0, ["Mega", "Pussy"]],
                    "Spd up": [0, ["Mega", "Puss", "Big Puss"]]}
            }
        }

    def set_page(self):
        try:
            self.current_menu_page = self.options[self.current_menu][self.cursor_x][self.menu_path[-1]]
            self.cursor_y = self.current_menu_page[0]
            self.current_menu_item = self.current_menu_page[1][self.cursor_y]
        except Exception as e:
            print(f"An exception of type {type(e).__name__} occurred.")
            print(f"Error message: {e}")
            print("Stack trace:")
            traceback.print_exc()
            print(f"current menu: {self.current_menu}, current menu page: {self.current_menu_page}")

    def activate_menu(self, page, x):
        menu_map = {0: "Phrase", 1: "Pattern", 2: "Track"}
        menu = "Master" if page == 2 and x == 0 else menu_map[page]
        self.track_index = x
        self.start_animation = self.movement_amt
        if menu != self.current_menu:
            self.menu_path = []
            self.current_menu = menu
            self.cursor_x, self.cursor_y = 0, 0
            self.menu_path.append(self.current_menu)
            self.y_path = [0]
            self.set_page()

    def move_cursor(self, x, y):
        force_redraw = False
        if x != 0:
            # store current menu option
            temp_x = self.cursor_x + x
            if temp_x >= 0 and temp_x in self.options[self.current_menu].keys():
                sel_opt = self.current_menu_page[1][self.cursor_y]
                print(sel_opt, self.options[self.current_menu][temp_x])

                s = sel_opt.replace(">", "")
                if x > 0 and s in self.options[self.current_menu][temp_x].keys():
                    self.cursor_x = temp_x
                    self.menu_path.append(s)
                    self.start_animation = self.movement_amt
                    force_redraw = True
                elif x < 0:
                    self.cursor_x = temp_x
                    if len(self.menu_path) > 1:
                        self.menu_path.pop()
                    self.start_animation = self.movement_amt
                    force_redraw = True
                self.set_page()
            if force_redraw and self.track_index is not None:
                for cell in self.renderer.cells[self.track_index][:8]:
                    cell.force_update = True
            return

        if y != 0:
            self.cursor_y = (self.cursor_y + y) % len(self.current_menu_page[1])
            self.current_menu_page[0] = self.cursor_y
            self.current_menu_item = self.current_menu_page[1][self.cursor_y]

    def show(self, x_pos, y_pos, page):
        # Rendering logic
        rect_h = 14
        options_height = len(self.current_menu_page[1]) * (rect_h + 1)
        if page != 2:
            x = 1
            w = display.col_w - 10
            start_y = 200
        else:
            x = display.track_x_positions[x_pos]
            w = display.col_w - 2
            start_y = display.menu_height - 1

        movement_factor = 1 - self.start_animation // 4
        self.renderer.render_queue.appendleft([RECT, (10, 20, 20), x + 2, start_y, w, options_height - 3 + (movement_factor * 3), 0])

        for i, option in enumerate(self.current_menu_page[1]):
            y = start_y + (i * rect_h)
            color = (255, 255, 255) if i != self.cursor_y else themeing.CURSOR_COLOR
            if ">" in option:
                option = option.replace(">", " >")
            self.renderer.render_queue.appendleft([RECT, color, x + 2, y + (movement_factor * i), w, rect_h - 1, 0])
            self.renderer.render_queue.appendleft([TEXT, "options_font", (0, 0, 0), option, x + 4, y - 2 + (movement_factor * i), 0])

        if self.start_animation > 0:
            self.start_animation = max(0, self.start_animation - 10)