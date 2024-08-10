import pygame
from sequencer import Sequencer
from gui_elements import UserInput
from key_handler import KeyHandler
import constants as cfg
import json
from time import perf_counter
import timeit


class Renderer:
    def __init__(self, screen):
        self.render_queue = []
        self.screen = screen
        self.fonts = {
            "tracker_info_font": pygame.font.Font(r'fonts\pixel\PixelOperatorMonoHB8.ttf', 8),
            "tracker_MIDI_out_font": pygame.font.Font(r'fonts\pixel\PixelOperatorSC-Bold.ttf', 24),
            "track_display_font": pygame.font.Font(r'fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
            "tracker_font": pygame.font.Font(r'fonts\pixel\PixelOperatorMonoHB.ttf', 16),
            "tracker_font_bold": pygame.font.Font(r'fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
            "tracker_row_label_font": pygame.font.Font(r'fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
            "tracker_timeline_font": pygame.font.Font(r'fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
        }
        self.text_cache = {}

    def fill(self, color):
        self.screen.fill(color)

    def add_line(self, color, start, end, height):
        pygame.draw.line(self.screen, color, start, end, height)

    def add_pane(self, color, x, y, w, h):
        s = pygame.Surface((w, h))
        s.set_alpha(40)
        s.fill(color)
        self.screen.blit(s, (x, y))
        pygame.draw.rect(s, (230, 203, 0), (x, y, w, h))

    def add_rect(self, color, x, y, w, h, b=None):
        if b is not None:
            pygame.draw.rect(self.screen, color, (x, y, w, h), b)
        else:
            pygame.draw.rect(self.screen, color, (x, y, w, h))

    def add_text(self, font, color, text, x, y, antialias=False, return_width=False):
        key = (font, color, text, antialias, x, y)

        if key not in self.text_cache:
            rendered_text = self.fonts[font].render(text, antialias, color)
            self.text_cache[key] = rendered_text
        else:
            rendered_text = self.text_cache[key]

        if return_width:
            return rendered_text.get_width()

        self.screen.blit(rendered_text, (x, y))

    def add_circle(self, color, center, radius, width):
        pygame.draw.circle(self.screen, color, center, radius, width)

    def add_polygon(self, color, points, b=None):
        if b is not None:
            pygame.draw.polygon(self.screen, color, points, b)
        else:
            pygame.draw.polygon(self.screen, color, points)

    def user_input(self, prompt, font, color):
        user_input = UserInput(prompt)
        user_input.get_text(self.screen, self.fonts[font], color)
        return user_input.inputted_text


class Tracker:
    def __init__(self, track_count, length):
        self.center_y = cfg.HEIGHT // 2
        self.cursor_x, self.cursor_y, self.cursor_x_span, self.cursor_y_span = 0, 0, 0, 0
        self.song_cursor, self.song_cursor_span, self.phrase_cursor, self.phrase_cursor_span = 0, 0, 0, 0
        self.octave_mod = 0

        # positional indices for detecting whether cursor_x on sequencer tracks
        self.phrase_track_index = track_count
        self.song_track_index = track_count + 1

        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((cfg.WIDTH, cfg.HEIGHT))
        pygame.display.set_caption("Tracker")
        pygame.key.set_repeat(180, 40)

        self.sequencer = Sequencer(timeline_length=length,
                                   num_patterns=1024,
                                   track_count=track_count)
        self.renderer = Renderer(self.screen)
        self.keyhandler = KeyHandler(tracker=self)

        self.clipboard = []
        self.page = 2  # 0 = song, 1 = phrase, 2 = pattern
        self.cycles = 0
        self.render_cycle = 0
        self.io_return = None

    def update_sequencer_time(self, last_update_time):
        return self.sequencer.update_time(perf_counter(), last_update_time)

    def running_loop(self):
        last_update_time = perf_counter()
        running = True

        while running:
            ret = self.keyhandler.check_for_events()
            if ret == "Exit":
                running = False

            self.renderer.fill(cfg.BG_COLOR)  # bg
            last_update_time = self.update_sequencer_time(last_update_time)
            self.render_pattern()  # draw pattern grid
            last_update_time = self.update_sequencer_time(last_update_time)
            self.renderer.add_rect(cfg.BG_DARKER, 0, 0, 95, 2000)  # timeline background
            self.render_timeline()  # draw timeline
            last_update_time = self.update_sequencer_time(last_update_time)
            self.render_playheads()  # draw playhead
            last_update_time = self.update_sequencer_time(last_update_time)
            x, y, w, h = self.get_selection_coords(for_display=True)
            self.render_cursors(x, y, w, h)  # draw row/cell cursors
            last_update_time = self.update_sequencer_time(last_update_time)
            self.renderer.add_rect(cfg.BG_TASKPANE, 0, 0, 2000, cfg.MENU_HEIGHT)
            self.render_info_pane()  # draw taskbar_pane
            last_update_time = self.update_sequencer_time(last_update_time)

            self.cycles += 1
            pygame.display.update()

        print("Cleaning up and exiting...")
        self.sequencer.quit()
        pygame.quit()

    def reset(self):
        self.sequencer.reset()
        self.cursor_x, self.cursor_y = 0, 0
        self.cursor_x_span, self.cursor_y_span = 0, 0
        self.song_cursor, self.song_cursor_span = 0, 0
        self.phrase_cursor, self.phrase_cursor_span = 0, 0
        self.page = 2

    def toggle_playback(self):
        if self.sequencer.is_playing:
            self.sequencer.stop_playback()
        else:
            self.sequencer.set_playing_pattern_to_cursor(self.phrase_cursor, self.song_cursor)
            if self.sequencer.cursor_pattern is not None:
                self.sequencer.start_playback()

    def toggle_mute(self, track_indices=None):
        if track_indices is None:
            x, xs = self.cursor_x, self.cursor_x_span
            x = x - xs if xs > 0 else x
            w = max((x - xs), x) - min((x - xs), x) + 1
            track_indices = [i for i in range(x, x + w)]
        for index in track_indices:
            track = self.sequencer.cursor_pattern.tracks[index]
            if not track.is_master:
                self.sequencer.handle_mute(track)

    def preview_note(self, note, velocity=80):
        if not self.sequencer.is_playing:
            track = self.sequencer.cursor_pattern.tracks[self.cursor_x]
            if track.is_master:
                return
            if not track.is_muted:
                self.sequencer.midi_handler.handle_note(track.channel, note, velocity)

    def add_midi_note(self, note):
        if note != "OFF":
            octave = int(note[-1]) + self.octave_mod
            note = note[:-1] + str(octave)
        pos, vel = self.cursor_y, self.sequencer.last_vel
        self.sequencer.cursor_pattern.tracks[self.cursor_x].update_step(pos, note, vel, None, None)
        # debugging
        self.preview_note(note)

    def add_master_component(self, data):
        if data == "C-3":
            self.sequencer.cursor_pattern.master_track.add_component(self.cursor_y, "R")
        elif data == "D-3":
            self.sequencer.cursor_pattern.master_track.add_component(self.cursor_y, "S")

    def add_step(self, data):
        if self.cursor_x == 0:  # on master track
            self.add_master_component(data)
        else:
            self.add_midi_note(note=data)

    def save_song(self):
        self.sequencer.stop_playback()
        save_name = self.renderer.user_input("Please enter a save name, then press Enter",
                                             "tracker_font", cfg.BG_TASKPANE)

        serialised_sequencer_data = self.sequencer.json_serialize()
        save_name = "save_files/" + save_name if not save_name.startswith("save_files/") else save_name
        save_name += ".json" if not save_name.endswith(".json") else ""

        with open(save_name, 'w') as file:
            json.dump(serialised_sequencer_data, file)

        print("Song saved successfully!")

    def load_song(self):
        self.sequencer.stop_playback()
        # check whether patterns is empty, if not ask user if they want to save
        load_name = self.renderer.user_input("Please enter the project name, then press Enter",
                                             "tracker_font", cfg.BG_TASKPANE)

        if not load_name:
            return
        load_name = "save_files/" + load_name if not load_name.startswith("save_files/") else load_name
        load_name += ".json" if not load_name.endswith(".json") else ""
        self.cursor_x = self.cursor_y = self.cursor_x_span = self.cursor_y_span = 0

        with open(load_name, 'r') as file:
            serialised_sequencer_data = json.load(file)
            self.sequencer.load_from_json(serialised_sequencer_data)

        self.page = 2
        self.cursor_x = self.cursor_y = self.cursor_x_span = self.cursor_y_span = 0
        self.song_cursor = self.phrase_cursor = 0
        print("Song loaded successfully!")

    def new_song(self):
        self.sequencer.stop_playback()
        ret = self.renderer.user_input("Do you want to save the current project first? (Y/N)",
                                       "tracker_font", cfg.BG_TASKPANE)
        if ret.lower() == "y":
            self.save_song()
        self.reset()

    def insert(self, opt):
        if opt == 'pattern':
            if self.phrase_cursor + 1 >= self.sequencer.timeline_length:
                return
            # get next unused pattern number
            for i in range(self.sequencer.max_patterns):
                if i not in self.sequencer.patterns.keys():
                    while self.sequencer.cursor_phrase[self.phrase_cursor] is not None:
                        self.phrase_cursor += 1
                    self.sequencer.update_phrase_step(self.phrase_cursor, i + 1)
                    break

        elif opt == 'phrase':
            if self.song_cursor + 1 >= self.sequencer.timeline_length:
                return
            for i in range(self.sequencer.timeline_length):
                if i not in self.sequencer.phrases.keys():
                    while self.sequencer.song_steps[self.song_cursor] is not None:
                        self.song_cursor += 1
                    self.sequencer.update_song_step(self.song_cursor, i + 1)
                    self.page = 0
                    break

    def jump_page(self, opt):
        if opt == 'down':
            if self.phrase_cursor + 1 < self.sequencer.timeline_length:
                if self.sequencer.cursor_phrase[self.phrase_cursor + 1] is None:
                    self.insert('pattern')
                else:
                    self.phrase_cursor += 1
                    self.sequencer.set_cursor_pattern(self.sequencer.cursor_phrase[self.phrase_cursor])

        elif opt == 'up':
            if self.phrase_cursor - 1 >= 0:
                if self.sequencer.cursor_phrase[self.phrase_cursor - 1] is not None:
                    self.phrase_cursor -= 1
                    self.sequencer.set_cursor_pattern(self.sequencer.cursor_phrase[self.phrase_cursor])

    def copy_selection(self):
        x, y, w, h = self.get_selection_coords()
        self.clipboard = []
        for track in range(w + 1):
            self.clipboard.append([])
            for row in range(h + 1):
                step = self.sequencer.cursor_pattern.tracks[x + track].steps[y + row]
                self.clipboard[track].append(step)

    def paste_selection(self):
        for track in range(len(self.clipboard)):
            for row in range(len(self.clipboard[track])):
                if (self.cursor_x + track < self.sequencer.track_count and
                        self.cursor_y + row < self.sequencer.cursor_pattern.length):
                    step = self.clipboard[track][row]
                    self.sequencer.cursor_pattern.tracks[self.cursor_x + track].update_step(self.cursor_y + row,
                                                                                            note=step.note,
                                                                                            vel=step.vel)

    # so we want to update the pattern step in the phrase track to the new pattern number
    # then we want to update the current pattern to the new pattern number

    def update_timeline_step(self, val):
        if self.page == 0:
            self.sequencer.update_song_step(self.song_cursor, val)
        elif self.page == 1:
            if self.sequencer.song_steps[self.song_cursor] is not None:
                self.sequencer.update_phrase_step(self.phrase_cursor, val)

    def move_cursor(self, x, y, expand_selection=False):
        prev_x, prev_y, prev_song, prev_phrase = self.cursor_x, self.cursor_y, self.song_cursor, self.phrase_cursor
        if self.page == 0:
            if x > 0:
                self.page = 1
            if y > 0:
                self.song_cursor = min(self.sequencer.timeline_length - 1, self.song_cursor + y)
            elif y < 0:
                self.song_cursor = max(0, self.song_cursor + y)

            if self.song_cursor != prev_song:
                self.phrase_cursor = 0
                self.sequencer.set_current_phrase(self.sequencer.song_steps[self.song_cursor])

        elif self.page == 1:
            if x != 0:
                if not (self.sequencer.cursor_pattern is None and x > 0):
                    self.page += (1 if x > 0 else -1)
            elif y > 0:
                self.phrase_cursor = min(self.sequencer.timeline_length - 1, self.phrase_cursor + y)
            elif y < 0:
                self.phrase_cursor = max(0, self.phrase_cursor + y)
            if self.phrase_cursor != prev_phrase:
                self.sequencer.set_cursor_pattern(self.sequencer.cursor_phrase[self.phrase_cursor])
        elif self.page == 2:
            if self.cursor_x == 0 and x < 0:
                self.page = 1
            if x > 0:
                self.cursor_x = min(self.sequencer.track_count - 1, self.cursor_x + x)
            elif x < 0:
                self.cursor_x = max(0, self.cursor_x + x)
            if y > 0:
                self.cursor_y = min(self.sequencer.cursor_pattern.tracks[self.cursor_x].length - 1, self.cursor_y + y)
            elif y < 0:
                self.cursor_y = max(0, self.cursor_y + y)

            if expand_selection and not (self.sequencer.is_playing and self.sequencer.follow_playhead):
                self.cursor_x_span += self.cursor_x - prev_x
                self.cursor_y_span += self.cursor_y - prev_y

            if not expand_selection:
                self.cursor_x_span, self.cursor_y_span = 0, 0

    def pattern_seek(self, opt, expand_selection):
        delta_x, delta_y = 0, 0
        if opt == 'left':
            delta_x = 0 - self.cursor_x
            self.cursor_x = 0
        elif opt == 'right':
            delta_x = self.sequencer.track_count - 1 - self.cursor_x
            self.cursor_x = self.sequencer.track_count - 1
        elif opt == 'up':
            if self.cursor_y > 0:
                self.cursor_y -= 1
                delta_y -= 1
                track = self.sequencer.cursor_pattern.tracks[self.cursor_x]
                while track.steps[self.cursor_y].note is None:
                    if self.cursor_y == 0:
                        break
                    delta_y -= 1
                    self.cursor_y -= 1
        elif opt == 'down':
            if self.cursor_y < self.sequencer.cursor_pattern.tracks[self.cursor_x].length - 1:
                self.cursor_y, delta_y = self.cursor_y + 1, 1
                track = self.sequencer.cursor_pattern.tracks[self.cursor_x]
                while not track.steps[self.cursor_y].has_data():
                    if self.cursor_y == self.sequencer.cursor_pattern.tracks[self.cursor_x].length - 1:
                        break
                    self.cursor_y += 1
                    delta_y += 1
        if expand_selection and not (self.sequencer.is_playing and self.sequencer.follow_playhead):
            self.cursor_x_span += delta_x
            self.cursor_y_span += delta_y

    def song_seek(self):
        print("Song seek, to do")

    def phrase_seek(self):
        print("Phrase seek, to do")

    def seek(self, opt, expand_selection=False):
        if self.page == 0:
            self.song_seek()
        elif self.page == 1:
            self.phrase_seek()
        elif self.page == 2:
            self.pattern_seek(opt, expand_selection)

    def duplicate_selection(self):
        x, y, w, h = self.get_selection_coords()
        for track in range(w + 1):
            for row in range(h + 1):
                step = self.sequencer.cursor_pattern.tracks[x + track].steps[y + row]
                if y + row + (h + 1) < self.sequencer.cursor_pattern.tracks[self.cursor_x].length:
                    self.sequencer.cursor_pattern.tracks[x + track].update_step(y + row + (h + 1), note=step.note,
                                                                                vel=step.vel)
        # update cursor_y and y_span
        max_len = self.sequencer.cursor_pattern.tracks[self.cursor_x].length
        if self.cursor_y_span < 0:
            if not self.cursor_y + (h + 1) * 2 < max_len:
                print("Cond 1.1", self.cursor_y, self.cursor_y_span, max_len, h)
                if self.cursor_y + h + 1 < max_len:
                    self.cursor_y += h + 1
                    self.cursor_y_span = -1 * (max_len - 1 - self.cursor_y)
                else:
                    self.cursor_y = max_len - 1
                    self.cursor_y_span = 0
            else:
                print("Cond 1.2", self.cursor_y, self.cursor_y_span, max_len, h)
                self.cursor_y += h + 1

        elif self.cursor_y + h + 1 < max_len:
            print("Cond 2", self.cursor_y, self.cursor_y_span, max_len, h)
            self.cursor_y += h + 1

        elif self.cursor_y + h >= max_len - 1:
            print("Cond 3", self.cursor_y, self.cursor_y_span, max_len, h)
            self.cursor_y = max_len - 1
            self.cursor_y_span = max_len - 1 - self.cursor_y

        else:
            # think the above should cover all cases but just in case
            print(f"Duplication issue: {self.cursor_y}, {self.cursor_y_span}, "
                  f"{self.sequencer.cursor_pattern.length}, {h}")

    def update_vel(self, val):
        x, y, w, h = self.get_selection_coords()
        for track in range(w + 1):
            for row in range(h + 1):
                curr_vel = self.sequencer.cursor_pattern.tracks[x + track].steps[y + row].vel
                note = self.sequencer.cursor_pattern.tracks[x + track].steps[y + row].note
                if curr_vel is not None:
                    if val > 0:
                        new_vel = min(99, int(curr_vel) + val)
                    else:
                        new_vel = max(0, int(curr_vel) + val)

                    self.sequencer.cursor_pattern.tracks[x + track].update_step(y + row, vel=new_vel)


                    if w == 0 and h == 0:  # only preview if single cell
                        self.sequencer.last_vel = new_vel
                        self.preview_note(note, new_vel)

    def delete_selection(self):
        if self.page == 2:
            x, y, w, h = self.get_selection_coords()
            for track in range(w + 1):
                for row in range(h + 1):
                    self.sequencer.cursor_pattern.tracks[x + track].clear_step(y + row)

    def adjust_length(self, increment):
        selected_tracks = self.get_selected_tracks()
        if self.sequencer.cursor_pattern is not None:
            for track in selected_tracks:
                self.sequencer.cursor_pattern.tracks[track].adjust_length(increment)
            self.sequencer.update_sequencer_params()

    def adjust_lpb(self, increment):
        selected_tracks = self.get_selected_tracks()
        if self.sequencer.cursor_pattern is not None:
            for track in selected_tracks:
                self.sequencer.cursor_pattern.tracks[track].adjust_lpb(increment)
            self.sequencer.update_sequencer_params()

    def adjust_bpm(self, increment):
        if self.sequencer.cursor_pattern is not None:
            new_bpm = min(max(1, self.sequencer.cursor_pattern.bpm + increment), 300)
            self.sequencer.cursor_pattern.bpm = new_bpm
            self.sequencer.update_sequencer_params()
            self.sequencer.last_bpm = new_bpm

    def get_selection_coords(self, for_display=False):
        xs, ys = self.cursor_x_span, self.cursor_y_span
        x = self.cursor_x - xs if xs > 0 else self.cursor_x
        h = max((self.cursor_y - ys), self.cursor_y) - min((self.cursor_y - ys), self.cursor_y)
        w = max((self.cursor_x - xs), self.cursor_x) - min((self.cursor_x - xs), self.cursor_x)

        if not for_display:
            y = self.cursor_y - ys if ys > 0 else self.cursor_y
        else:
            x = (x * cfg.col_w) + cfg.tr_offset_x + 15
            y = self.center_y - (h * cfg.row_h) if ys > 0 else self.center_y
            w = (w + 1) * cfg.col_w
            h = (h + 1) * cfg.row_h

        return x, y, w, h

    def get_selected_tracks(self):
        x, xs = self.cursor_x, self.cursor_x_span
        x = x - xs if xs > 0 else x
        w = max((x - xs), x) - min((x - xs), x) + 1
        return [i for i in range(x, x + w)]

    def get_selected_rows(self):
        y, ys = self.cursor_y, self.cursor_y_span
        y = y - ys if ys > 0 else y
        h = max((y - ys), y) - min((y - ys), y) + 1
        return [i for i in range(y, y + h)]

    def render_pattern(self):
        window_height = pygame.display.get_surface().get_height()
        # Compute offset_y to center the current step
        if self.sequencer.cursor_pattern is None:
            return None

        row_labels_rendered = set()
        track_container_xy = [[None, None] for _ in range(self.sequencer.track_count)]
        selected_rows = self.get_selected_rows()

        for track_index, track in enumerate(self.sequencer.cursor_pattern.tracks):
            track_x = cfg.start_x + (track_index * cfg.col_w) + 40
            track_container_xy[track_index][0] = track_x - 3

            for step_index, step in enumerate(track.steps):
                row_y = (step_index * cfg.row_h) + (self.center_y - (self.cursor_y * cfg.row_h))
                # don't draw if outside of window
                if step_index == 0:
                    track_container_xy[track_index][1] = row_y

                if step_index > track.length - 1:
                    break

                if row_y < cfg.MENU_HEIGHT - 5 or row_y > window_height:  # top of window
                    continue

                # add line background
                if not step_index % track.lpb:  # beats
                    line_bg_color = cfg.LINE_16_HL_BG
                elif (step_index * 2) % track.lpb < 2:  # eighth notes
                    line_bg_color = cfg.LINE_8_HL_BG
                else:
                    line_bg_color = cfg.LINE_BG

                # line bg
                self.renderer.add_line(line_bg_color, (track_x, row_y + 10),
                                       (track_x + cfg.col_w - 10, row_y + 10), cfg.row_h - 1)

                # row cursor
                if step_index not in row_labels_rendered:
                    row_label_col = (255, 255, 255)
                    if step_index in selected_rows and self.sequencer.cursor_pattern is not None:
                        self.renderer.add_rect(cfg.CURSOR_COLOR, cfg.start_x, row_y + 1, 22, cfg.row_h - 1)
                        row_label_col = (0, 0, 0)
                    elif step_index >= self.sequencer.cursor_pattern.master_track.length:
                        row_label_col = (255, 150, 150)

                    # row label
                    self.renderer.add_text("tracker_row_label_font", row_label_col, f"{step_index:02}",
                                           cfg.start_x + 3, row_y + 2)
                    row_labels_rendered.add(step_index)

                step_x = cfg.start_x + (track_index * cfg.col_w) + 46
                if step.type == 'midi':
                    # step_text
                    i = 0
                    fonts = ["tracker_font", "tracker_font", "tracker_font_bold"]
                    x_positions = [step_x, step_x + 30, step_x + 54]
                    y_positions = [row_y + 2, row_y + 2, row_y + 2]
                    for component, color in step.get_visible_components():
                        self.renderer.add_text(fonts[i], color, component, x_positions[i], y_positions[i])
                        i += 1
                elif step.type == 'master':
                    # step_text
                    offset = 0
                    for component, color in step.get_visible_components():
                        self.renderer.add_text("tracker_font", color, component, step_x + offset, row_y + 2)
                        offset += 12

            x, y = track_container_xy[track_index]
            w, h = cfg.col_w - 3, (track.length * cfg.row_h) + 1
            thickness = 1 if not self.cursor_x == track_index else 3
            self.renderer.add_rect(cfg.track_colors[track_index], x, y, w, h, thickness)
        return

    def render_timeline(self):
        for step_index in range(self.sequencer.timeline_length):

            # SONG TRACK
            song_playhead_pos = self.sequencer.song_playhead_pos
            if song_playhead_pos < step_index:
                row_y = self.center_y + (step_index - self.song_cursor) * cfg.row_h
            else:
                row_y = self.center_y - (self.song_cursor - step_index) * cfg.row_h

            diff = row_y - self.center_y
            diff = diff * -1 if diff < 0 else diff // 1.8
            r, g, b = max(245 - diff, 26), max(255 - diff, 36), max(255 - diff, 36)

            step = self.sequencer.song_steps[step_index]
            if step is not None and step_index == self.sequencer.song_playhead_pos and self.sequencer.is_playing:
                song_step_color = cfg.PLAYHEAD_COLOR
            elif self.sequencer.song_steps[step_index] is not None:
                song_step_color = (r, g, b)
            else:
                song_step_color = (r, g, b)

            if step is None:
                step = '- -'

            self.renderer.add_text("tracker_timeline_font", song_step_color, f"{step:0>2}", 18, row_y + 2)

            # PHRASE TRACK
            phrase_playhead_pos = self.sequencer.phrase_playhead_pos
            if phrase_playhead_pos < step_index:
                row_y = self.center_y + (step_index - self.phrase_cursor) * cfg.row_h
            else:
                row_y = self.center_y - (self.phrase_cursor - step_index) * cfg.row_h

            diff = row_y - self.center_y
            diff = diff * -1 if diff < 0 else diff // 1.8
            r, g, b = max(245 - diff, 20), max(255 - diff, 32), max(255 - diff, 32)

            phrase_step_num = self.sequencer.cursor_phrase[step_index]
            on_phrase = self.sequencer.song_playhead_pos == self.song_cursor
            x = 55
            if step_index == self.sequencer.phrase_playhead_pos and self.sequencer.is_playing and on_phrase:
                phrase_step_color = cfg.PLAYHEAD_COLOR
            elif self.sequencer.cursor_phrase[step_index] is not None:
                phrase_step_color = (r, g, b)
            else:
                phrase_step_num, phrase_step_color, x = '- -', (r, g, b), 59

            if phrase_step_num is not None:
                self.renderer.add_text("tracker_timeline_font", phrase_step_color,
                                       f"{phrase_step_num:0>3}", x, row_y + 2)

    def render_playheads(self):
        if self.sequencer.cursor_pattern is not None:
            if self.sequencer.is_cursor_on_playing_pattern(self.song_cursor, self.phrase_cursor):
                master_track = self.sequencer.cursor_pattern.master_track
                playhead_pos_y = ((master_track.playhead_pos * cfg.row_h) +
                                  (self.center_y - (self.cursor_y * cfg.row_h)))

                self.renderer.add_rect(cfg.PLAYHEAD_COLOR, cfg.start_x - 2, playhead_pos_y, 26, cfg.row_h + 1, 2)
                # self.renderer.add_line(cfg.PLAYHEAD_COLOR, (cfg.start_x, playhead_pos_y),
                #                        (cfg.pattern_line_len, playhead_pos_y), 2)

                # add individual track playheads
                for index, track in enumerate(self.sequencer.cursor_pattern.tracks):
                    if track.playhead_pos is not None:
                        ticks_per_step = 96 // track.lpb
                        row_ticks = track.ticks % ticks_per_step
                        y_offset = int(cfg.row_h * (row_ticks / ticks_per_step))
                        if not track.is_master and track.is_reversed:
                            y_offset = (y_offset * -1) + cfg.row_h
                        playhead_pos_y = ((track.playhead_pos * cfg.row_h) +
                                          (self.center_y - (self.cursor_y * cfg.row_h) + y_offset))

                        playhead_x = cfg.start_x + (index * cfg.col_w) + 37
                        self.renderer.add_line(cfg.PLAYHEAD_COLOR, (playhead_x, playhead_pos_y),
                                               (playhead_x + cfg.col_w - 4, playhead_pos_y), 2)

    def render_cursors(self, x, y, w, h):
        cursor_offset_x, cursor_offset_w = cfg.start_x - 2, 15

        # song edit cursor
        self.renderer.add_rect(cfg.CURSOR_COLOR if self.page == 0 else cfg.CURSOR_COLOR_ALT, 10,
                               self.center_y, 34, 1 + cfg.row_h, 2)

        # phrase edit cursor
        self.renderer.add_rect(cfg.CURSOR_COLOR if self.page == 1 else cfg.CURSOR_COLOR_ALT, 50,
                               self.center_y, 34, 1 + cfg.row_h, 2)

        if self.sequencer.cursor_pattern is not None:
            # cell edit cursor
            color = cfg.CURSOR_COLOR if self.page == 2 else cfg.CURSOR_COLOR_ALT

            x_left = x + cursor_offset_x
            curs_w = w - cursor_offset_w
            curs_h = h - 3
            x_right = x_left + w - cursor_offset_w
            y_top = y + 2
            y_bottom = y_top + curs_h - 2

            self.renderer.add_pane((255, 255, 0), x_left, y_top, curs_w + 2, curs_h)

            if self.page == 2:
                chk = self.sequencer.ticks % 96
                if 72 > chk > 48:
                    x_left -= 2
                    x_right += 2
                    curs_w += 4
                    curs_h += 2
                    y_top -= 2
                    y_bottom += 2
                elif chk > 24:
                    x_left -= 1
                    x_right += 1
                    curs_w += 2
                    curs_h += 1
                    y_top -= 1
                    y_bottom += 1

            coords = [
                #  horz
                ((x_left, y_top), (x_left + cfg.col_w // 13, y_top)),
                ((x_right, y_top), (x_right - (cfg.col_w - cursor_offset_w) // 13, y_top)),
                ((x_left, y_bottom), (x_left + cfg.col_w // 13, y_bottom)),
                ((x_right, y_bottom), (x_right - (cfg.col_w - cursor_offset_w) // 13, y_bottom)),

                #  vert
                ((x_left, y_top), (x_left, y_top + cfg.row_h // 4)),
                ((x_right, y_top), (x_right, y_top + cfg.row_h // 4)),
                ((x_left, y_bottom), (x_left, y_bottom - cfg.row_h // 4)),
                ((x_right, y_bottom + 1), (x_right, y_bottom - cfg.row_h // 4))
            ]

            for coord in coords:
                self.renderer.add_line(color, coord[0], coord[1], 2)
        return

    def render_info_pane(self):
        selected_tracks = self.get_selected_tracks()
        for index in range(self.sequencer.track_count):
            if self.sequencer.cursor_pattern is not None:
                track = self.sequencer.cursor_pattern.tracks[index]
            else:
                track = None

            if index in selected_tracks and self.sequencer.cursor_pattern is not None:
                track_bg = cfg.CURSOR_COLOR if self.page == 2 else cfg.CURSOR_COLOR_ALT
            else:
                track_bg = (255, 255, 255)

            if track is not None and not track.is_master:
                if not track.is_muted:
                    sel_r, sel_g, sel_b = track_bg
                    ticks_since_last_note = self.sequencer.midi_handler.last_notes_played[track.channel][1]
                    if ticks_since_last_note is not None:
                        v = min(255, ticks_since_last_note * 24)
                        sel_r = min(0 + v, track_bg[0])
                        sel_b = min(0 + v, track_bg[2])

                    track_bg = (sel_r, sel_g, sel_b)
                else:
                    if index in selected_tracks and self.sequencer.cursor_pattern is not None:
                        track_bg = (200, 100, 100)
                    else:
                        track_bg = (150, 50, 50)

            # track bg
            self.renderer.add_rect(track_bg, cfg.start_x - 34 + cfg.midi_label_offset + index * cfg.col_w,
                                   cfg.start_y + 35, cfg.col_w - 4, 24)

            # track box outline
            self.renderer.add_rect(cfg.BG_DARKER, cfg.start_x - 34 + cfg.midi_label_offset + index * cfg.col_w,
                                   cfg.start_y + 35, cfg.col_w - 4, 24, 4)

            # Calculate the width of the text to center it correctly
            display_txt = cfg.track_names[index]
            start_x = 9 + cfg.start_x + cfg.midi_label_offset + index * cfg.col_w

            text_width = self.renderer.add_text("track_display_font", (0, 0, 0), display_txt, 0, 0, False, True)
            self.renderer.add_text("track_display_font", (0, 0, 0), display_txt,
                                   start_x - text_width // 2, cfg.start_y + 38, False)

            if track is not None:
                track_len, track_lpb = str(track.length), str(track.lpb)
            else:
                track_len, track_lpb = 'n/a', 'n/a'
            for i, elem in enumerate(["LEN:" + track_len, "LPB:" + track_lpb]):
                text_width = self.renderer.add_text("tracker_info_font", (0, 0, 0), elem, 0, 0, False, True)
                self.renderer.add_text("tracker_info_font", track_bg, elem,
                                       start_x - text_width // 2, cfg.start_y + 63 + (i * 14))

        # draw play icon if playing
        polygon_pts = ((cfg.play_x, cfg.play_y),
                       (cfg.play_x + 30, cfg.play_y + 20),
                       (cfg.play_x, cfg.play_y + 40))

        if self.sequencer.is_playing:
            color = cfg.PLAYHEAD_COLOR if 48 > self.sequencer.ticks % 96 else cfg.PLAYHEAD_COLOR_ALT
            self.renderer.add_polygon(color, polygon_pts)
        else:
            self.renderer.add_polygon(cfg.BG_SHADOW, polygon_pts)

        if self.sequencer.cursor_pattern is not None:
            info_text_items = [f"BPM: {self.sequencer.cursor_pattern.bpm}",
                               f"OCT: {self.octave_mod + 3}"]
        else:
            info_text_items = [f"BPM: n/a",
                               f"OCT: {self.octave_mod + 3}"]

        y, g, r = 10, 255, 150
        for itm in info_text_items:
            self.renderer.add_text("tracker_info_font", (r, g, 255), itm, 5, y, False)

            y, g, r = y + 16, g - 30, r + 30

        midi_out = f"MIDI Out: {self.sequencer.midi_handler.midi_name}"
        color = cfg.PLAYHEAD_COLOR if self.sequencer.is_playing else (255, 255, 255)
        self.renderer.add_text("tracker_MIDI_out_font", color, midi_out,
                               cfg.start_x - 32 + cfg.midi_label_offset, 2, False)
