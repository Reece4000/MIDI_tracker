import numpy as np
import pygame
import asyncio
from threading import Lock
from time import perf_counter

from config.pages import *
from config import constants, display, events
from src.utils import timing_decorator, calculate_timeline_increment

from src.input_handler import InputHandler
from src.midi_handler import MidiHandler
from src.clock import Clock
from src.renderer import Renderer
from src.pattern import Pattern
from src.ui_components.info_pane import InfoPane
from src.ui_components.pattern_view import PatternEditor
from src.ui_components.master_view import MasterTrack
from src.ui_components.editor_window import EditorWindow
from src.ui_components.timeline_tracks import TimelinePage
from src.ui_components.gui_elements import RowNumberCell


class Tracker:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.event_bus.subscribe(events.QUIT, self.quit)
        self.renderer = Renderer(self)
        self.renderer.initialise()
        self.input_handler = InputHandler(self)
        self.midi_handler = MidiHandler()

        self._tick_mutex = Lock()
        self.ticks = 0
        self.is_playing = False
        self.clock = Clock(bpm=constants.start_bpm, callback=self.tick)

        self.track_count = constants.track_count
        self.timeline_length = constants.timeline_length

        self.song = [0] + [None for _ in range(self.timeline_length - 1)]

        self.phrase_pool = {None: [None for _ in range(self.timeline_length)],
                            0: [0] + [None for _ in range(self.timeline_length - 1)]}
        self.pattern_pool = {None: None,
                             0: Pattern(num=0, length=constants.start_len, lpb=constants.start_lpb,
                                        bpm=constants.start_bpm, swing=constants.start_swing, tracker=self)}

        self.phrase_playhead = 0
        self.song_playhead = 0

        self.follow_playhead = False

        self.mouse_x = 0
        self.mouse_y = 0

        self.octave_mod = 2
        # self.channel_ccs = [[i for i in range(1, 17)] for _ in range(16)]
        self.channel_ccs = [[1, 3, 9, 14, 15, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30] for _ in range(16)]

        self.last_note = constants.start_note
        self.last_vel = constants.start_vel
        self.last_bpm = constants.start_bpm
        self.last_lpb = constants.start_lpb
        self.last_length = constants.start_len
        self.last_swing = constants.start_swing
        self.last_cc = constants.start_cc
        self.last_cc_val = constants.start_cc_val

        self.page = PATTERN
        self.pages = {}

        self.page_border = None
        self.is_playing = False
        self.running = False

        row_number_cells = [RowNumberCell(y) for y in range(display.visible_rows)]
        self.info_pane = InfoPane(self)

        self.pages[TIMELINE] = TimelinePage(self)
        self.pages[MASTER] = MasterTrack(self, row_number_cells)
        self.pages[PATTERN] = PatternEditor(self, row_number_cells)
        self.pages[EDITOR] = EditorWindow(self)

        self.initialise()

    def initialise(self):
        # some ui components need to share state vars
        self.pages[MASTER].pattern_view = self.pages[PATTERN]
        self.pages[PATTERN].master_track_view = self.pages[MASTER]

        self.pages[TIMELINE].initialise_view()
        self.pages[TIMELINE].update_view()

        # initialise the page borders by turning on and off. Jank?
        for page in {TIMELINE, MASTER}:
            self.pages[page].toggle_active()
            self.pages[page].toggle_active()

        self.page_switch(None, None, PATTERN)

    @timing_decorator
    def update_view_states(self):
        self.info_pane.update_view()
        for _, page in self.pages.items():
            if page is not None:
                page.update_view()
        self.renderer.process_queue()
        self.renderer.update_screen()

    def handle_events_non_async(self):
        input_return = self.input_handler.check_for_events(current_time=perf_counter())
        if input_return == "Exit":
            self.running = False

    def running_loop_non_async(self):
        try:
            self.running = True
            render_interval = 1 / display.FPS
            last_render_time = perf_counter()
            while self.running:
                self.handle_events_non_async()
                curr_time = perf_counter()
                elapsed = curr_time - last_render_time
                if elapsed >= render_interval:
                    self.update_view_states()
                    last_render_time = curr_time
                else:
                    # use pygame wait instead of time.sleep to avoid blocking the event loop
                    pygame.time.wait(int((render_interval - elapsed) * 1000))
        finally:
            self.quit(is_async=0)

    async def handle_events(self):
        input_return = self.input_handler.check_for_events(current_time=perf_counter())
        if input_return == "Exit":
            self.running = False

    async def running_loop(self):
        self.running = True
        loop = asyncio.get_event_loop()
        while self.running:
            events_handled = loop.create_task(self.handle_events())
            await loop.run_in_executor(None, self.update_view_states)
            await events_handled
        self.quit(is_async=1)

    def quit(self, is_async):
        print("Cleaning up and exiting...")
        jitter = self.calculate_midi_jitter()
        with open("jitter.csv", "a") as f:
            f.write(f"{is_async},{jitter}\n")
        self.renderer.quit()
        self.clock.stop()
        self.midi_handler.all_notes_off()
        self.midi_handler.send_midi_stop()
        self.midi_handler.midi_out.close_port()

    def calculate_midi_jitter(self):
        pulse_timings = self.midi_handler.timings
        pulses = sorted(pulse_timings.keys())

        # Calculate the actual intervals between consecutive pulses
        actual_intervals = [
            pulse_timings[pulses[i + 1]] - pulse_timings[pulses[i]]
            for i in range(len(pulses) - 1)
        ]
        avg_interval = np.mean(actual_intervals)
        deviations = [interval - avg_interval for interval in actual_intervals]
        jitter = np.std(deviations)
        return jitter

    @timing_decorator
    def tick(self):
        with self._tick_mutex:
            self.midi_handler.send_midi_clock()
            if not self.is_playing:
                return
            self.update_track_playheads()
            self.ticks += 1

    def update_channel_ccs(self, channel, cc_index, new_cc):
        self.channel_ccs[channel][cc_index] = new_cc

    def get_song_cursor(self):
        return self.pages[TIMELINE].pages[TIMELINE_SONG].cursor_x

    def get_phrase_cursor(self):
        return self.pages[TIMELINE].pages[TIMELINE_PHRASE].cursor_x

    def get_selected_phrase(self):
        return self.add_phrase_if_not_exists(self.song[self.get_song_cursor()])

    def get_selected_pattern(self, num=False):
        selected_phrase = self.get_selected_phrase()
        phrase_cursor = self.get_phrase_cursor()
        selected_pattern = self.add_pattern_if_not_exists(selected_phrase[phrase_cursor])
        if selected_pattern is None:
            return None

        return selected_pattern.num if num else selected_pattern

    def get_playing_phrase(self):
        return self.phrase_pool[self.song[self.song_playhead]]

    def get_playing_pattern(self, num=False):
        playing_phrase_num = self.song[self.song_playhead]
        playing_pattern_num = self.phrase_pool[playing_phrase_num][self.phrase_playhead]
        return playing_pattern_num if num else self.pattern_pool[playing_pattern_num]

    def on_playing_pattern(self):
        return self.get_selected_pattern(num=True) == self.get_playing_pattern(num=True)

    def update_timeline_cursors(self):
        self.song_playhead = self.pages[TIMELINE].pages[TIMELINE_SONG].cursor_x
        self.phrase_playhead = self.pages[TIMELINE].pages[TIMELINE_PHRASE].cursor_x

    def update_pattern_parameters(self):
        playing_pattern = self.get_playing_pattern()
        if playing_pattern is not None:
            self.clock.set_bpm(playing_pattern.bpm)
            if self.follow_playhead:
                self.update_timeline_cursors()
        else:
            self.is_playing = False

    def stop_playback(self):
        self.is_playing = False
        self.ticks = 0
        self.midi_handler.all_notes_off()
        self.midi_handler.send_midi_stop()
        self.pages[TIMELINE].flag_state_change()

    def start_playback(self, from_pattern_start=True):
        print('\n########### Starting playback ###########\n')

        playing_pattern = self.get_playing_pattern()
        for i, track in enumerate(playing_pattern.midi_tracks):
            track.is_reversed = False

        self.song_playhead, self.phrase_playhead = self.get_song_cursor(), self.get_phrase_cursor()
        self.update_pattern_parameters()

        if from_pattern_start:
            self.midi_handler.send_midi_start()
            self.reset_track_playheads()

        self.is_playing = True
        self.pages[TIMELINE].flag_state_change()

    def toggle_playback(self):
        if self.is_playing:
            self.stop_playback()
        elif self.get_selected_pattern() is not None:
            self.start_playback()

    def set_playing_pattern_to_cursor(self):
        if self.get_selected_pattern() is not None and not self.on_playing_pattern():
            self.song_playhead = self.pages[TIMELINE].pages[TIMELINE_SONG].cursor_x
            self.phrase_playhead = self.pages[TIMELINE].pages[TIMELINE_PHRASE].cursor_x

    def process_master_components(self):
        playing_pattern = self.get_playing_pattern()
        master_step = playing_pattern.master_track.get_current_step()
        if not master_step.has_data():
            return

        mapping = constants.master_component_mapping
        for i in range(4):
            component_key = master_step.components[i]
            x_vals = master_step.component_x_vals[i]
            y_vals = master_step.component_y_vals[i]
            track_masks = master_step.component_track_masks[i]

            if component_key not in mapping:
                continue
            if mapping[component_key]["name"] == "REVERSE":
                playing_pattern.reverse_tracks(track_masks)

            elif mapping[component_key]["name"] == "MASTER SYNC":
                playing_pattern.synchronise_playheads(track_masks)

            elif mapping[component_key]["name"] == "SPEED UP":
                print("speed up, to be implemented")

            elif mapping[component_key]["name"] == "SLOW DOWN":
                print("slow down, to be implemented")

            elif mapping[component_key]["name"] == "TRANSPOSE":
                print("transpose, to be implemented")

            elif mapping[component_key]["name"] == "STEP REPEAT":
                print("step repeat, to be implemented")

            elif mapping[component_key]["name"] == "STEP HOLD":
                print("step hold, to be implemented")

            elif mapping[component_key]["name"] == "JUMP TO":
                print("jump to, to be implemented")

            elif mapping[component_key]["name"] == "MUTE TRACKS":
                print("mute tracks, to be implemented")

            elif mapping[component_key]["name"] == "SOLO TRACKS":
                print("solo tracks, to be implemented")

            elif mapping[component_key]["name"] == "RANDOMISE":
                print("randomise, to be implemented")

            elif mapping[component_key]["name"] == "RAMP":
                print("ramp, to be implemented")

            elif mapping[component_key]["name"] == "RETRIGGER":
                print("retrigger, to be implemented")

            elif mapping[component_key]["name"] == "PROBABILITY":
                print("probability, to be implemented")

            elif mapping[component_key]["name"] == "SKIP":
                print("skip, to be implemented")

            elif mapping[component_key]["name"] == "CLEAR":
                print("clear, to be implemented")

    def update_song_playhead(self):
        next_step = self.song_playhead + 1
        if next_step < len(self.song) and self.song[next_step] is not None:
            self.song_playhead = next_step
            self.phrase_playhead = 0

            # handle case where sequencer is playing and no patterns in phrase track
            playing_phrase_num = self.song[self.song_playhead]
            playing_pattern_num = self.phrase_pool[playing_phrase_num][self.phrase_playhead]
            if playing_pattern_num not in self.pattern_pool.keys():
                self.song_playhead = 0
        else:
            while self.song[self.song_playhead] is not None:
                self.song_playhead -= 1
                if self.song_playhead == 0:
                    break
            if self.song[self.song_playhead] is None:
                self.song_playhead += 1

            self.phrase_playhead = 0

    def update_phrase_playhead(self):
        next_step = self.phrase_playhead + 1
        current_phrase_num = self.song[self.song_playhead]
        current_patterns = self.phrase_pool[current_phrase_num]
        if next_step < len(current_patterns) and current_patterns[next_step] is not None:
            self.phrase_playhead = next_step
        else:
            self.update_song_playhead()  # Move to next song step if no more patterns in current phrase

    def update_track_playheads(self):
        playing_pattern = self.get_playing_pattern()
        ticks = []
        chk_components = False
        if playing_pattern.master_track.tick():
            chk_components = True
            if playing_pattern.master_track.ticks == 0:
                self.pages[TIMELINE].flag_state_change()
                self.update_phrase_playhead()
                self.update_pattern_parameters()
                self.reset_track_playheads()
                return

        for track in playing_pattern.midi_tracks:
            ticks.append(track.tick())

        if chk_components:
            master = playing_pattern.master_track
            self.process_master_components()

        for i, tick in enumerate(ticks):
            if tick:
                playing_pattern.midi_tracks[i].play_step()
        return

    def reset_track_playheads(self):
        playing_pattern = self.get_playing_pattern()
        playing_pattern.master_track.reset()
        for track in playing_pattern.midi_tracks:
            track.reset()

        self.process_master_components()
        for track in playing_pattern.midi_tracks:
            track.play_step()

    @timing_decorator
    def clone_pattern(self, pattern):
        if pattern is None:
            return
        new_pattern_num = None
        # find next unused pattern number
        for i in range(constants.max_patterns):
            if i not in self.pattern_pool.keys():
                new_pattern_num = i
                break

        if new_pattern_num is not None:
            new_pattern = pattern.clone(new_pattern_num)
            self.pattern_pool[new_pattern_num] = new_pattern

        return new_pattern_num

    def add_pattern_if_not_exists(self, pattern_num):
        if pattern_num not in self.pattern_pool.keys():
            new = Pattern(pattern_num, self.last_length, self.last_lpb,
                          self.last_bpm, self.last_swing, tracker=self)
            self.pattern_pool[pattern_num] = new

        return self.pattern_pool[pattern_num]

    def add_phrase_if_not_exists(self, phrase_num):
        if phrase_num not in self.phrase_pool.keys():
            self.phrase_pool[phrase_num] = [None for _ in range(1000)]

        return self.phrase_pool[phrase_num]

    def adjust_song_step(self, index, value):
        new_val = calculate_timeline_increment(self.song[index], value)
        self.song[index] = new_val
        self.add_phrase_if_not_exists(new_val)
        return new_val

    def adjust_phrase_step(self, index, increment):
        selected_phrase = self.get_selected_phrase()
        new_val = calculate_timeline_increment(selected_phrase[index], increment)
        selected_phrase[index] = new_val
        self.add_pattern_if_not_exists(new_val)
        return new_val

    def get_selected_master_step(self):
        selected_pattern = self.get_selected_pattern()
        if selected_pattern is None:
            return None

        return selected_pattern.master_track.steps[self.pages[MASTER].cursor_y]

    def get_selected_step(self, track=None):
        if track is None:
            track = self.get_selected_track()
            if track is None:
                return None

        if self.pages[PATTERN].cursor_y >= track.length:
            return None
        return track.steps[self.pages[PATTERN].cursor_y]

    def get_selected_track(self):
        selected_pattern = self.get_selected_pattern()
        if selected_pattern is None:
            return None

        return selected_pattern.midi_tracks[self.pages[PATTERN].cursor_x]

    def handle_select(self):
        self.pages[self.page].handle_select()

    def handle_delete(self, remove_steps=False):
        self.pages[self.page].handle_delete(remove_steps)

    def handle_insert(self):
        self.pages[self.page].handle_insert()

    def handle_param_adjust(self, value, alt=False):
        try:
            self.pages[self.page].handle_param_adjust(value, alt)
        except TypeError as e:
            import traceback
            traceback.print_exc()
            print(f"Error {e}: handle_param_adjust method not implemented for current page", self.page,
                  "Please implement this method in the current page class", "Page = ", self.pages[self.page])

    def adjust_velocity(self, inc):
        step = self.get_selected_step()
        if step is not None:
            for pos in range(4):
                curr_vel = step.velocities[pos]
                if curr_vel is not None:
                    step.update_velocity(pos, min(max(0, curr_vel + inc), 127))

    def move_in_place(self, x, y):
        self.pages[self.page].move_in_place(x, y)

    def handle_copy(self):
        self.pages[self.page].handle_copy()

    def handle_paste(self):
        self.pages[self.page].handle_paste()

    def move_cursor(self, x, y, expand_selection=False):
        self.pages[self.page].move_cursor(x, y, expand_selection)

    def handle_duplicate(self):
        self.pages[self.page].handle_duplicate()

    def seek(self, xy, expand_selection=False):
        x, y = xy
        if self.page == EDITOR:
            self.pages[self.page].seek(xy, expand_selection=True)
        elif self.page == PATTERN or self.page == MASTER:
            self.pages[self.page].move_cursor(x * 8, y * 8, expand_selection)

    def toggle_editor_window(self):
        if self.pages[EDITOR].active:
            self.page_switch(None, None, page_num=self.pages[EDITOR].previous_page)
        else:
            self.pages[EDITOR].previous_page = self.page
            self.page_switch(None, None, page_num=EDITOR)

    def toggle_timeline_view(self):
        if self.pages[TIMELINE].active:
            self.page_switch(None, None, PATTERN)
        else:
            self.pages[TIMELINE].previous_page = self.page
            self.page_switch(None, None, TIMELINE)

    def page_switch(self, x, y, page_num=None):
        if page_num is not None:
            self.page = page_num
        else:
            if y != 0 and self.page == EDITOR:
                self.pages[EDITOR].open_page(page_index=None, increment=y)
            elif y > 0:
                if self.page == PATTERN or self.page == MASTER:
                    self.pages[TIMELINE].previous_page = self.page
                    self.page = TIMELINE
                elif self.page == TIMELINE:
                    self.pages[TIMELINE].move_cursor(0, y)
            elif y < 0 and self.page == TIMELINE:
                if self.pages[TIMELINE].cursor_y == 1:
                    self.pages[TIMELINE].move_cursor(0, y)
                else:
                    self.page = self.pages[TIMELINE].previous_page
            elif x > 0 and self.page == MASTER:
                self.page = PATTERN
                self.event_bus.publish(events.ON_PATTERN_TRACK)
            elif x < 0 and self.page == PATTERN:
                self.page = MASTER
                self.event_bus.publish(events.ON_MASTER_TRACK)
            elif x != 0 and self.page == TIMELINE:
                self.pages[TIMELINE].move_cursor(x, 0)

        self.pages[PATTERN].update_y_anchor(self.page)

        for i, view in self.pages.items():
            if (i != self.page and view.active) or (i == self.page and not view.active):
                view.toggle_active()

    def stop_preview(self):
        selected_pattern = self.get_selected_pattern()
        if not self.is_playing:
            if self.page == PATTERN and self.pages[PATTERN].cursor_x > 0:
                track = selected_pattern.tracks[self.pages[PATTERN].cursor_x]
                self.midi_handler.all_notes_off(track.channel)

    def options_menu(self, is_active):
        pass

    def reset(self):
        pass

    def toggle_mute(self):
        selected_pattern = self.get_selected_pattern()
        for index in self.pages[PATTERN].selected_tracks:
            track = selected_pattern.midi_tracks[index]
            if not track.is_master:
                track.handle_mute(send_note_offs=self.on_playing_pattern())

    def preview_step(self, notes_only=False):
        if not self.is_playing:
            track = self.get_selected_track()
            if track.is_master:
                return

            step = self.get_selected_step()
            if not track.is_muted:
                if not notes_only:
                    track.handle_ccs(step.ccs)

                track.handle_notes(step.notes, step.velocities)

    def keyboard_insert(self, key):
        print(self.page)
        self.pages[self.page].keyboard_insert(key)

    def save_song(self):
        pass
        """
        self.sequencer.stop_playback()
        save_name = self.renderer.user_input("Please enter a save name, then press Enter",
                                             "tracker_font", themeing.BG_TASKPANE)

        serialised_sequencer_data = self.sequencer.json_serialize()
        save_name = "save_files/" + save_name if not save_name.startswith("save_files/") else save_name
        save_name += ".json" if not save_name.endswith(".json") else ""

        with open(save_name, 'w') as file:
            json.dump(serialised_sequencer_data, file)

        print("Song saved successfully!")
        """

    def load_song(self):
        pass

    def new_song(self):
        self.stop_playback()
        """
        ret = self.renderer.user_input("Do you want to save the current project first? (Y/N)",
                                       "tracker_font", themeing.BG_TASKPANE)
        if ret.lower() == "y":
            self.save_song()
        self.reset()"""

    def jump_page(self, opt):
        pass
        """
        if opt == 'down':
            if self.state.phrase_cursor["y"] + 1 < self.state.timeline_length:
                if self.state.cursor_phrase[self.state.phrase_cursor["y"] + 1] is None:
                    self.insert('pattern')
                else:
                    self.state.phrase_cursor["y"] += 1
                    self.state.set_cursor_pattern(self.state.cursor_phrase[self.state.phrase_cursor["y"]])

        elif opt == 'up':
            if self.state.phrase_cursor["y"] - 1 >= 0:
                if self.state.cursor_phrase[self.state.phrase_cursor["y"] - 1] is not None:
                    self.state.phrase_cursor["y"] -= 1
                    self.state.set_cursor_pattern(self.state.cursor_phrase[self.state.phrase_cursor["y"]])
        """

    def adjust_length(self, increment):
        selected_pattern = self.get_selected_pattern()
        pattern_view = self.pages[PATTERN]
        selected_tracks = pattern_view.get_selected_tracks()
        if selected_pattern is not None:
            for x in selected_tracks:
                selected_pattern.midi_tracks[x].adjust_length(increment)
                self.event_bus.publish(events.PATTERN_TRACK_STATE_CHANGED, x)
            # self.sequencer.update_sequencer_params()

    def adjust_lpb(self, increment):
        selected_pattern = self.get_selected_pattern()
        pattern_view = self.pages[PATTERN]
        selected_tracks = pattern_view.get_selected_tracks()
        if selected_pattern is not None:
            for x in selected_tracks:
                selected_pattern.midi_tracks[x].adjust_lpb(increment)
                self.event_bus.publish(events.PATTERN_TRACK_STATE_CHANGED, x)

    def adjust_bpm(self, increment):
        selected_pattern = self.get_selected_pattern()
        if selected_pattern is not None:
            new_bpm = min(max(1, selected_pattern.bpm + increment), 1000)
            selected_pattern.bpm = new_bpm
            self.update_pattern_parameters()
            self.last_bpm = new_bpm

    ### mouse methods ###
    def screen_pos_to_pattern_pos(self, x, y):
        pass
        """
        y_cursor = self.state.pattern_cursor["y"] if not self.temp_y else self.temp_y
        pattern_y = (y - (self.renderer.center_y - (y_cursor * display.row_h))) // display.row_h
        pattern_x = (x - (display.timeline_width + 51)) // display.col_w

        pattern_x = min(max(0, pattern_x), constants.track_count - 1)
        pattern_y = min(max(0, pattern_y), self.cursor_pattern.tracks[self.state.pattern_cursor["x"]].length - 1)

        return pattern_x, pattern_y
        """

    def process_mouse(self, initial_pos, final_pos, s):
        pass
        """
        # the way to fix this will be to integrate an option to disable centering of the y_cursor
        # on the screen. If mouse pressed, this is disabled automatically
        # in this case, the tracker would just scroll through pages like the M8
        for step in self.cursor_pattern.master_track.steps:
            print(step.components)
        if initial_pos is None or final_pos is None:
            return None

        x0, y0 = initial_pos
        x1, y1 = final_pos

        if s == 2:  # mouse up
            self.state.pattern_cursor["y"] = self.temp_y
            self.temp_y = None
            return

        x_start, y_start = self.screen_pos_to_pattern_pos(x0, y0)
        x_end, y_end = self.screen_pos_to_pattern_pos(x1, y1)

        print(f"Initial x, y: {x_start, y_start}, Final x, y: {x_end, y_end}")

        if s == 0:  # mouse down
            self.temp_y = y_start
            print(f"temp y: {self.temp_y}")
            self.state.pattern_cursor["x"] = x_start
            self.state.pattern_cursor["w"] = 0
            self.state.pattern_cursor["h"] = 0
            return

        if x_start is not False and x_end is not False:
            self.state.pattern_cursor["x"] = x_end
            self.state.pattern_cursor["w"] = x_end - x_start

        if y_start is not False and y_end is not False:
            self.state.pattern_cursor["h"] = y_start - y_end
        """
