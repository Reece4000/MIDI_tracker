import pygame
import pygame.midi
from sequencer_components import *
from gui_elements import *
import constants as cfg
import csv
import pickle
from constants import *
import os


class Tracker:
    """
    Functions to add:
    - Fade down: with a selected range, fade down the vel of the notes in each track
    - Fade up: with a selected range, fade up the vel of the notes in each track
    - Fill: with a selected range, fill the notes in each track, harmonic or percussive
    - Add notes: allow users to add more than one note or cc to a given step:
        -    this will require a new data structure to hold multiple notes per step
        -    on the tracker, will display as the root note with an asterisk

    - Add keyboard shortcut to increase/decrease note/octave of selection

    - CTRL and up/ ctrl down should go up one or down one in the phrase sequencer - if no next pattern,
    should create a new one
    """

    def __init__(self, screen, track_count, length, midi_out, midi_output_name, midi_ix):
        self.screen = screen
        self.win_height = pygame.display.get_surface().get_height()
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

        self.midi_out = midi_out
        self.midi_output_name = midi_output_name
        self.midi_ix = midi_ix

        self.input_font = pygame.font.SysFont('Consolas', 12)

        self.clipboard = []
        self.page = 2  # 0 = song, 1 = phrase, 2 = pattern
        self.render_queue = RenderQueue()

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
                if self.midi_out is not None and self.sequencer.last_note_played[channel] is not None:
                    self.midi_out.note_off(self.sequencer.last_note_played[channel], 0, channel=channel)
                self.sequencer.last_note_played[channel] = None
                self.sequencer.steps_since_last_note[channel] = None

    @staticmethod
    def note_to_midi(note):
        # Mapping note names to MIDI note numbers
        if note == 'OFF':
            return -1
        elif note is not None:
            note_name = note[:-1]  # Extract note name
            if note_name not in cfg.note_base_names:
                return None
            octave = int(note[-1])  # Extract octave number
            note_index = cfg.note_base_names.index(note_name)
            return 12 * (octave + 1) + note_index

    def play_notes(self):
        if self.midi_out is None:
            return
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

            note_number = self.note_to_midi(step.note.strip())
            if self.sequencer.last_note_played[channel] is not None:
                self.midi_out.note_off(note=self.sequencer.last_note_played[channel],
                                       channel=channel)
            if note_number != -1:
                vel = cfg.midi_scaling[int(step.vel)]
                self.sequencer.last_note_played[channel] = note_number
                self.sequencer.steps_since_last_note[channel] = 0
                self.midi_out.note_on(note=note_number,
                                      velocity=vel,
                                      channel=channel)
            else:
                self.sequencer.last_note_played[channel] = None
                self.sequencer.steps_since_last_note[channel] = None

    def preview_note(self, note):
        # get current track
        if self.midi_out is None:
            return
        if not self.sequencer.is_playing:
            channel = self.cursor_x
            if self.sequencer.last_note_played[channel] is not None:
                self.midi_out.note_off(note=self.sequencer.last_note_played[channel],
                                       channel=channel)  # Stop the last note
            if note != 'OFF':
                note_number = self.note_to_midi(note)
                self.midi_out.note_on(note=note_number,
                                      velocity=cfg.midi_scaling[self.sequencer.last_vel],
                                      channel=channel)
                self.sequencer.last_note_played[channel] = note_number

    def save_song(self):
        self.sequencer.is_playing = False
        font = pygame.font.SysFont('Consolas', 14, bold=True)
        userinput = UserInput(prompt="Please enter a save name, then press Enter")
        userinput.get_text(self.screen, font, cfg.BG_TASKPANE)
        save_name = userinput.inputted_text

        if save_name is None:
            return

        for pattern in self.sequencer.patterns.items():
            print(pattern.num, pattern.length, pattern.bpm, pattern.lpb)

        if not save_name.endswith(".pkl"):
            save_name += ".pkl"

        try:
            with open(save_name, 'wb') as file:
                pickle.dump(self.sequencer, file)
            print("Project saved.")
            return True
        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    def load_song(self):
        font = pygame.font.SysFont('Consolas', 14, bold=True)
        userinput = UserInput(prompt="Please enter a save name, then press Enter")
        userinput.get_text(self.screen, font, cfg.BG_TASKPANE)
        load_name = userinput.inputted_text

        if load_name is None:
            return

        if not load_name.endswith(".pkl"):
            load_name += ".pkl"

        try:
            with open(load_name, 'rb') as file:
                self.sequencer = pickle.load(file)
                self.phrase_cursor = 0
                self.song_cursor = 0
            print("Project loaded successfully.")
            return True
        except FileNotFoundError:
            print("Error: File does not exist.")
            return False
        except Exception as e:
            print(f"Error loading project: {e}")
            return False

    def new_project(self):
        font = pygame.font.SysFont('Consolas', 14, bold=True)
        userinput = UserInput(prompt="Do you want to save the current project first? Press Enter to save, Esc to continue without saving.")
        userinput.get_text(self.screen, font, cfg.BG_TASKPANE)
        response = userinput.inputted_text
        if response == "":
            self.save_song()

        self.sequencer = Sequencer(64, 1024, 8)

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
                track = self.sequencer.cursor_pattern.tracks[self.cursor_x]
                while track.steps[self.cursor_y].note is None:
                    if self.cursor_y == 0:
                        break
                    delta_y -= 1
                    self.cursor_y -= 1
        elif opt == 'down':
            if self.cursor_y < self.sequencer.cursor_pattern.length - 1:
                self.cursor_y += 1
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
            print(
                f"Duplication issue: {self.cursor_y}, {self.cursor_y_span}, {self.sequencer.cursor_pattern.length}, {h}")

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

        curr_length, min_length, max_length = self.sequencer.patterns[cursor_pattern_num].length, 1, 128
        new_length = curr_length + increment
        if new_length < min_length:
            new_length = min_length
        elif new_length > max_length:
            new_length = max_length

        self.sequencer.patterns[cursor_pattern_num].length = new_length
        if new_length > len(self.sequencer.patterns[cursor_pattern_num].tracks[0].steps):
            for track in self.sequencer.patterns[cursor_pattern_num].tracks:
                track.steps.extend([Step() for _ in range(self.sequencer.patterns[cursor_pattern_num].length -
                                                          len(track.steps))])
        self.sequencer.update_sequencer_params()
        self.sequencer.last_length = new_length

    def adjust_lpb(self, increment):
        cursor_phrase_num = self.sequencer.song_steps[self.song_cursor]
        cursor_pattern_num = self.sequencer.phrases[cursor_phrase_num][self.phrase_cursor]

        curr_lpb, min_lpb, max_lpb = self.sequencer.patterns[cursor_pattern_num].lpb, 2, 32
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

        curr_bpm, min_bpm, max_bpm = self.sequencer.patterns[cursor_pattern_num].bpm, 15, 9999
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
        # Compute offset_y to center the current step
        if self.sequencer.cursor_pattern is None:
            return None
        for track_index, track in enumerate(self.sequencer.cursor_pattern.tracks):
            for step_index, step in enumerate(track.steps):

                row_y = (step_index * cfg.row_h) + (self.center_y - (self.cursor_y * cfg.row_h))

                # don't draw if outside of window
                if 75 < row_y < self.win_height:
                    if step_index > self.sequencer.cursor_pattern.length - 1:
                        break

                    line_bg_color = None
                    if track_index == 0:
                        if not step_index % self.sequencer.cursor_pattern.lpb:  # beats
                            line_bg_color = cfg.LINE_16_HL_BG
                        elif not step_index % round((self.sequencer.cursor_pattern.lpb / 2), 0):  # eighth notes
                            line_bg_color = cfg.LINE_8_HL_BG
                        elif not step_index % round((self.sequencer.cursor_pattern.lpb / 4), 0):  # sixteenth notes
                            line_bg_color = cfg.LINE_4_HL_BG

                            # line bg
                        if line_bg_color is not None:
                            self.render_queue.add_line(line_bg_color, (cfg.start_x, row_y + 9),
                                                       (cfg.pattern_line_len, row_y + 9), cfg.row_h)

                        # row label
                        self.render_queue.add_text("tracker_row_label_font", (255, 255, 255), f"{step_index:02}",
                                                   cfg.start_x + 3, row_y + 7)

                    # step_text
                    x_offset, step_x, f = 38, cfg.start_x + (track_index * cfg.col_w), "tracker_pattern_font"
                    for component, color in step.components():
                        self.render_queue.add_text(f, color, component, step_x + x_offset, row_y + 5)
                        x_offset += len(component) * (cfg.col_w // 9)
        return

    def render_queue_add_timeline(self):
        for step_index in range(self.sequencer.timeline_length):

            # SONG TRACK
            song_playhead_pos = self.sequencer.song_playhead_pos
            if song_playhead_pos < step_index:
                row_y = self.center_y + (step_index - self.song_cursor) * cfg.row_h
            else:
                row_y = self.center_y - (self.song_cursor - step_index) * cfg.row_h

            if 75 < row_y < self.win_height:  # don't want to draw if outside of window
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
                    step = '--'

                self.render_queue.add_text("tracker_song_font", song_step_color,
                                           f"{step:0>2}", 18, row_y + 6)

            # PHRASE TRACK
            phrase_playhead_pos = self.sequencer.phrase_playhead_pos
            if phrase_playhead_pos < step_index:
                row_y = self.center_y + (step_index - self.phrase_cursor) * cfg.row_h
            else:
                row_y = self.center_y - (self.phrase_cursor - step_index) * cfg.row_h

            if 75 < row_y < self.win_height:  # don't draw if outside of window
                diff = row_y - self.center_y
                diff = diff * -1 if diff < 0 else diff // 1.8
                r, g, b = max(245 - diff, 20), max(255 - diff, 32), max(255 - diff, 32)

                phrase_step_num = self.sequencer.cursor_phrase[step_index]
                on_phrase = self.sequencer.song_playhead_pos == self.song_cursor

                if step_index == self.sequencer.phrase_playhead_pos and self.sequencer.is_playing and on_phrase:
                    phrase_step_color = cfg.PLAYHEAD_COLOR
                elif self.sequencer.cursor_phrase[step_index] is not None:
                    phrase_step_color = (r, g, b)
                else:
                    phrase_step_num, phrase_step_color = '---', (r, g, b)

                if phrase_step_num is not None:
                    self.render_queue.add_text("tracker_phrase_font", phrase_step_color,
                                               f"{phrase_step_num:0>3}", 55, row_y + 8)

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
            self.render_queue.add_rect(cfg.PLAYHEAD_COLOR, cfg.start_x - 2, playhead_pos_y, 26, cfg.row_h + 1, 2)
            self.render_queue.add_line(cfg.PLAYHEAD_COLOR, (cfg.start_x, playhead_pos_y),
                                       (cfg.pattern_line_len, playhead_pos_y), 2)

    def render_queue_add_cursors(self, x, y, w, h):
        cursor_offset_x, cursor_offset_w = cfg.start_x - 10, 0
        # song edit cursor
        self.render_queue.add_rect(cfg.CURSOR_COLOR if self.page == 0 else cfg.CURSOR_COLOR_ALT,
                                   10, self.center_y, 34, 1 + cfg.row_h, 2)
        # phrase edit cursor
        self.render_queue.add_rect(cfg.CURSOR_COLOR if self.page == 1 else cfg.CURSOR_COLOR_ALT,
                                   50, self.center_y, 34, 1 + cfg.row_h, 2)

        if self.sequencer.cursor_pattern is not None:
            # cell edit cursor
            self.render_queue.add_rect(cfg.CURSOR_COLOR if self.page == 2 else cfg.CURSOR_COLOR_ALT,
                                       x + cursor_offset_x, y, w - cursor_offset_w, h + 1, 2)
            # row edit cursor
            self.render_queue.add_rect(cfg.CURSOR_COLOR if self.page == 2 else cfg.CURSOR_COLOR_ALT,
                                       cfg.start_x - 2, y, 26, 1 + cfg.row_h + (h - cfg.row_h), 2)

        return cursor_offset_x, cursor_offset_w

    def render_queue_add_info_pane(self):
        for channel in range(self.sequencer.track_count):
            if self.sequencer.steps_since_last_note[channel] is not None:
                v = min(255, self.sequencer.steps_since_last_note[channel] * 36)
                label_font_color = (v, 255, v)
            else:
                label_font_color = (255, 255, 255)

            # MIDI labels
            self.render_queue.add_text("big_display_font", label_font_color, f"TRACK {channel + 1}",
                                       cfg.start_x - 12 + cfg.midi_label_offset + channel * cfg.col_w,
                                       cfg.start_y + 46, antialias=True)

        # draw play icon if playing
        polygon_pts = ((cfg.play_x, cfg.play_y),
                       (cfg.play_x + 30, cfg.play_y + 20),
                       (cfg.play_x, cfg.play_y + 40))

        if self.sequencer.is_playing:
            if self.sequencer.pattern_playhead_pos % self.sequencer.playing_pattern.lpb > 8:
                self.render_queue.add_triangle(cfg.PLAYHEAD_COLOR, polygon_pts)
            else:
                self.render_queue.add_triangle(cfg.PLAYHEAD_COLOR_ALT, polygon_pts)
        else:
            self.render_queue.add_triangle(cfg.BG_SHADOW, polygon_pts)

        if self.sequencer.cursor_pattern is not None:
            info_text_items = [f"BPM: {self.sequencer.cursor_pattern.bpm}",
                               f"LPB: {self.sequencer.cursor_pattern.lpb}",
                               f"Length: {self.sequencer.cursor_pattern.length}",
                               f"Octave: {self.octave_mod + 3}",
                               f"MIDI Out: {self.midi_output_name} ({self.midi_ix})"]
        else:
            info_text_items = [f"BPM: n/a",
                               f"LPB: n/a",
                               f"Length: n/a",
                               f"Octave: {self.octave_mod + 3}",
                               f"MIDI Out: {self.midi_output_name} ({self.midi_ix})"]

        info_text = "  -  ".join(info_text_items)
        self.render_queue.add_text("medium_font", (255, 255, 255), info_text,
                                   cfg.start_x - 12 + cfg.midi_label_offset, 10, antialias=True)

    def update_render_queue(self):
        self.render_queue.clear()
        # draw pattern grid
        self.render_queue_add_pattern()

        # timeline background
        self.render_queue.add_rect(cfg.BG_DARKER, 0, 0, 95, 2000)

        # timeline
        self.render_queue_add_timeline()

        # playhead
        self.render_queue_add_playhead()

        # row/cell cursors
        x, y, w, h = self.get_selection_coords(for_display=True)
        cursor_offset_x, cursor_offset_w = self.render_queue_add_cursors(x, y, w, h)

        # taskbar_pane (needs to be after cursor so that it's on top)
        self.render_queue.add_rect(cfg.BG_TASKPANE, 0, 0, 2000, 75)

        # track selection cursor
        if self.sequencer.cursor_pattern is not None:
            self.render_queue.add_rect(cfg.CURSOR_COLOR if self.page == 2 else cfg.CURSOR_COLOR_ALT,
                                       x + cursor_offset_x, 41,
                                       cfg.col_w + (w - cfg.col_w) - cursor_offset_w, 24, 2)

        self.render_queue_add_info_pane()

