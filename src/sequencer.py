from threading import Thread, Lock, Event, BoundedSemaphore
from time import perf_counter
import time
from src.tracks import MasterTrack, MidiTrack
from src.midi_handler import MidiHandler
from src.utils import timing_decorator
from config import constants
import random

############# master component ideas #############
# reverse: reverse the playback of chosen tracks
# sync: synchronise the playheads of chosen tracks with the master track
# speedup: gradually increase the lpb of the track from x to y over z steps
# slowdown: gradually decrease the lpb of the track from x to y over z steps
# global transpose: transpose the notes in the track by x semitones
# scale transpose: transpose the notes in the track to a specific scale
# loop: loop the track from x to y z times
# mute: mute chosen tracks

############# step component ideas #############
# speedup track: gradually increase the lpb of the track from x to y over z steps
# slowdown track: gradually decrease the lpb of the track from x to y over z steps
# arppegiate: play the notes in the track in an arpeggiated fashion
# reverse: play the notes in the track in reverse order
# randomize playback: play the notes in the track in a random order
# retrig: retrigger the notes in the track every x ticks, fading vel to y over z ticks
# random note: randomise the note at the current step
# random vel: randomise the vel at the current step
# ramp: ramp pitch, velocity or cc from x to y over z steps
# transpose: transpose the step note by x semitones with conditional probability y
# fill: fill the notes in the track
# skip: skip ahead x steps
# repeat step: repeat the current step x times
# pause on step: pause on the current step for x steps
# probability: set the probability of the step being played


class Clock:
    def __init__(self, bpm, callback):
        self._mutex = Lock()
        self.bpm = bpm
        self.interval = 60.0 / (bpm * 96)
        self.running = Event()
        self.running.set()
        self.callback = callback
        self.thread = Thread(target=self._run)
        self.thread.start()

    def _run(self):
        next_time = perf_counter()
        while self.running.is_set():
            current_time = perf_counter()
            elapsed = current_time - next_time
            if elapsed >= self.interval:
                # print("callback")
                self.callback()
                next_time += self.interval
            else:
                sleep_time = self.interval - elapsed
                time.sleep(sleep_time)

            # check if execution paused:
            elapsed = current_time - next_time
            if elapsed >= self.interval * 24:
                next_time = current_time

    def set_bpm(self, bpm):
        with self._mutex:
            if bpm != self.bpm:
                self.bpm = bpm
                self.interval = 60.0 / (bpm * 96)

    def stop(self):
        self.running.clear()
        self.thread.join()


class Sequencer:
    def __init__(self, tracker):
        self.tracker = tracker
        self.is_playing = False
        self.midi_handler = MidiHandler()
        self.clock = Clock(bpm=self.tracker.cursor_pattern.bpm, callback=self.tick)
        self._tick_mutex = Lock()
        self.ticks = 0

        # self.tracker.event_bus.on("Sequencer parameters updated", self.update_bpm)

    def reset(self):
        pass

    @timing_decorator
    def tick(self):
        with self._tick_mutex:
            self.midi_handler.send_midi_clock()
            if not self.is_playing:
                return
            self.update_track_playheads()
            self.ticks += 1

    def quit(self):
        self.clock.stop()
        self.midi_handler.all_notes_off()
        self.midi_handler.send_midi_stop()
        self.midi_handler.midi_out.close_port()

    def json_serialize(self):
        pass

    def load_from_json(self, data):
        pass

    def update_bpm(self):
        bpm = self.tracker.playing_pattern.bpm
        self.clock.set_bpm(bpm)

    def stop_playback(self):
        self.is_playing = False
        self.ticks = 0
        self.midi_handler.all_notes_off()
        self.midi_handler.send_midi_stop()

    def start_playback(self):
        print('\n########### Starting playback ###########\n')
        for i, track in enumerate(self.tracker.playing_pattern.midi_tracks):
            track.is_reversed = False
        self.midi_handler.send_midi_start()
        self.update_bpm()
        self.reset_track_playheads()
        self.is_playing = True

    def process_master_components(self):
        master_components = self.tracker.playing_pattern.master_track.get_components()

        for component in master_components:
            if component is not None:
                if component[0] == 'REV':
                    self.tracker.playing_pattern.reverse_tracks()
                elif component[0] == 'SNC':
                    self.tracker.playing_pattern.synchronise_playheads(self.midi_handler)

    def print_ticks(self):
        print(f"master ticks: {self.tracker.playing_pattern.master_track.get_current_tick()}",
              f"track ticks: {self.tracker.playing_pattern.midi_tracks[0].get_current_tick()}",
              f"is reversed: {self.tracker.playing_pattern.midi_tracks[0].is_reversed}")

    def update_song_playhead(self):
        next_step = self.tracker.song_playhead + 1
        if next_step < len(self.tracker.song_pool) and self.tracker.song_pool[next_step] is not None:
            self.tracker.song_playhead = next_step
            self.tracker.phrase_playhead = 0

            # handle case where sequencer is playing and no patterns in phrase track
            playing_phrase_num = self.tracker.song_pool[self.tracker.song_playhead]
            playing_pattern_num = self.tracker.phrase_pool[playing_phrase_num][self.tracker.phrase_playhead]
            if playing_pattern_num not in self.tracker.pattern_pool.keys():
                self.tracker.song_playhead = 0
        else:
            self.tracker.song_playhead = 0
            self.tracker.phrase_playhead = 0

    def update_phrase_playhead(self):
        next_step = self.tracker.phrase_playhead + 1
        current_phrase_num = self.tracker.song_pool[self.tracker.song_playhead]
        current_patterns = self.tracker.phrase_pool[current_phrase_num]
        if next_step < len(current_patterns) and current_patterns[next_step] is not None:
            self.tracker.phrase_playhead = next_step
        else:
            self.update_song_playhead()  # Move to next song step if no more patterns in current phrase
        self.update_bpm()

    def update_track_playheads(self):
        ticks = []
        chk_components = False
        if self.tracker.playing_pattern.master_track.tick():
            chk_components = True
            if self.tracker.playing_pattern.master_track.ticks == 0:
                self.update_phrase_playhead()
                self.update_bpm()
                self.reset_track_playheads()
                return

        for track in self.tracker.playing_pattern.midi_tracks:
            ticks.append(track.tick())

        if chk_components:
            self.process_master_components()

        for i, tick in enumerate(ticks):
            if tick:
                self.tracker.playing_pattern.midi_tracks[i].play_step(self.midi_handler)
        return

    def reset_track_playheads(self):
        tracks = self.tracker.playing_pattern.tracks
        for track in tracks:
            track.reset()
        for track in tracks:
            if track.is_master:
                self.process_master_components()
            else:
                track.play_step(self.midi_handler)
