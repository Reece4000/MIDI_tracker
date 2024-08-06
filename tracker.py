import pygame
from sequencer_components import Sequencer, MidiHandler
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

    def add_text(self, font, color, text, x, y, antialias=False):
        key = (font, color, text, antialias, x, y)

        if key not in self.text_cache:
            rendered_text = self.fonts[font].render(text, antialias, color)
            self.text_cache[key] = rendered_text
        else:
            rendered_text = self.text_cache[key]

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

        # positional indices for detecting whether cursor['x on sequencer tracks
        self.phrase_track_index = track_count
        self.song_track_index = track_count + 1

        self.sequencer = Sequencer(timeline_length=length,
                                   num_patterns=1024,
                                   track_count=track_count)

        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((cfg.WIDTH, cfg.HEIGHT))
        pygame.display.set_caption("Tracker")
        pygame.key.set_repeat(180, 40)
        self.midi_handler = MidiHandler(num_channels=track_count)
        self.renderer = Renderer(self.screen)
        self.keyhandler = KeyHandler(tracker=self)

        self.midi_output_name = self.midi_handler.initialise_midi()

        self.clipboard = []
        self.page = 2  # 0 = song, 1 = phrase, 2 = pattern
        self.cycles = 0
        self.render_cycle = 0
        self.io_return = None

    def check_for_tick(self, last_update_time):
        current_time = perf_counter()
        if self.sequencer.is_playing:
            self.sequencer.time_since_last_pulse += (current_time - last_update_time)
            self.sequencer.time_since_last_step += (current_time - last_update_time)
            if self.sequencer.time_since_last_pulse >= self.sequencer.pulse_time:
                self.midi_handler.send_midi_clock()
                self.sequencer.time_since_last_pulse -= self.sequencer.pulse_time
            if self.sequencer.time_since_last_step >= self.sequencer.step_time:
                self.tick()
                self.sequencer.time_since_last_step -= self.sequencer.step_time

        return current_time

    def running_loop(self):
        last_update_time = perf_counter()
        running = True

        while running:
            ret = self.keyhandler.check_for_events()
            if ret == "Exit":
                running = False

            self.renderer.fill(cfg.BG_COLOR)  # bg
            last_update_time = self.check_for_tick(last_update_time)
            self.render_queue_add_pattern()  # draw pattern grid
            last_update_time = self.check_for_tick(last_update_time)
            self.renderer.add_rect(cfg.BG_DARKER, 0, 0, 95, 2000)  # timeline background
            self.render_queue_add_timeline()  # draw timeline
            last_update_time = self.check_for_tick(last_update_time)
            self.render_queue_add_playhead()  # draw playhead
            last_update_time = self.check_for_tick(last_update_time)
            x, y, w, h = self.get_selection_coords(for_display=True)
            self.render_queue_add_cursors(x, y, w, h)  # draw row/cell cursors
            last_update_time = self.check_for_tick(last_update_time)
            self.renderer.add_rect(cfg.BG_TASKPANE, 0, 0, 2000, 75)
            self.render_queue_add_info_pane()  # draw taskbar_pane
            last_update_time = self.check_for_tick(last_update_time)

            self.cycles += 1
            pygame.display.update()

        print("Cleaning up and exiting...")
        self.midi_handler.midi_out.close_port()
        pygame.quit()

    def reset(self):
        self.sequencer.reset()
        self.cursor_x, self.cursor_y = 0, 0
        self.cursor_x_span, self.cursor_y_span = 0, 0
        self.song_cursor, self.song_cursor_span = 0, 0
        self.phrase_cursor, self.phrase_cursor_span = 0, 0
        self.page = 2

    def play(self, init=False):
        self.sequencer.is_playing = not self.sequencer.is_playing  # Toggle play/pause
        if self.sequencer.is_playing:
            if self.sequencer.song_playhead_pos != self.song_cursor:
                self.sequencer.song_playhead_pos = self.song_cursor
            self.sequencer.phrase_playhead_pos = self.phrase_cursor

            self.sequencer.playing_pattern = self.sequencer.cursor_pattern
            if self.sequencer.playing_pattern is None:
                self.sequencer.is_playing = False
                return
            self.sequencer.pattern_playhead_pos = 0
            self.sequencer.time_since_last_step = 0
            if self.sequencer.follow_playhead:
                self.cursor_y_span = 0

            if init:
                self.play_notes()

        else:
            for channel in range(self.sequencer.track_count):
                if self.sequencer.last_note_played[channel] is not None:
                    self.midi_handler.note_off(channel, self.sequencer.last_note_played[channel])
                self.sequencer.last_note_played[channel] = None
                self.sequencer.steps_since_last_note[channel] = None

    def play_notes(self):
        if self.sequencer.follow_playhead:
            self.phrase_cursor = self.sequencer.phrase_playhead_pos
            self.song_cursor = self.sequencer.song_playhead_pos

        playing_phrase_num = self.sequencer.song_steps[self.sequencer.song_playhead_pos]
        playing_pattern_num = self.sequencer.phrases[playing_phrase_num][self.sequencer.phrase_playhead_pos]
        playing_pattern = self.sequencer.patterns[playing_pattern_num]

        for channel, track in enumerate(playing_pattern.tracks):
            step = track.steps[self.sequencer.pattern_playhead_pos]
            if step.note is None:
                if self.sequencer.steps_since_last_note[channel] is not None:
                    self.sequencer.steps_since_last_note[channel] += 1
                continue

            if self.sequencer.last_note_played[channel] is not None:
                self.midi_handler.note_off(channel, self.sequencer.last_note_played[channel])
            if step.note != 'OFF':
                self.sequencer.last_note_played[channel] = step.note
                self.sequencer.steps_since_last_note[channel] = 0
                self.midi_handler.note_on(channel, step.note.strip(), int(step.vel))
            else:
                self.sequencer.last_note_played[channel] = None
                self.sequencer.steps_since_last_note[channel] = None

    def preview_note(self, note):
        # get current track
        if not self.sequencer.is_playing:
            channel = self.cursor_x
            if self.sequencer.last_note_played[channel] is not None:
                self.midi_handler.note_off(channel, self.sequencer.last_note_played[channel])
            if note != 'OFF':
                self.midi_handler.note_on(channel, note, self.sequencer.last_vel)
                self.sequencer.last_note_played[channel] = note

    def save_song(self):
        self.midi_handler.all_notes_off()
        self.sequencer.is_playing = False
        save_name = self.renderer.user_input("Please enter a save name, then press Enter",
                                             "tracker_font", cfg.BG_TASKPANE)

        serialised_sequencer_data = self.sequencer.json_serialize()
        # save json dump to file
        if not save_name.startswith("save_files/"):
            save_name = "save_files/" + save_name
        if not save_name.endswith(".json"):
            save_name += ".json"

        with open(save_name, 'w') as file:
            json.dump(serialised_sequencer_data, file)

        print("Song saved successfully!")

    def load_song(self):
        self.midi_handler.all_notes_off()
        # check whether patterns is empty, if not ask user if they want to save
        load_name = self.renderer.user_input("Please enter the project name, then press Enter",
                                             "tracker_font", cfg.BG_TASKPANE)

        if not load_name:
            return

        if not load_name.startswith("save_files/"):
            load_name = "save_files/" + load_name
        if not load_name.endswith(".json"):
            load_name += ".json"
        self.sequencer.is_playing = False
        self.cursor_x, self.cursor_y = 0, 0
        self.cursor_x_span, self.cursor_y_span = 0, 0

        with open(load_name, 'r') as file:
            serialised_sequencer_data = json.load(file)
            self.sequencer.load_from_json(serialised_sequencer_data)

        self.page, self.cursor_x, self.cursor_y = 2, 0, 0
        self.cursor_x_span, self.cursor_y_span = 0, 0
        self.song_cursor, self.phrase_cursor = 0, 0
        print("Song loaded successfully!")

    def new_song(self):
        self.midi_handler.all_notes_off()

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
                    self.sequencer.set_current_pattern(self.sequencer.cursor_phrase[self.phrase_cursor])

        elif opt == 'up':
            if self.phrase_cursor - 1 >= 0:
                if self.sequencer.cursor_phrase[self.phrase_cursor - 1] is not None:
                    self.phrase_cursor -= 1
                    self.sequencer.set_current_pattern(self.sequencer.cursor_phrase[self.phrase_cursor])

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

    def tick(self):
        self.sequencer.update_pattern_playhead()
        playing_phrase_num = self.sequencer.song_steps[self.sequencer.song_playhead_pos]
        playing_pattern_num = self.sequencer.phrases[playing_phrase_num][self.sequencer.phrase_playhead_pos]
        if playing_pattern_num is not None:
            playing_pattern = self.sequencer.patterns[playing_pattern_num]
            self.sequencer.step_time = 60 / (playing_pattern.bpm * playing_pattern.lpb)
            self.play_notes()
        else:
            self.sequencer.is_playing = False

    # so we want to update the pattern step in the phrase track to the new pattern number
    # then we want to update the current pattern to the new pattern number

    def update_timeline_step(self, val):
        if self.page == 0:
            self.sequencer.update_song_step(self.song_cursor, val)
        elif self.page == 1:
            if self.sequencer.song_steps[self.song_cursor] is not None:
                self.sequencer.update_phrase_step(self.phrase_cursor, val)

    def add_note(self, note):
        if note != "OFF":
            octave = int(note[-1]) + self.octave_mod
            note = note[:-1] + str(octave)
        pos, vel = self.cursor_y, self.sequencer.last_vel
        self.sequencer.cursor_pattern.tracks[self.cursor_x].update_step(pos, note, vel, "00", "00")
        # debugging
        self.preview_note(note)

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
                self.sequencer.set_current_pattern(self.sequencer.cursor_phrase[self.phrase_cursor])
        elif self.page == 2:
            if self.cursor_x == 0 and x < 0:
                self.page = 1
            if x > 0:
                self.cursor_x = min(self.sequencer.track_count - 1, self.cursor_x + x)
            elif x < 0:
                self.cursor_x = max(0, self.cursor_x + x)
            if y > 0:
                self.cursor_y = min(self.sequencer.cursor_pattern.length - 1, self.cursor_y + y)
            elif y < 0:
                self.cursor_y = max(0, self.cursor_y + y)

            if expand_selection and not (self.sequencer.is_playing and self.sequencer.follow_playhead):
                self.cursor_x_span += self.cursor_x - prev_x
                self.cursor_y_span += self.cursor_y - prev_y

            if self.sequencer.is_playing and self.sequencer.follow_playhead:
                self.sequencer.pattern_playhead_pos = self.cursor_y
                self.play_notes()

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
            if self.cursor_y < self.sequencer.cursor_pattern.length - 1:
                self.cursor_y, delta_y = self.cursor_y + 1, 1
                track = self.sequencer.cursor_pattern.tracks[self.cursor_x]
                while track.steps[self.cursor_y].note is None:
                    if self.cursor_y == self.sequencer.cursor_pattern.length - 1:
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
                if y + row + (h + 1) < self.sequencer.cursor_pattern.length:
                    self.sequencer.cursor_pattern.tracks[x + track].update_step(y + row + (h + 1), note=step.note,
                                                                                vel=step.vel)
        # update cursor_y and y_span
        if self.cursor_y_span < 0:
            if not self.cursor_y + (h + 1) * 2 < self.sequencer.cursor_pattern.length:
                print("Cond 1.1", self.cursor_y, self.cursor_y_span, self.sequencer.cursor_pattern.length, h)
                if self.cursor_y + h + 1 < self.sequencer.cursor_pattern.length:
                    self.cursor_y += h + 1
                    self.cursor_y_span = -1 * (self.sequencer.cursor_pattern.length - 1 - self.cursor_y)
                else:
                    self.cursor_y = self.sequencer.cursor_pattern.length - 1
                    self.cursor_y_span = 0
            else:
                print("Cond 1.2", self.cursor_y, self.cursor_y_span, self.sequencer.cursor_pattern.length, h)
                self.cursor_y += h + 1

        elif self.cursor_y + h + 1 < self.sequencer.cursor_pattern.length:
            print("Cond 2", self.cursor_y, self.cursor_y_span, self.sequencer.cursor_pattern.length, h)
            self.cursor_y += h + 1

        elif self.cursor_y + h >= self.sequencer.cursor_pattern.length - 1:
            print("Cond 3", self.cursor_y, self.cursor_y_span, self.sequencer.cursor_pattern.length, h)
            self.cursor_y = self.sequencer.cursor_pattern.length - 1
            self.cursor_y_span = self.sequencer.cursor_pattern.length - 1 - self.cursor_y

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
                        self.preview_note(note)

    def delete_selection(self):
        if self.page == 2:
            x, y, w, h = self.get_selection_coords()
            for track in range(w + 1):
                for row in range(h + 1):
                    self.sequencer.cursor_pattern.tracks[x + track].clear_step(y + row)

    def adjust_length(self, increment):
        cursor_phrase_num = self.sequencer.song_steps[self.song_cursor]
        cursor_pattern_num = self.sequencer.phrases[cursor_phrase_num][self.phrase_cursor]

        if cursor_pattern_num is None:
            return

        curr_length, min_length, max_length = self.sequencer.patterns[cursor_pattern_num].length, 1, 128
        new_length = curr_length + increment
        if new_length < min_length:
            new_length = min_length
        elif new_length > max_length:
            new_length = max_length

        self.sequencer.patterns[cursor_pattern_num].length = new_length
        if new_length > len(self.sequencer.patterns[cursor_pattern_num].tracks[0].steps):
            for track in self.sequencer.patterns[cursor_pattern_num].tracks:
                track.extend_steps(new_length)

        self.sequencer.update_sequencer_params()
        self.sequencer.last_length = new_length

    def adjust_lpb(self, increment):
        cursor_phrase_num = self.sequencer.song_steps[self.song_cursor]
        cursor_pattern_num = self.sequencer.phrases[cursor_phrase_num][self.phrase_cursor]

        if cursor_pattern_num is None:
            return

        curr_lpb, min_lpb, max_lpb = self.sequencer.patterns[cursor_pattern_num].lpb, 1, 32
        new_lpb = curr_lpb + increment
        if new_lpb < min_lpb:
            new_lpb = min_lpb
        elif new_lpb > max_lpb:
            new_lpb = max_lpb

        self.sequencer.patterns[cursor_pattern_num].lpb = new_lpb
        self.sequencer.update_sequencer_params()
        self.sequencer.last_lpb = new_lpb

    def adjust_bpm(self, increment):
        cursor_phrase_num = self.sequencer.song_steps[self.song_cursor]
        cursor_pattern_num = self.sequencer.phrases[cursor_phrase_num][self.phrase_cursor]

        if cursor_pattern_num is None:
            return

        curr_bpm, min_bpm, max_bpm = self.sequencer.patterns[cursor_pattern_num].bpm, 15, 10000
        new_bpm = curr_bpm + increment
        if new_bpm < min_bpm:
            new_bpm = min_bpm
        elif new_bpm > max_bpm:
            new_bpm = max_bpm

        self.sequencer.patterns[cursor_pattern_num].bpm = new_bpm
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

    def render_queue_add_pattern(self):
        window_height = pygame.display.get_surface().get_height()
        # Compute offset_y to center the current step
        if self.sequencer.cursor_pattern is None:
            return None
        for track_index, track in enumerate(self.sequencer.cursor_pattern.tracks):
            for step_index, step in enumerate(track.steps):

                row_y = (step_index * cfg.row_h) + (self.center_y - (self.cursor_y * cfg.row_h))
                # don't draw if outside of window
                if step_index > self.sequencer.cursor_pattern.length - 1:
                    break

                if row_y < 70 or row_y > window_height:  # top of window
                    continue

                if track_index == 0:
                    if not step_index % self.sequencer.cursor_pattern.lpb:  # beats
                        line_bg_color = cfg.LINE_16_HL_BG
                    elif (step_index * 2) % self.sequencer.cursor_pattern.lpb < 2:  # eighth notes
                        line_bg_color = cfg.LINE_8_HL_BG
                    # elif not step_index % (self.sequencer.cursor_pattern.lpb // 4):  # sixteenth notes
                    #     line_bg_color = cfg.LINE_4_HL_BG
                    else:
                        line_bg_color = None

                    # line bg
                    if line_bg_color is not None:
                        self.renderer.add_line(line_bg_color, (cfg.start_x, row_y + 10),
                                               (cfg.pattern_line_len, row_y + 10), cfg.row_h - 1)

                    # row cursor
                    row_label_col = (255, 255, 255)
                    if step_index == self.cursor_y and self.sequencer.cursor_pattern is not None:
                        self.renderer.add_rect(cfg.CURSOR_COLOR, cfg.start_x, row_y + 1, 22, cfg.row_h - 1)
                        row_label_col = (0, 0, 0)

                    # row label
                    self.renderer.add_text("tracker_row_label_font", row_label_col, f"{step_index:02}",
                                             cfg.start_x + 3, row_y + 2)

                # step_text
                x_offset, step_x = 42, cfg.start_x + (track_index * cfg.col_w)
                i = 0
                f = "tracker_font"
                for component, color in step.components():
                    self.renderer.add_text(f, color, component, step_x + x_offset, row_y + 2)
                    x_offset += 3 + len(component) * (cfg.col_w // 11)
                    i += 1
        return

    def render_queue_add_timeline(self):
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

    def render_queue_add_playhead(self):
        playhead_pos_y = None
        if self.sequencer.follow_playhead and self.sequencer.is_playing:
            self.cursor_y = self.sequencer.pattern_playhead_pos
            playhead_pos_y = self.center_y
        else:
            if self.sequencer.cursor_pattern is not None:
                if self.sequencer.is_cursor_on_playing_pattern(self.song_cursor, self.phrase_cursor):
                    playhead_pos_y = ((self.sequencer.pattern_playhead_pos * cfg.row_h) +
                                      (self.center_y - (self.cursor_y * cfg.row_h)))

        if playhead_pos_y is not None:
            self.renderer.add_rect(cfg.PLAYHEAD_COLOR, cfg.start_x - 2, playhead_pos_y, 26, cfg.row_h + 1, 2)
            self.renderer.add_line(cfg.PLAYHEAD_COLOR, (cfg.start_x, playhead_pos_y),
                                     (cfg.pattern_line_len, playhead_pos_y), 2)

    def render_queue_add_cursors(self, x, y, w, h):
        cursor_offset_x, cursor_offset_w = cfg.start_x - 6, 10

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
            curs_h = h - 1
            x_right = x_left + w - cursor_offset_w
            y_top = y + 1
            y_bottom = y_top + curs_h - 2

            self.renderer.add_pane((255, 255, 200), x_left, y_top, curs_w + 2, curs_h)

            if self.page == 2:
                chk = self.sequencer.pattern_playhead_pos % self.sequencer.playing_pattern.lpb
                if chk > 8:
                    x_left -= 2
                    x_right += 2
                    curs_w += 4
                    curs_h += 2
                    y_top -= 2
                    y_bottom += 2
                elif chk > 4:
                    x_left -= 1
                    x_right += 1
                    curs_w += 2
                    curs_h += 1
                    y_top -= 1
                    y_bottom += 1

            coords = [
                #  horz
                ((x_left, y_top), (x_left + curs_w // 8, y_top)),
                ((x_right, y_top), (x_right - curs_w // 8, y_top)),
                ((x_left, y_bottom), (x_left + curs_w // 8, y_bottom)),
                ((x_right, y_bottom), (x_right - curs_w // 8, y_bottom)),

                #  vert
                ((x_left, y_top), (x_left, y_top + curs_h // 3)),
                ((x_right, y_top), (x_right, y_top + curs_h // 3)),
                ((x_left, y_bottom), (x_left, y_bottom - curs_h // 3)),
                ((x_right, y_bottom), (x_right, y_bottom - curs_h // 3))
            ]

            for coord in coords:
                self.renderer.add_line(color, coord[0], coord[1], 2)
        return

    def render_queue_add_info_pane(self):
        track_colors = [
            (255, 0, 0),  # Red
            (255, 165, 0),  # Orange
            (255, 255, 0),  # Yellow
            (0, 255, 0),  # Green
            (120, 120, 255),  # Blue
            (0, 255, 255),  # Cyan
            (200, 50, 200),  # Purple
            (255, 192, 203)  # Pink
        ]

        for channel in range(self.sequencer.track_count):
            r, g, b = track_colors[channel]

            if channel == self.cursor_x and self.sequencer.cursor_pattern is not None:
                track_bg = cfg.CURSOR_COLOR if self.page == 2 else cfg.CURSOR_COLOR_ALT
            else:
                track_bg = [255, 255, 255]

            sel_r, sel_g, sel_b = track_bg
            if self.sequencer.steps_since_last_note[channel] is not None:
                v = min(255, self.sequencer.steps_since_last_note[channel] * 36)
                # Calculate the inverted colour
                ir = 255 - r
                ig = 255 - g
                ib = 255 - b
                # Blend back to the original colour based on v
                r = ir + (r - ir) * (v / 255)
                g = ig + (g - ig) * (v / 255)
                b = ib + (b - ib) * (v / 255)

                sel_r = min(0 + v, track_bg[0])
                sel_b = min(0 + v, track_bg[2])

            track_bg = (sel_r, sel_g, sel_b)
            track_color = (int(r), int(g), int(b))

            self.renderer.add_rect(track_bg, cfg.start_x - 34 + cfg.midi_label_offset + channel * cfg.col_w,
                                   cfg.start_y + 45, cfg.col_w - 4, 24)

            self.renderer.add_rect(cfg.BG_DARKER, cfg.start_x - 34 + cfg.midi_label_offset + channel * cfg.col_w,
                                   cfg.start_y + 45, cfg.col_w - 4, 24, 4)

            self.renderer.add_rect(track_color,
                                   cfg.start_x - 14 + cfg.midi_label_offset + channel * cfg.col_w,
                                   cfg.start_y + 71, cfg.col_w - 44, 2, 5)

            # MIDI labels
            self.renderer.add_text("track_display_font", (0, 0, 0), f"TRACK {channel + 1}",
                                   cfg.start_x - 10 + cfg.midi_label_offset + channel * cfg.col_w,
                                   cfg.start_y + 48, False)

        # draw play icon if playing
        polygon_pts = ((cfg.play_x, cfg.play_y),
                       (cfg.play_x + 30, cfg.play_y + 20),
                       (cfg.play_x, cfg.play_y + 40))

        if self.sequencer.is_playing:
            if self.sequencer.pattern_playhead_pos % self.sequencer.playing_pattern.lpb > 8:
                self.renderer.add_polygon(cfg.PLAYHEAD_COLOR, polygon_pts)
            else:
                self.renderer.add_polygon(cfg.PLAYHEAD_COLOR_ALT, polygon_pts)
        else:
            self.renderer.add_polygon(cfg.BG_SHADOW, polygon_pts)

        if self.sequencer.cursor_pattern is not None:
            info_text_items = [f"BPM: {self.sequencer.cursor_pattern.bpm}",
                               f"LPB: {self.sequencer.cursor_pattern.lpb}",
                               f"LEN: {self.sequencer.cursor_pattern.length}",
                               f"OCT: {self.octave_mod + 3}"]
        else:
            info_text_items = [f"BPM: n/a",
                               f"LPB: n/a",
                               f"LEN: n/a",
                               f"OCT: {self.octave_mod + 3}"]

        y, g, r = 10, 255, 150
        for itm in info_text_items:
            self.renderer.add_text("tracker_info_font", (r, g, 255), itm, 5, y, False)

            y, g, r = y + 16, g - 30, r + 30

        midi_out = f"MIDI Out: {self.midi_output_name}"
        color = cfg.PLAYHEAD_COLOR if self.sequencer.is_playing else (255, 255, 255)
        self.renderer.add_text("tracker_MIDI_out_font", color, midi_out,
                                 cfg.start_x - 32 + cfg.midi_label_offset, 10, False)
