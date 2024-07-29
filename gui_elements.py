import pygame
import pygame_textinput


class UserInput:
    def __init__(self, prompt):
        self.prompt = prompt
        self.inputted_text = None
        self.done = False

    def get_text(self, screen, font, taskpane_color):
        # Create TextInput-object
        textinput = pygame_textinput.TextInputVisualizer()
        clock = pygame.time.Clock()

        while not self.done:
            # screen.fill((225, 225, 225))

            events = pygame.event.get()
            textinput.update(events)
            # redraw taskpane
            pygame.draw.rect(screen, taskpane_color, (0, 0, 2000, 75))
            # create prompt
            pygame.draw.rect(screen, (255, 255, 255), (10, 25, 340, 35))
            prompt = font.render(self.prompt, True, (255, 255, 255))
            screen.blit(prompt, (10, 5))

            screen.blit(textinput.surface, (15, 30))

            for event in events:
                if event.type == pygame.QUIT:
                    self.done = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.inputted_text = textinput.value
                        self.done = True
                    elif event.key == pygame.K_ESCAPE:
                        self.done = True

            pygame.display.update()
            clock.tick(30)


class Cell:
    def __init__(self, x, y, w, h, step):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.step = step

    def draw(self, screen, bg_color):
        note = self.step.note
        vel = self.step.vel
        pitchbend = self.step.pitchbend
        modwheel = self.step.modwheel
        pygame.draw.rect(screen, bg_color, (self.x, self.y, self.w, self.h))


class MenuPane:
    def __init__(self, color, x, y, w, h):
        self.color = color
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        # self.step = step

    def draw(self, screen, color, x, y, w, h):
        s = pygame.Surface((self.w, self.h))
        s.set_alpha(40)
        s.fill(self.color)
        screen.blit(s, (self.x, self.y))
        pygame.draw.rect(screen, (230, 203, 0), (self.x, self.y, self.w, self.h), 2)


class RenderQueue:
    def __init__(self):
        self.queue = []

    def clear(self):
        self.queue = []

    def add(self, component):
        self.queue.append(component)

    def add_pane(self, color, x, y, w, h):
        render_component = ("pane", [color, (w, h), (x, y)])
        self.queue.append(render_component)

    def add_line(self, color, start, end, height):
        render_component = ("line", [color, start, end, height])
        self.queue.append(render_component)

    def add_text(self, font, color, text, x, y, antialias=False):
        render_component = ("text", font, [text, antialias, color], (x, y))
        self.queue.append(render_component)

    def add_rect(self, color, x, y, w, h, b=None):
        if b is not None:
            render_component = ("rect", [color, (x, y, w, h), b])
        else:
            render_component = ("rect", [color, (x, y, w, h)])
        self.queue.append(render_component)

    def add_circle(self, color, center, radius, w=None):
        if w is not None:
            render_component = ("circle", [color, center, radius, w])
        else:
            render_component = ("circle", [color, center, radius])
        self.queue.append(render_component)

    def add_triangle(self, color, points, b=None):
        if b is not None:
            render_component = ("polygon", [color, points, b])
        else:
            render_component = ("polygon", [color, points])
        self.queue.append(render_component)
