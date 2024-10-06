import pygame
from collections import deque
from src.utils import timing_decorator
from config import display, themeing, events
from config.render_map import *


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
            "textbox_font": pygame.font.Font(r'resources\fonts\pixel\PixelOperatorMono-Bold.ttf', 16),
            "textbox_small": pygame.font.Font(r'resources\fonts\pixel\PixelOperatorMono.ttf', 16),
        }

        self.text_cache = {}
        self.pane_cache = {}
        self.render_queue = deque()
        self.dirty_rects = []
        self.render_cycle = 0

        # https://www.iconpacks.net
        pygame.display.set_icon(pygame.image.load(r"resources/black-gameplay-symbol-20172.svg"))
        pygame.display.set_caption("GAMT")

        self.tracker.event_bus.subscribe(events.FULLSCREEN, self.toggle_fullscreen)
        self.tracker.event_bus.subscribe(events.QUIT, self.quit)

    @staticmethod
    def load_image(path):
        return pygame.image.load(path).convert()

    def quit(self):
        self.render_queue = None
        self.pane_cache = None
        self.text_cache = None
        pygame.quit()

    def toggle_fullscreen(self):
        pass  # may be more hassle than it's worth
        """
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((display.display_w, display.display_h), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((display.display_w, display.display_h))

        self.tracker.event_bus.publish(events.RENDERER_INITIALISED)
        """

    def render_element_from_queue(self):
        e = self.render_queue.pop()

        try:
            if e[0] == FILL:
                self.screen.fill(e[1])

            elif e[0] == LINE or e[0] == LINE_NO_DIRTY:
                color, start, end, width = e[1], e[2], e[3], e[4]
                l = pygame.draw.line(self.screen, color, start, end, width)
                if e[0] == LINE:
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

            elif e[0] == RECT or e[0] == RECT_NO_DIRTY:
                color, x, y, w, h, b = e[1], e[2], e[3], e[4], e[5], e[6]
                try:
                    r = pygame.draw.rect(self.screen, color, (x, y, w, h), b)
                    if e[0] == RECT:
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

            elif e[0] == CIRCLE or e[0] == CIRCLE_NO_DIRTY:
                color, center, radius, width = e[1], e[2], e[3], e[4]
                c = pygame.draw.circle(self.screen, color, center, radius, width)
                if e[0] == CIRCLE:
                    self.dirty_rects.append(c)

            elif e[0] == POLYGON or e[0] == POLYGON_NO_DIRTY:
                color, points, b = e[1], e[2], e[3]
                p = pygame.draw.polygon(self.screen, color, points, b)
                if e[0] == POLYGON:
                    self.dirty_rects.append(p)

            elif e[0] == "user input":
                pass

            elif e[0] == IMAGE:
                # image, x, y
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

    @timing_decorator
    def update_screen(self):
        pygame.display.update(self.dirty_rects)
        # pygame.display.update()
        self.dirty_rects = []
        self.render_cycle += 1

    def process_queue(self):
        while self.render_queue:
            self.render_element_from_queue()

