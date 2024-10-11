from config import display, themeing
from config.render_map import *
from src.ui_components.gui_elements import PatternInfoText, Button


class PlayPause:
    def __init__(self):
        self.x_screen = display.play_x + 2
        self.y_screen = display.play_y + 2
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

    def initialise(self):
        return [[RECT, themeing.BLACK, 2, 3, display.timeline_width, 40, 0],
                [RECT, (26, 26, 26), 2, 3, display.timeline_width, 40, 3],
                [RECT, (26, 26, 26), 2, 3, display.timeline_width, 18, 0],
                [RECT, themeing.BG_SEP, 2, 3, display.timeline_width - 1, 39, 1]]

    def check_for_state_change(self, current_pulse, is_playing):
        elems = []
        if is_playing:
            play_color = themeing.PLAYHEAD_COLOR_ALT if 96 > (current_pulse % 192) else themeing.PLAYHEAD_COLOR
            pause_color = themeing.PLAY_PAUSE_OFF
        else:
            play_color = themeing.PLAY_PAUSE_OFF
            pause_color = themeing.PLAY_PAUSE_OFF  # themeing.BLUE

        if play_color != self.play_color:
            elems.append([POLYGON, play_color, self.play_coords, 0])
            self.play_color = play_color

        if pause_color != self.pause_color:
            self.pause_color = pause_color

        return elems


class ClockIcon:
    def __init__(self):
        self.x_screen = 11
        self.y_screen = 94
        self.h = 24
        self.w = 24
        self.clock_active = True
        self.play_color = None

    def initialise(self):
        return [[RECT, themeing.BLACK, 2, self.y_screen-9, display.timeline_width, 40, 0],
                [RECT, (26, 26, 26), 2, self.y_screen-9, display.timeline_width, 40, 3],
                [RECT, (26, 26, 26), 2, self.y_screen-9, display.timeline_width, 18, 0],
                [RECT, themeing.BG_SEP, 2, self.y_screen-9, display.timeline_width - 1, 39, 1],
                [CIRCLE_NO_DIRTY, themeing.WHITE, (self.x_screen + 13, self.y_screen + 12), 11, 0],
                [CIRCLE_NO_DIRTY, themeing.BG_TASKPANE_HL, (self.x_screen + 13, self.y_screen + 12), 11, 2],
                [LINE, themeing.BLACK, (self.x_screen + 12, self.y_screen + 12), (self.x_screen + 12, self.y_screen + 5), 2],
                [LINE, themeing.BLACK, (self.x_screen + 12, self.y_screen + 12), (self.x_screen + 18, self.y_screen + 12), 2]]

    def check_for_state_change(self, current_pulse):
        elems = []
        if self.clock_active:
            on_pulse = 24 > (current_pulse % 48)
            play_color = (80, 80, 60) if on_pulse else (255, 255, 100)
            outline = themeing.BLACK if on_pulse else themeing.WHITE

            if play_color != self.play_color:
                elems.append([CIRCLE, play_color, (self.x_screen, self.y_screen-1), 3, 0])
                elems.append([CIRCLE, outline, (self.x_screen, self.y_screen-1), 4, 1])
                self.play_color = play_color

        return elems


class OptionsButton:
    def __init__(self, icon):
        self.options_icon = icon

    def initialise(self):
        return [[RECT, themeing.BLACK, 2, 44, display.timeline_width, 40, 0],
                [RECT, (26, 26, 26), 2, 44, display.timeline_width, 40, 3],
                [RECT, (26, 26, 26), 2, 44, display.timeline_width, 18, 0],
                [RECT, themeing.BG_SEP, 2, 44, display.timeline_width - 1, 39, 1],
                [IMAGE, self.options_icon, 10, 51]]


class InfoPane:
    def __init__(self, tracker):
        self.tracker = tracker
        self.pattern_info_text = PatternInfoText()
        self.play_pause = PlayPause()
        self.clock = ClockIcon()
        renderer = self.tracker.renderer
        options_icon = renderer.load_image(r"resources\icons\settings.png", scale=(25, 25))
        self.options_button = OptionsButton(options_icon)
        self.initialise()

    def initialise(self):
        renderer = self.tracker.renderer
        # timeline bg
        renderer.render_queue.appendleft([RECT, themeing.TIMELINE_BG, -1, 0, display.timeline_width+3, renderer.screen_h, 0])
        renderer.render_queue.appendleft([RECT, themeing.BG_SEP, -1, 0, display.timeline_width+5, renderer.screen_h, 1])
        renderer.render_queue.extendleft(self.play_pause.initialise())
        renderer.render_queue.extendleft(self.options_button.initialise())
        renderer.render_queue.extendleft(self.clock.initialise())

    def update_view(self):
        renderer = self.tracker.renderer
        play_pause = self.play_pause.check_for_state_change(self.tracker.midi_handler.pulse, self.tracker.is_playing)
        clock = self.clock.check_for_state_change(self.tracker.midi_handler.pulse)
        if play_pause:
            renderer.render_queue.extendleft(play_pause)
        if clock:
            renderer.render_queue.extendleft(clock)
