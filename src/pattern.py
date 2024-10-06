from src.tracks import MasterTrack, MidiTrack
from config import constants
from config.scales import *
import copy

class Pattern:
    def __init__(self, num, length, lpb, bpm, swing, tracker, master_track=None, midi_tracks=None):
        self.tracker = tracker
        self.num = num
        self.bpm = bpm
        self.swing = swing
        self.scale = CHROMATIC
        self.transpose = 0
        self.loops = 1
        if master_track is None:
            self.master_track = MasterTrack(length, lpb, pattern=self)
        else:
            self.master_track = master_track
            self.master_track.pattern = self
        if midi_tracks is None:
            self.midi_tracks = [MidiTrack(i, length, lpb, pattern=self) for i in range(constants.track_count)]
        else:
            self.midi_tracks = midi_tracks
            for track in self.midi_tracks:
                track.pattern = self
        self.tracks = [self.master_track] + self.midi_tracks

        # self.transposition = [0, 0, 0, 0, 0, 0, 0, 0]  # independent transposition per track
        # self.fit_to_scale = [0, 0, 0, 0, 0, 0, 0, 0]  # independent scale per track
        # self.swing = [0, 0, 0, 0, 0, 0, 0, 0]  # independent swing per track

    def clone(self, new_num):
        master_track = self.master_track.clone()
        midi_tracks = [track.clone() for track in self.midi_tracks]
        new_pattern = Pattern(new_num, master_track.length, master_track.lpb, self.bpm,
                              self.swing, self.tracker, master_track, midi_tracks)
        new_pattern.transpose = self.transpose
        new_pattern.scale = self.scale
        new_pattern.loops = self.loops
        return new_pattern

    def adjust_swing(self, increment: int) -> None:
        current_swing: int = self.swing
        new_swing: int = min(max(-1, current_swing + increment), 24)
        self.swing = new_swing

    def adjust_transpose(self, increment: int) -> None:
        current_transpose: int = self.transpose
        new_transpose: int = min(max(-48, current_transpose + increment), 48)
        self.transpose = new_transpose

    def adjust_scale(self, increment: int) -> None:
        self.scale = min(20, max(0, self.scale + increment))

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

    def json_serialize(self):
        pass

    def load_from_json(self, data):
        pass
