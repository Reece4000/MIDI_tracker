from src.ui_components.editor_panes.menu_page import MenuPage
from config.render_map import *
from config import themeing


class PatternPage(MenuPage):
    def __init__(self, x, y, tracker):
        super().__init__(x, y, "PATTERN", tracker)
        self.image = self.image = self.tracker.renderer.load_image(r"resources\editor_panes\pattern_page.png")
        self.cursor_x = 0
        self.cursor_y = 0
        self.title_bg_selected = themeing.PATTERN_TITLE_SELECTED
        self.title_bg_unselected = themeing.PATTERN_TITLE_UNSELECTED

    def update_view(self, tracker, editor_active):
        pattern_num = tracker.cursor_pattern.num
        self.title = f"{self.name} {pattern_num}"
        super().update_view(tracker, editor_active)

        self.check_redraw(tracker.renderer.render_queue)
