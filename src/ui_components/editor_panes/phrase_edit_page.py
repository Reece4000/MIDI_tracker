from src.ui_components.editor_panes.menu_page import MenuPage
from config.render_map import *
from config import themeing

class PhrasePage(MenuPage):
    def __init__(self, x, y, tracker):
        super().__init__(x, y, "PHRASE", tracker)
        self.image = self.image = self.tracker.renderer.load_image(r"resources\editor_panes\phrase_page.png")
        self.cursor_x = 0
        self.cursor_y = 0
        self.title_bg_selected = themeing.PHRASE_TITLE_SELECTED
        self.title_bg_unselected = themeing.PHRASE_TITLE_UNSELECTED

    def update_view(self, tracker, editor_active):
        phrase_num = tracker.song[tracker.song_playhead]
        self.title = f"{self.name} {phrase_num}"
        super().update_view(tracker, editor_active)

        self.check_redraw(tracker.renderer.render_queue)
