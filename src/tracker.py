from threading import Lock
import time
import json
from time import perf_counter
import timeit

from config import constants, display, themeing, events
from config.pages import *
from config.constants import page_map as pmap
from src.utils import timing_decorator, calculate_timeline_increment

from src.input_handler import InputHandler
from src.midi_handler import MidiHandler
from src.sequencer import Clock
from src.renderer import Renderer
from src.pattern import Pattern

from src.ui_components.info_pane import InfoPane
from src.ui_components.pattern_view import PatternEditor
from src.ui_components.master_view import MasterTrack
from src.ui_components.editor_window import EditorWindow
from src.ui_components.timeline_tracks import SongTrack, PhraseTrack

from src.gui_elements import RowNumberCell



# going for component based architecture with elements of MVC

"""
You could call this a "Hierarchical MVC with Component-Based Views" or a "Centralized Data Component Architecture." 
The exact name isn't as important as understanding its key characteristics:

Centralized data management
Decentralized view state management
Hierarchical structure
Event-driven updates
Separation of concerns between data, input handling, and view rendering

This architecture seems well-suited for a music sequencer, as it allows for complex data management while providing 
flexibility in how different parts of the UI are rendered and updated.
"""


class Tracker:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.event_bus.subscribe(events.QUIT, self.quit)
        self.track_count = constants.track_count
        self.timeline_length = constants.timeline_length
        self.song_pool = [0] + [None for _ in range(self.timeline_length - 1)]
        self.phrase_pool = {None: [None for _ in range(self.timeline_length)],
                            0: [0] + [None for _ in range(self.timeline_length - 1)]}
        self.pattern_pool = {None: None,
                             0: Pattern(num=0, length=constants.start_len, lpb=constants.start_lpb,
                                        bpm=constants.start_bpm, swing=constants.start_swing, tracker=self)}
        self.song_playhead = 0
        self.phrase_playhead = 0
        self.cursor_pattern = self.pattern_pool[0]
        self.cursor_phrase = self.phrase_pool[0]
        self.playing_pattern = self.cursor_pattern
        self.on_playing_pattern = True
        self.is_playing = False
        self.follow_playhead = False

        self.renderer = Renderer(self)
        self.renderer.initialise()
        self.input_handler = InputHandler(self)
        self.midi_handler = MidiHandler()
        self.clock = Clock(bpm=self.cursor_pattern.bpm, callback=self.tick)
        self._tick_mutex = Lock()
        self.ticks = 0

        self.mouse_x = 0
        self.mouse_y = 0

        self.octave_mod = 2
        self.last_note = constants.start_note
        self.last_vel = constants.start_vel
        self.last_bpm = constants.start_bpm
        self.last_lpb = constants.start_lpb
        self.last_length = constants.start_len
        self.last_swing = constants.start_swing
        self.channel_ccs = [[1, 2, 3, 4, 5, 6, 7, 8] for _ in range(8)]

        self.page = 3
        self.pages = {}

        self.page_border = None
        self.is_playing = False
        self.running = False

        row_number_cells = [RowNumberCell(y) for y in range(display.visible_rows)] # shared between pattern and master
        self.info_pane = InfoPane(self)
        self.pages[0] = SongTrack(self)
        self.pages[1] = PhraseTrack(self)
        self.pages[2] = MasterTrack(self, row_number_cells)
        self.pages[3] = PatternEditor(self, row_number_cells)
        self.pages[4] = EditorWindow(self)


        # some ui components need to share state vars
        self.pages[MASTER].pattern_view = self.pages[PATTERN]
        self.pages[PATTERN].master_track_view = self.pages[MASTER]


    def running_loop(self):
        try:
            self.running = True
            render_interval = 1 / 60
            last_render_time = perf_counter()
            while self.running:
                self.handle_events()
                curr_time = perf_counter()
                elapsed = curr_time - last_render_time
                if elapsed >= render_interval:
                    self.update_view_states()
                    self.renderer.process_queue()
                    self.renderer.update_screen()
                    last_render_time = curr_time
                else:
                    time.sleep(render_interval - elapsed)

        finally:
            print("Cleaning up and exiting...")
            self.quit()

    @timing_decorator
    def update_view_states(self):
        self.info_pane.update_view()
        for _, page in self.pages.items():
            if page is not None:
                page.update_view()
        self.renderer.process_queue()
        self.renderer.update_screen()

    def quit(self):
        self.renderer.quit()
        self.clock.stop()
        self.midi_handler.all_notes_off()
        self.midi_handler.send_midi_stop()
        self.midi_handler.midi_out.close_port()

    @timing_decorator
    def tick(self):
        with self._tick_mutex:
            self.midi_handler.send_midi_clock()
            if not self.is_playing:
                return
            self.update_track_playheads()
            self.ticks += 1

    def update_pattern_parameters(self):
        playing_phrase_num = self.song_pool[self.song_playhead]
        playing_pattern_num = self.phrase_pool[playing_phrase_num][self.phrase_playhead]
        if playing_pattern_num is not None:
            playing_pattern = self.pattern_pool[playing_pattern_num]
            self.playing_pattern = playing_pattern
            self.clock.set_bpm(self.playing_pattern.bpm)

            if self.follow_playhead:
                self.cursor_pattern = self.playing_pattern
                self.cursor_phrase = self.phrase_pool[playing_phrase_num]

            self.on_playing_pattern = (self.playing_pattern == self.cursor_pattern)

        else:
            self.is_playing = False


    def stop_playback(self):
        self.is_playing = False
        self.ticks = 0
        self.midi_handler.all_notes_off()
        self.midi_handler.send_midi_stop()
        self.pages[pmap["song"]].flag_state_change()
        self.pages[pmap["phrase"]].flag_state_change()

    def start_playback(self):
        print('\n########### Starting playback ###########\n')
        for i, track in enumerate(self.playing_pattern.midi_tracks):
            track.is_reversed = False
        self.set_playing_pattern_to_cursor()
        self.update_pattern_parameters()
        self.reset_track_playheads()
        self.midi_handler.send_midi_start()
        self.is_playing = True
        self.pages[pmap["song"]].flag_state_change()
        self.pages[pmap["phrase"]].flag_state_change()

    def process_master_components(self):
        master_components = self.playing_pattern.master_track.get_components()

        for component in master_components:
            if component is not None:
                if component[0] == 'REV':
                    self.playing_pattern.reverse_tracks()
                elif component[0] == 'SNC':
                    self.playing_pattern.synchronise_playheads(self.channel_ccs, self.midi_handler)

    def update_song_playhead(self):
        next_step = self.song_playhead + 1
        if next_step < len(self.song_pool) and self.song_pool[next_step] is not None:
            self.song_playhead = next_step
            self.phrase_playhead = 0

            # handle case where sequencer is playing and no patterns in phrase track
            playing_phrase_num = self.song_pool[self.song_playhead]
            playing_pattern_num = self.phrase_pool[playing_phrase_num][self.phrase_playhead]
            if playing_pattern_num not in self.pattern_pool.keys():
                self.song_playhead = 0
        else:
            self.song_playhead = 0
            self.phrase_playhead = 0

    def update_phrase_playhead(self):
        next_step = self.phrase_playhead + 1
        current_phrase_num = self.song_pool[self.song_playhead]
        current_patterns = self.phrase_pool[current_phrase_num]
        if next_step < len(current_patterns) and current_patterns[next_step] is not None:
            self.phrase_playhead = next_step
        else:
            self.update_song_playhead()  # Move to next song step if no more patterns in current phrase

        self.update_pattern_parameters()

    def update_track_playheads(self):
        ticks = []
        chk_components = False
        if self.playing_pattern.master_track.tick():
            chk_components = True
            if self.playing_pattern.master_track.ticks == 0:
                self.pages[pmap["song"]].flag_state_change()
                self.pages[pmap["phrase"]].flag_state_change()
                self.update_phrase_playhead()
                self.update_pattern_parameters()
                self.reset_track_playheads()
                return

        for track in self.playing_pattern.midi_tracks:
            ticks.append(track.tick())

        if chk_components:
            self.process_master_components()

        for i, tick in enumerate(ticks):
            if tick:
                self.playing_pattern.midi_tracks[i].play_step(self.channel_ccs, self.midi_handler)
        return

    def reset_track_playheads(self):
        tracks = self.playing_pattern.tracks
        for track in tracks:
            track.reset()
        for track in tracks:
            if track.is_master:
                self.process_master_components()
            else:
                track.play_step(self.channel_ccs, self.midi_handler)

    def update_playing_pattern(self):
        playing_phrase_num = self.song_pool[self.song_playhead]
        playing_pattern_num = self.phrase_pool[playing_phrase_num][self.phrase_playhead]
        self.playing_pattern = self.pattern_pool[playing_pattern_num]
        self.event_bus.publish(events.TIMELINE_STATE_CHANGED)

    def is_cursor_on_playing_pattern(self):
        song_y = self.pages[pmap["song"]].cursor_y
        phrase_y = self.pages[pmap["phrase"]].cursor_y
        cursor_pattern_num = self.phrase_pool[self.song_pool[song_y]][phrase_y]
        if cursor_pattern_num is None:
            return False
        playing_phrase_num = self.song_pool[self.song_playhead]
        playing_pattern_num = self.phrase_pool[playing_phrase_num][self.phrase_playhead]
        if playing_pattern_num in self.pattern_pool.keys():
            return cursor_pattern_num == playing_pattern_num
        return False

    def add_pattern(self, pattern_num):
        if pattern_num not in self.pattern_pool.keys():
            new = Pattern(pattern_num, self.last_length, self.last_lpb, self.last_bpm, self.last_swing, tracker=self)
            self.pattern_pool[pattern_num] = new

    def add_phrase(self, phrase_num):
        if phrase_num not in self.phrase_pool.keys():
            self.phrase_pool[phrase_num] = [None for _ in range(1000)]

    def get_next_pattern(self):
        song_y = self.pages[pmap["song"]].cursor_y
        phrase_y = self.pages[pmap["phrase"]].cursor_y
        cursor_pattern_num = self.phrase_pool[self.song_pool[song_y]][phrase_y]
        if cursor_pattern_num is None:
            return None
        next_phrase_cursor = (phrase_y + 1) % constants.timeline_length
        next_pattern_num = self.phrase_pool[self.song_pool[song_y]][next_phrase_cursor]
        return self.pattern_pool[next_pattern_num]

    def set_playing_pattern(self, pattern_num):
        if pattern_num is not None:
            self.playing_pattern = self.pattern_pool[pattern_num]
            playing_phrase_num = self.song_pool[self.song_playhead]
            playing_pattern_num = self.phrase_pool[playing_phrase_num][self.phrase_playhead]
            if playing_pattern_num is not None:
                self.playing_pattern = self.pattern_pool[playing_pattern_num]
                if self.follow_playhead:
                    self.cursor_pattern = self.playing_pattern
                    self.cursor_phrase = self.phrase_pool[playing_phrase_num]
            else:
                self.is_playing = False

    def set_cursor_pattern(self, pattern_num):
        self.cursor_pattern = None
        if pattern_num is not None:
            self.add_pattern(pattern_num)
            self.cursor_pattern = self.pattern_pool[pattern_num]

    def set_playing_pattern_to_cursor(self):
        song_y = self.pages[pmap["song"]].cursor_y
        phrase_y = self.pages[pmap["phrase"]].cursor_y
        cursor_pattern_num = self.phrase_pool[self.song_pool[song_y]][phrase_y]
        if cursor_pattern_num is not None and not self.is_cursor_on_playing_pattern():
            self.song_playhead = song_y
            self.phrase_playhead = phrase_y
            self.set_playing_pattern(cursor_pattern_num)

        print(self.playing_pattern.num)

    def set_current_phrase(self, phrase_num):
        self.add_phrase(phrase_num)
        self.cursor_phrase = self.phrase_pool[phrase_num]
        if self.cursor_phrase[0] is not None:
            self.cursor_pattern = self.pattern_pool[self.cursor_phrase[0]]
        else:
            self.cursor_pattern = None

    def update_song_step(self, index, value):
        new_val = calculate_timeline_increment(self.song_pool[index], value)
        self.song_pool[index] = new_val
        if new_val is not None:
            self.add_phrase(new_val)
            self.set_current_phrase(new_val)
            self.set_cursor_pattern(self.cursor_phrase[0])
        else:
            self.set_current_phrase(None)

    def update_phrase_step(self, index, value):
        new_val = calculate_timeline_increment(self.cursor_phrase[index], value)
        self.cursor_phrase[index] = new_val
        self.set_cursor_pattern(new_val)

    def get_selected_step(self, track=None):
        pattern_view = self.pages[PATTERN]
        if track is None:
            track = self.get_selected_track()
        if pattern_view.cursor_y >= track.length:
            return None
        return track.steps[pattern_view.cursor_y]

    def get_selected_track(self):
        pattern_view = self.pages[PATTERN]
        try:
            return self.cursor_pattern.midi_tracks[pattern_view.cursor_x]
        except IndexError:
            return None

    def handle_select(self):
        self.pages[self.page].handle_select()

    def handle_delete(self, remove_steps=False):
        self.pages[self.page].handle_delete(remove_steps)

    def handle_insert(self):
        self.pages[self.page].handle_insert()

    def handle_param_adjust(self, increment):
        self.pages[self.page].handle_param_adjust(increment)

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

    def activate_editor_window(self):
        editor_window_page = EDITOR
        if self.pages[editor_window_page].active:
            return

        self.pages[editor_window_page].previous_page = self.page
        self.page_switch(direction=None, page_num=editor_window_page)

    def deactivate_editor_window(self):
        if not self.pages[EDITOR].active:
            return

        prev_page = self.pages[EDITOR].previous_page
        if prev_page is not None:
            self.page_switch(direction=None, page_num=prev_page)

    def page_switch(self, direction, page_num=None):
        if page_num is None:
            self.page = (self.page + direction) % (len(self.pages) - 1)
        else:
            self.page = page_num

        self.pages[PATTERN].update_y_anchor(self.page)

        for i, view in self.pages.items():
            if view is None:
                continue
            if (i != self.page and view.active) or (i == self.page and not view.active):
                view.toggle_active()



    def handle_events(self):
        input_return = self.input_handler.check_for_events(current_time=perf_counter())
        if input_return == "Exit":
            self.running = False

    def stop_preview(self):
        if not self.is_playing:
            if self.page == PATTERN and self.pages[PATTERN].cursor_x > 0:
                track = self.cursor_pattern.tracks[self.pages[PATTERN].cursor_x]
                self.midi_handler.all_notes_off(track.channel)

    def options_menu(self, is_active):
        pass

    def reset(self):
        pass

    def toggle_playback(self):
        if self.is_playing:
            self.stop_playback()
        else:
            if self.cursor_pattern is not None:
                self.set_playing_pattern_to_cursor()
                self.start_playback()

    def toggle_mute(self, track_indices=None):
        if track_indices is None:
            x, xs = self.state.pattern_cursor["x"], self.state.pattern_cursor["w"]
            x = x - xs if xs > 0 else x
            w = max((x - xs), x) - min((x - xs), x) + 1
            track_indices = [i for i in range(x, x + w)]
        for index in track_indices:
            track = self.cursor_pattern.tracks[index]
            if not track.is_master:
                track.handle_mute(send_note_offs=self.on_playing_pattern, midi_handler=self.midi_handler)

    def preview_step(self):
        if not self.is_playing:
            track = self.get_selected_track()
            if track.is_master:
                return

            step = self.get_selected_step()
            if not track.is_muted:
                track.handle_ccs(self.channel_ccs, step.ccs, self.midi_handler)
                track.handle_notes(step.notes, step.velocities, self.midi_handler)

    def add_master_component(self, step, data):
        if data == 12:
            step.add_component(["REV", "--", "--"])
        elif data == 14:
            step.add_component(["SNC", "--", "--"])

    def keyboard_insert(self, data):
        track = self.get_selected_track()
        step = self.get_selected_step()

        if track.is_master:
            self.add_master_component(step, data)
            return

        note = data if data == -1 else data + (self.octave_mod * 12)
        if self.page == EDITOR:
            self.add_note(step, self.pages[EDITOR].cursor_y, note)
        else:
            self.pages[EDITOR].state_changed = True
            for pos in range(4):
                step.update_note(pos, note if pos == 0 else None)
                step.update_velocity(pos, self.last_vel if pos == 0 else None)
            self.last_note = note
        self.preview_step()


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

    # so we want to update the pattern step in the phrase track to the new pattern number
    # then we want to update the current pattern to the new pattern number
    
    def insert_pattern(self):
        phrase_cursor = self.pages[pmap["phrase"]].cursor_y
        if phrase_cursor + 1 >= self.timeline_length:
            return

        # get next unused pattern number
        for i in range(constants.max_patterns):
            if i not in self.pattern_pool.keys():
                while self.cursor_phrase[phrase_cursor] is not None:
                    phrase_cursor += 1
                self.update_phrase_step(phrase_cursor, i + 1)
                self.pages[pmap["phrase"]].cursor_y = phrase_cursor
                break
    
    def insert_phrase(self):
        song_cursor = self.pages[pmap["song"]].cursor_y
        phrase_cursor = self.pages[pmap["phrase"]].cursor_y
        
        if song_cursor + 1 >= self.timeline_length:
                return
        for i in range(self.timeline_length):
            if i not in self.phrase_pool.keys():
                while self.song_pool[song_cursor] is not None:
                    song_cursor += 1
                self.sequencer.update_song_step(song_cursor, i + 1)
                break

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

    def update_timeline_step(self, val):
        pass
        """
        if self.state.page == 0:
            self.state.update_song_step(self.state.song_cursor, val)
        elif self.state.page == 1:
            if self.state.song_track[self.state.song_cursor] is not None:
                self.state.update_phrase_step(self.state.phrase_cursor["y"], val)
        """

    def activate_detail_window(self):
        pass
        """
        if not self.state.page == 4:
            self.state.page = 4
        else:
            self.step_detail_window_widget.handle_select(self.state.get_selected_step())
        """


    def master_seek(self):
        print("master seek, to do")

    def pattern_seek(self, opt, expand_selection):
        pass

    def song_seek(self):
        print("Song seek, to do")

    def phrase_seek(self):
        print("Phrase seek, to do")

    def seek(self, opt, expand_selection=False):
        pass

    def adjust_length(self, increment):
        pattern_view = self.pages[PATTERN]
        selected_tracks = pattern_view.get_selected_tracks()
        if self.cursor_pattern is not None:
            for x in selected_tracks:
                self.cursor_pattern.midi_tracks[x].adjust_length(increment)
                self.event_bus.publish(events.PATTERN_TRACK_STATE_CHANGED, x)
            # self.sequencer.update_sequencer_params()

    def adjust_lpb(self, increment):
        pattern_view = self.pages[PATTERN]
        selected_tracks = pattern_view.get_selected_tracks()
        if self.cursor_pattern is not None:
            for x in selected_tracks:
                self.cursor_pattern.midi_tracks[x].adjust_lpb(increment)
                self.event_bus.publish(events.PATTERN_TRACK_STATE_CHANGED, x)

    def adjust_bpm(self, increment):
        if self.cursor_pattern is not None:
            new_bpm = min(max(1, self.cursor_pattern.bpm + increment), 1000)
            self.cursor_pattern.bpm = new_bpm
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

