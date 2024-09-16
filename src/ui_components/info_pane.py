from config import constants, display, themeing
from src.ui_components.view_component import ViewComponent
from src.gui_elements import PatternInfoText, PlayPause, OptionsButton
from config.constants import page_map as pmap


class InfoPane:
    def __init__(self, tracker):
        self.tracker = tracker
        render_queue = self.tracker.renderer.render_queue
        self.pattern_info_text = PatternInfoText()
        self.play_pause = PlayPause()
        self.options_button = OptionsButton()
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
