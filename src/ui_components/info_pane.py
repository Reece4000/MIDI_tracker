from config import display, themeing
from src.ui_components.gui_elements import PatternInfoText, PlayPause, Button


class InfoPane:
    def __init__(self, tracker):
        self.tracker = tracker
        self.pattern_info_text = PatternInfoText()
        self.play_pause = PlayPause()
        self.options_button = Button(x=4, y=132, w=70, h=display.row_h - 4, text="OPTIONS",
                                     font="options_font", text_color=themeing.WHITE,
                                     bg_color=themeing.TIMELINE_BG_HL)
        self.initialise()

    def initialise(self):
        render_queue = self.tracker.renderer.render_queue
        render_queue.extendleft(self.pattern_info_text.initialise())
        render_queue.extendleft(self.play_pause.initialise())
        render_queue.extendleft(self.options_button.initialise())

    def update_view(self):
        play_pause = self.play_pause.check_for_state_change(self.tracker.midi_handler.pulse, self.tracker.is_playing)
        opt = self.options_button.check_for_state_change(self.tracker.mouse_x, self.tracker.mouse_y)
        pattern_text = self.pattern_info_text.check_for_state_change(self.tracker.cursor_pattern)

        for e in [play_pause, pattern_text, opt]:
            if e:
                self.tracker.renderer.render_queue.extendleft(e)
