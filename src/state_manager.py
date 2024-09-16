from src.pattern import Pattern
from config import constants, display, themeing
from src.utils import calculate_timeline_increment


class EventBus:
    def __init__(self):
        self._handlers = {}

    def on(self, event_type, handler):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def emit(self, event_type, data=None):
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                handler(data)

class StateManager:
    def __init__(self):
        self.event_bus = EventBus()

        # sequencer parameters
        self.pulse = 0
        self.track_count = constants.track_count
        self.timeline_length = constants.timeline_length
        self.song_track = [0] + [None for _ in range(self.timeline_length-1)]
        self.phrase_pool = {None: [None for _ in range(self.timeline_length)],
                            0: [0] + [None for _ in range(self.timeline_length-1)]}
        self.pattern_pool = {None: None,
                             0: Pattern(num=0, length=constants.start_len, lpb=constants.start_lpb,
                                        bpm=constants.start_bpm, swing=constants.start_swing)}
        self.song_playhead = 0
        self.phrase_playhead = 0
        self.cursor_pattern = self.pattern_pool[0]
        self.cursor_phrase = self.phrase_pool[0]
        self.playing_pattern = self.cursor_pattern
        self.on_playing_pattern = True
        self.is_playing = False
        self.follow_playhead = False

        # tracker control parameters
        self.page = 3
        self.pattern_cursor = {"x": 0, "y": 0, "w": 0, "h": 0}
        self.selected_rows = [0]
        self.selected_tracks = [0]
        self.master_cursor = {"y": 0, "h": 0}
        self.song_cursor = {"y": 0, "h": 0}
        self.phrase_cursor = {"y": 0, "h": 0}
        self.param_cursor = 0

        # detail window parameters
        self.detail_window_x = 0
        self.detail_window_y = 0

        # store this within tracks
        self.last_notes_played = [{"Notes": [None, None, None, None], "Channel": None} for _ in range(8)]
        self.mutes = [False for _ in range(8)]
        self.last_note_pulses = [0 for _ in range(8)]
        self.channel_ccs = [[None for _ in range(8)] for _ in range(8)]

        self.clipboard = []

        self.octave_mod = 2
        self.last_note = constants.start_note
        self.last_vel = constants.start_vel
        self.last_cc = 1
        self.last_cc_val = 0

        self.mouse_x = 0
        self.mouse_y = 0

        self.last_bpm = constants.start_bpm
        self.last_lpb = constants.start_lpb
        self.last_length = constants.start_len
        self.last_swing = constants.start_swing

    def update_channel_ccs(self, channel, index, control):
        self.channel_ccs[channel][index] = control
        self.last_cc = control

    def on_pattern(self):
        return self.page == 3 and self.pattern_cursor["x"] > 0

    def on_master(self):
        return self.page == 2

    def on_phrase(self):
        return self.page == 1

    def on_song(self):
        return self.page == 0

    def get_step(self):
        return self.cursor_pattern.tracks[self.pattern_cursor["x"]].steps[self.pattern_cursor["y"]]

    def is_cursor_on_playing_pattern(self):
        cursor_pattern_num = self.phrase_pool[self.song_track[self.song_cursor["y"]]][self.phrase_cursor["y"]]
        if cursor_pattern_num is None:
            return False
        playing_phrase_num = self.song_track[self.song_playhead]
        playing_pattern_num = self.phrase_pool[playing_phrase_num][self.phrase_playhead]
        if playing_pattern_num in self.pattern_pool.keys():
            return cursor_pattern_num == playing_pattern_num
        return False

    def add_pattern(self, pattern_num):
        if pattern_num not in self.pattern_pool.keys():
            new = Pattern(pattern_num, self.last_length, self.last_lpb, self.last_bpm, self.last_swing)
            self.pattern_pool[pattern_num] = new

    def add_phrase(self, phrase_num):
        if phrase_num not in self.phrase_pool.keys():
            self.phrase_pool[phrase_num] = [None for _ in range(1000)]

    def get_next_pattern(self):
        cursor_pattern_num = self.phrase_pool[self.song_track[self.song_cursor["y"]]][self.phrase_cursor["y"]]
        if cursor_pattern_num is None:
            return None
        next_phrase_cursor = (self.phrase_cursor["y"] + 1) % constants.timeline_length
        next_pattern_num = self.phrase_pool[self.song_track[self.song_cursor["y"]]][next_phrase_cursor]
        return self.pattern_pool[next_pattern_num]

    def set_playing_pattern(self, pattern_num):
        if pattern_num is not None:
            self.playing_pattern = self.pattern_pool[pattern_num]
            playing_phrase_num = self.song_track[self.song_playhead]
            playing_pattern_num = self.phrase_pool[playing_phrase_num][self.phrase_playhead]
            if playing_pattern_num is not None:
                self.playing_pattern = self.pattern_pool[playing_pattern_num]
                if self.follow_playhead:
                    self.cursor_pattern = self.playing_pattern
                    self.cursor_phrase = self.phrase_pool[playing_phrase_num]
                self.event_bus.emit("Sequencer parameters updated")
            else:
                self.is_playing = False

    def set_cursor_pattern(self, pattern_num):
        self.cursor_pattern = None
        if pattern_num is not None:
            self.add_pattern(pattern_num)
            self.cursor_pattern = self.pattern_pool[pattern_num]

    def set_playing_pattern_to_cursor(self):
        cursor_pattern_num = self.phrase_pool[self.song_track[self.song_cursor["y"]]][self.phrase_cursor["y"]]
        if cursor_pattern_num is not None and not self.is_cursor_on_playing_pattern():
            self.song_playhead = self.song_cursor
            self.phrase_playhead = self.phrase_cursor["y"]
            self.set_playing_pattern(cursor_pattern_num)

    def set_current_phrase(self, phrase_num):
        self.add_phrase(phrase_num)
        self.cursor_phrase = self.phrase_pool[phrase_num]
        if self.cursor_phrase[0] is not None:
            self.cursor_pattern = self.pattern_pool[self.cursor_phrase[0]]
        else:
            self.cursor_pattern = None

    def update_song_step(self, index, value):
        new_val = calculate_timeline_increment(self.song_track[index], value)
        self.song_track[index] = new_val
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





