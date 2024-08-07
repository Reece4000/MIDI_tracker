from rtmidi import MidiOut
from time import perf_counter
import sys


class MidiHandler:
    def __init__(self, num_channels):
        self.num_channels = num_channels
        self.midi_scaling = {i: int(i / 0.7874) for i in range(100)}
        self.note_base_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-', 'OFF']
        self.midi_out = MidiOut()
        self.pulse = 0

    def initialise_midi(self):
        available_ports = self.midi_out.get_ports()
        if available_ports:
            for index, port in enumerate(available_ports):
                if "Internal MIDI" in port:
                    self.midi_out.open_port(index)
                    return f"{port} ({index})"
        return None

    def note_to_midi(self, note):
        if note == 'OFF':
            return -1
        if note:
            note_name = note[:-1]
            octave = int(note[-1])
            note_index = self.note_base_names.index(note_name)
            return 12 * (octave + 1) + note_index
        return None

    def send_midi_clock(self):
        self.pulse += 1
        if self.pulse == 4:
            self.midi_out.send_message([0xF8])
            self.pulse = 0

    def send_midi_start(self):
        self.midi_out.send_message([0xFA])

    def send_midi_stop(self):
        self.midi_out.send_message([0xFC])

    def note_on(self, channel, note, velocity):
        velocity = self.midi_scaling[velocity]
        midi_note = self.note_to_midi(note) if not isinstance(note, int) else note
        if midi_note != -1:
            self.midi_out.send_message([0x90 + channel, midi_note, velocity])

    def note_off(self, channel, note):
        midi_note = self.note_to_midi(note) if not isinstance(note, int) else note
        if midi_note != -1:
            self.midi_out.send_message([0x80 + channel, midi_note, 0])

    def all_notes_off(self):
        for channel in range(self.num_channels):
            self.midi_out.send_message([0xB0 + channel, 123, 0])


class Sequencer:
    def __init__(self, timeline_length, num_patterns=1024, track_count=8):
        self.track_count = track_count
        self.timeline_length = timeline_length
        self.max_patterns = num_patterns
        self.song_steps = [0] + [None for _ in range(self.timeline_length-1)]
        # -1 is the blank phrase
        self.phrases = {0: [0] + [None for _ in range(self.timeline_length - 1)],
                        -1: [None for _ in range(self.timeline_length)]}
        self.patterns = {0: Pattern(num=0, track_count=self.track_count, length=64, lpb=16, bpm=120)}

        self.cursor_pattern = self.playing_pattern = self.patterns[0]
        self.cursor_phrase = self.phrases[0]

        self.pulse_time = 60 / (self.cursor_pattern.bpm * 96)
        self.step_time = 60 / (self.cursor_pattern.bpm * self.cursor_pattern.lpb)
        self.clock_time = 60 / (self.cursor_pattern.bpm * 24)
        self.time_since_last_step = 0
        self.time_since_last_pulse = 0
        self.last_vel = 80
        self.song_playhead_pos = 0
        self.phrase_playhead_pos = 0
        self.pattern_playhead_pos = 0
        self.last_note_played = [None for _ in range(self.track_count)]
        self.steps_since_last_note = [None for _ in range(self.track_count)]
        self.is_playing = False
        self.follow_playhead = False

        self.last_bpm, self.last_lpb, self.last_length = 120, 16, 64

    def reset(self):
        self.song_steps = [0] + [None for _ in range(self.timeline_length-1)]
        self.phrases = {0: [0] + [None for _ in range(self.timeline_length - 1)],
                        -1: [None for _ in range(self.timeline_length)]}
        self.patterns = {0: Pattern(num=0, track_count=self.track_count, length=64, lpb=16, bpm=120)}

        self.cursor_pattern = self.playing_pattern = self.patterns[0]
        self.cursor_phrase = self.phrases[0]

        self.step_time = 60 / (self.cursor_pattern.bpm * self.cursor_pattern.lpb)
        self.time_since_last_step = 0
        self.song_playhead_pos = 0
        self.phrase_playhead_pos = 0
        self.pattern_playhead_pos = 0
        self.last_note_played = [None for _ in range(self.track_count)]
        self.steps_since_last_note = [None for _ in range(self.track_count)]
        self.is_playing = False
        self.last_bpm, self.last_lpb, self.last_length = 120, 16, 64

    def json_serialize(self):
        return {
            "song_steps": self.song_steps,
            "phrases": self.phrases,
            "patterns": {num: pattern.json_serialize() for num, pattern in self.patterns.items()},
        }

    def load_from_json(self, data):
        self.reset()
        self.song_steps = data['song_steps']
        self.phrases = {}
        for num, phrase_data in data['phrases'].items():
            if num.isdigit():
                self.phrases[int(num)] = phrase_data

        self.patterns = {}
        for num, pattern_data in data['patterns'].items():
            if num.isdigit():
                num = int(num)
                if num in self.patterns:
                    self.patterns[num].load_from_json(pattern_data)
                else:
                    new_pattern = Pattern(num, self.track_count, self.last_length,
                                          self.last_lpb, self.last_bpm)
                    new_pattern.load_from_json(pattern_data)
                    self.patterns[num] = new_pattern

        self.timeline_length = len(self.song_steps)
        self.cursor_pattern = self.playing_pattern = self.patterns[0]
        self.cursor_phrase = self.phrases[0]

    def calculate_increment(self, current_value, increment):
        if current_value is None and increment < 0:
            return None
        elif current_value is None and increment > 0:
            return increment-1
        elif current_value == 0 and increment < 0:
            return None
        elif current_value > 0 > increment:
            return max(0, current_value + increment)
        else:
            return min(self.max_patterns, current_value + increment)

    def add_pattern(self, pattern_num):
        if pattern_num not in self.patterns.keys():
            self.patterns[pattern_num] = Pattern(pattern_num, self.track_count, self.last_length,
                                                 self.last_lpb, self.last_bpm)

    def set_current_pattern(self, pattern_num):
        self.cursor_pattern = None
        if pattern_num is not None:
            self.add_pattern(pattern_num)
            self.cursor_pattern = self.patterns[pattern_num]

    def add_phrase(self, phrase_num):
        if phrase_num not in self.phrases.keys():
            self.phrases[phrase_num] = [None for _ in range(self.timeline_length)]

    def set_current_phrase(self, phrase_num):
        self.add_phrase(phrase_num)
        self.cursor_phrase = self.phrases[phrase_num]
        if self.cursor_phrase[0] is not None:
            self.cursor_pattern = self.patterns[self.cursor_phrase[0]]
        else:
            self.cursor_pattern = None

    def update_song_step(self, index, value):
        new_val = self.calculate_increment(self.song_steps[index], value)
        self.song_steps[index] = new_val
        if new_val is not None:
            self.add_phrase(new_val)
            self.set_current_phrase(new_val)
            self.set_current_pattern(self.cursor_phrase[0])
        else:
            self.set_current_phrase(-1)

    def update_phrase_step(self, index, value):
        # don't update if there's no song step
        new_val = self.calculate_increment(self.cursor_phrase[index], value)
        self.cursor_phrase[index] = new_val
        self.set_current_pattern(new_val)

    def is_cursor_on_playing_pattern(self, song_cursor, phrase_cursor):
        cursor_phrase_num = self.song_steps[song_cursor]
        cursor_pattern_num = self.phrases[cursor_phrase_num][phrase_cursor]
        if cursor_pattern_num is None:
            return False

        cursor_pattern = self.patterns[cursor_pattern_num]

        playing_phrase_num = self.song_steps[self.song_playhead_pos]
        playing_pattern_num = self.phrases[playing_phrase_num][self.phrase_playhead_pos]
        if playing_pattern_num in self.patterns.keys():
            return cursor_pattern == self.patterns[playing_pattern_num]

        return False

    def update_sequencer_params(self):
        playing_phrase_num = self.song_steps[self.song_playhead_pos]
        playing_pattern_num = self.phrases[playing_phrase_num][self.phrase_playhead_pos]
        playing_pattern = self.patterns[playing_pattern_num]

        self.step_time = 60 / (playing_pattern.bpm * playing_pattern.lpb)
        self.pulse_time = 60 / (playing_pattern.bpm * 96)
        self.playing_pattern = playing_pattern

        if self.follow_playhead:
            self.cursor_pattern = self.playing_pattern
            self.cursor_phrase = self.phrases[playing_phrase_num]

    def update_song_playhead(self):
        _next = self.song_playhead_pos + 1
        if _next < len(self.song_steps) and self.song_steps[_next] is not None:
            self.song_playhead_pos = _next
            self.phrase_playhead_pos = 0
            self.pattern_playhead_pos = 0

            # handle case where sequencer is playing and no patterns in phrase track
            playing_phrase_num = self.song_steps[self.song_playhead_pos]
            playing_pattern_num = self.phrases[playing_phrase_num][self.phrase_playhead_pos]
            if playing_pattern_num not in self.patterns.keys():
                self.song_playhead_pos = 0

            self.update_sequencer_params()
        else:
            self.song_playhead_pos = 0
            self.phrase_playhead_pos = 0
            self.pattern_playhead_pos = 0
            self.update_sequencer_params()

    def update_phrase_playhead(self):
        _next = self.phrase_playhead_pos + 1
        current_phrase_num = self.song_steps[self.song_playhead_pos]
        current_patterns = self.phrases[current_phrase_num]

        if _next < len(current_patterns) and current_patterns[_next] is not None:
            self.phrase_playhead_pos = _next
            self.pattern_playhead_pos = 0
            self.update_sequencer_params()
        else:
            self.update_song_playhead()  # Move to next song step if no more patterns in current phrase

    def update_pattern_playhead(self):
        if self.pattern_playhead_pos + 1 < self.playing_pattern.length:
            self.pattern_playhead_pos += 1
        else:
            self.update_phrase_playhead()


class Pattern:
    def __init__(self, num, track_count, length, lpb, bpm):
        self.num = num
        self.length = length
        self.tracks = [Track(length) for _ in range(track_count)]
        self.lpb = lpb
        self.bpm = bpm

    def json_serialize(self):
        return {
            "num": self.num,
            "length": self.length,
            "tracks": [track.json_serialize() for track in self.tracks],
            "lpb": self.lpb,
            "bpm": self.bpm
        }

    def load_from_json(self, data):
        self.num = data['num']
        self.length = data['length']
        self.lpb = data['lpb']
        self.bpm = data['bpm']
        # print(data['tracks'])  # should show list of dictionaries
        self.tracks = [Track(self.length) for _ in range(len(data.get('tracks', [])))]
        for i, track_data in enumerate(data.get('tracks', [])):
            self.tracks[i].load_from_json(track_data)


class Track:
    def __init__(self, length):
        self.length = length
        self.steps = [Step() for _ in range(length)]

    def json_serialize(self):
        serialized_steps = {str(i): step.json_serialize() for i, step in enumerate(self.steps) if step.has_data()}
        return {"length": self.length, "steps": serialized_steps}

    def load_from_json(self, data):
        # Check if data is the expected dictionary with 'length' and 'steps'
        if isinstance(data, dict) and 'length' in data and 'steps' in data:
            self.length = data['length']
            steps_data = data['steps']
            self.steps = [Step() for _ in range(self.length)]  # reinitialize steps based on tr length
            for index, step_data in steps_data.items():
                self.steps[int(index)].load_from_json(step_data)
        elif isinstance(data, dict) and 'steps' not in data:
            max_index = max((int(index) for index in data.keys()), default=-1)
            self.length = max_index + 1  # Update length to accommodate all steps
            self.steps = [Step() for _ in range(self.length)]
            for index, step_data in data.items():
                if isinstance(step_data, dict):
                    self.steps[int(index)].load_from_json(step_data)
        else:
            raise TypeError(f"Unexpected data type or format. Data: {data}")

    def update_step(self, position, note=None, vel=None, pitchbend=None, modwheel=None):
        step = self.steps[position]
        if note is not None:
            step.note = note
        if vel is not None:
            step.vel = vel
        if pitchbend is not None:
            step.pitchbend = pitchbend
        if modwheel is not None:
            step.modwheel = modwheel

    def print_steps(self):
        for i, step in enumerate(self.steps):
            if step.note is not None:
                print(f'{i}: {step.note} {step.vel} {step.pitchbend} {step.modwheel})')

    def extend_steps(self, new_length):
        if new_length > self.length:
            self.steps.extend([Step() for _ in range(new_length - self.length)])
            self.length = new_length

    def clear_step(self, position):
        self.steps[position] = Step()


class Step:
    def __init__(self, note=None, vel=None, pitchbend=None, modwheel=None):
        self.note = note
        self.vel = vel
        self.pitchbend = pitchbend
        self.modwheel = modwheel

    def has_data(self):
        return any([self.note, self.vel, self.pitchbend, self.modwheel])

    def json_serialize(self):
        return {
            "note": self.note,
            "vel": self.vel,
            "pitchbend": self.pitchbend,
            "modwheel": self.modwheel
        }

    def load_from_json(self, data):
        self.note = data.get('note')
        self.vel = data.get('vel')
        self.pitchbend = data.get('pitchbend')
        self.modwheel = data.get('modwheel')

    def components(self):
        if self.note == 'OFF':
            return [(f'OFF', (255, 150, 150))]
        else:
            note = '- -' if self.note is None else self.note
            vel = '--' if self.vel is None else self.vel
            pitchbend = '00' if self.pitchbend is None else self.pitchbend
            modwheel = '00' if self.modwheel is None else self.modwheel

            return [(f'{note}', (100, 255, 100)),
                    (f'{vel:0>2}', (255, 150, 150)),
                    (f'{pitchbend:0>2}', (200, 100, 200)),
                    (f'{modwheel:0>2}', (100, 200, 200))]


