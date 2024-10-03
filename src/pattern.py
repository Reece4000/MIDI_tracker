from src.tracks import MasterTrack, MidiTrack
from config import constants
from config.scales import *

class Pattern:
    def __init__(self, num, length, lpb, bpm, swing, tracker):
        self.tracker = tracker
        self.num = num
        self.bpm = bpm
        self.master_track = MasterTrack(length, lpb, pattern=self)
        self.midi_tracks = [MidiTrack(i, length, lpb, pattern=self) for i in range(constants.track_count)]
        self.loops = 1
        self.swing = swing
        self.scale = CHROMATIC
        self.tracks = [self.master_track] + self.midi_tracks

        # self.transposition = [0, 0, 0, 0, 0, 0, 0, 0]  # independent transposition per track
        # self.fit_to_scale = [0, 0, 0, 0, 0, 0, 0, 0]  # independent scale per track
        # self.swing = [0, 0, 0, 0, 0, 0, 0, 0]  # independent swing per track

        self.set_swing()

    def synchronise_playheads(self):
        master_track_step_pos = self.master_track.get_step_pos()
        for track in self.midi_tracks:
            ticks = master_track_step_pos * (96 // track.lpb)
            if track.is_reversed:
                ticks += track.ticks_per_step
            if ticks >= track.length_in_ticks:
                ticks = 0
            track.ticks = ticks
            if track.get_current_tick() == 0:
                track.play_step()

    def reverse_tracks(self):
        for track in self.midi_tracks:
            track.reverse()

    def set_swing(self):
        for track in self.tracks:
            if not track.is_master:
                track.swing = self.swing
                track.swing_factor = int((track.swing / track.lpb) * 4)

    def json_serialize(self):
        pass

    def load_from_json(self, data):
        pass
