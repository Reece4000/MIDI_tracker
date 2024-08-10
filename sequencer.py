from rtmidi import MidiOut
from tracks import MasterTrack, MidiTrack

# step component ideas:

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


class MidiHandler:
    # need to store last played note for each channel, send note offs etc
    def __init__(self, num_channels):
        self.num_channels = num_channels
        self.midi_scaling = {i: int(i / 0.7874) for i in range(100)}
        self.note_base_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-', 'OFF']
        self.midi_out = MidiOut()
        self.midi_name = self.initialise_midi()
        # store last note played for each channel and pulses since last note
        self.last_notes_played = [[None, None] for _ in range(self.num_channels)]
        self.mutes = [False for _ in range(self.num_channels)]
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
        if self.pulse % 4 == 0:
            self.midi_out.send_message([0xF8])
            for ch in self.last_notes_played:
                if ch[0] is not None:
                    ch[1] += 1

    def send_midi_start(self):
        self.midi_out.send_message([0xFA])

    def send_midi_stop(self):
        self.midi_out.send_message([0xFC])

    def handle_note(self, channel, note, velocity):
        if self.mutes[channel]:
            return
        velocity = self.midi_scaling[velocity]
        midi_note = self.note_to_midi(note) if not isinstance(note, int) else note
        if self.last_notes_played[channel][0] is not None:
            self.note_off(channel, self.last_notes_played[channel][0])
        if midi_note != -1:
            self.note_on(channel, midi_note, velocity)
            self.last_notes_played[channel] = [midi_note, 0]
        else:
            self.last_notes_played[channel] = [None, None]

    def note_on(self, channel, note, velocity):
        self.midi_out.send_message([0x90 + channel, note, velocity])

    def note_off(self, channel, note):
        self.midi_out.send_message([0x80 + channel, note, 0])

    def all_notes_off(self):
        for channel in range(self.num_channels):
            if self.last_notes_played[channel][0] is not None:
                self.note_off(channel, self.last_notes_played[channel][0])


class Sequencer:
    def __init__(self, timeline_length, num_patterns=1024, track_count=8):
        self.midi_handler = MidiHandler(num_channels=track_count)
        self.timeline_length = timeline_length
        self.max_patterns = num_patterns
        self.song_steps = [0] + [None for _ in range(self.timeline_length-1)]
        # -1 is the blank phrase
        self.phrases = {0: [0] + [None for _ in range(self.timeline_length - 1)],
                        -1: [None for _ in range(self.timeline_length)]}
        self.patterns = {0: Pattern(num=0, length=16, lpb=8, bpm=120)}

        self.cursor_pattern = self.playing_pattern = self.patterns[0]
        self.track_count = track_count
        self.master = self.playing_pattern.master_track
        self.cursor_phrase = self.phrases[0]

        self.create_test_content()

        self.pulse_time = 60 / (self.cursor_pattern.bpm * 96)
        self.clock_time = 60 / (self.cursor_pattern.bpm * 24)
        self.ticks = 0
        self.time_since_last_pulse = 0
        self.last_vel = 80
        self.song_playhead_pos = 0
        self.phrase_playhead_pos = 0
        self.pattern_playhead_pos = 0
        self.last_note_played = [None for _ in range(self.track_count)]
        self.pulses_since_last_note = [None for _ in range(self.track_count)]
        self.is_playing = False
        self.follow_playhead = False

        self.last_bpm, self.last_lpb, self.last_length = 120, 16, 64

    def reset(self):
        self.song_steps = [0] + [None for _ in range(self.timeline_length-1)]
        self.phrases = {0: [0] + [None for _ in range(self.timeline_length - 1)],
                        -1: [None for _ in range(self.timeline_length)]}
        self.patterns = {0: Pattern(num=0, length=16, lpb=8, bpm=120)}

        self.cursor_pattern = self.playing_pattern = self.patterns[0]
        self.cursor_phrase = self.phrases[0]
        self.time_since_last_pulse = 0
        self.song_playhead_pos = 0
        self.phrase_playhead_pos = 0
        self.pattern_playhead_pos = 0
        self.last_note_played = [None for _ in range(self.track_count)]
        self.pulses_since_last_note = [None for _ in range(self.track_count)]
        self.is_playing = False
        self.last_bpm, self.last_lpb, self.last_length = 120, 16, 64

    def handle_mute(self, track):
        track.is_muted = not track.is_muted
        if self.cursor_pattern == self.playing_pattern:
            if track.is_muted and self.midi_handler.last_notes_played[track.channel][0] is not None:
                self.midi_handler.note_off(track.channel, self.midi_handler.last_notes_played[track.channel][0])

    def create_test_content(self):
        self.patterns[0].midi_tracks[0].update_step(0, note='C-2', vel=80)

    def quit(self):
        self.midi_handler.all_notes_off()
        self.midi_handler.send_midi_stop()
        self.midi_handler.midi_out.close_port()

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
                    new_pattern = Pattern(num, self.last_length, self.last_lpb, self.last_bpm)
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
            self.patterns[pattern_num] = Pattern(pattern_num, self.last_length, self.last_lpb, self.last_bpm)

    def is_cursor_on_playing_pattern(self, song_cursor, phrase_cursor):
        cursor_pattern_num = self.phrases[self.song_steps[song_cursor]][phrase_cursor]
        if cursor_pattern_num is None:
            return False
        playing_phrase_num = self.song_steps[self.song_playhead_pos]
        playing_pattern_num = self.phrases[playing_phrase_num][self.phrase_playhead_pos]
        if playing_pattern_num in self.patterns.keys():
            return self.patterns[cursor_pattern_num] == self.patterns[playing_pattern_num]
        return False

    def set_playing_pattern_to_cursor(self, phrase_cursor, song_cursor):
        cursor_pattern_num = self.phrases[self.song_steps[song_cursor]][phrase_cursor]
        if cursor_pattern_num is not None and not self.is_cursor_on_playing_pattern(song_cursor, phrase_cursor):
            self.phrase_playhead_pos = phrase_cursor
            self.set_playing_pattern(cursor_pattern_num)

    def set_playing_pattern(self, pattern_num):
        if pattern_num is not None:
            self.playing_pattern = self.patterns[pattern_num]
            self.update_sequencer_params()

    def set_cursor_pattern(self, pattern_num):
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
            self.set_cursor_pattern(self.cursor_phrase[0])
        else:
            self.set_current_phrase(-1)

    def update_phrase_step(self, index, value):
        # don't update if there's no song step
        new_val = self.calculate_increment(self.cursor_phrase[index], value)
        self.cursor_phrase[index] = new_val
        self.set_cursor_pattern(new_val)

    def update_sequencer_params(self):
        playing_phrase_num = self.song_steps[self.song_playhead_pos]
        playing_pattern_num = self.phrases[playing_phrase_num][self.phrase_playhead_pos]
        if playing_pattern_num is not None:
            playing_pattern = self.patterns[playing_pattern_num]
            self.pulse_time = 60 / (playing_pattern.bpm * 96)
            self.playing_pattern = playing_pattern

            if self.follow_playhead:
                self.cursor_pattern = self.playing_pattern
                self.cursor_phrase = self.phrases[playing_phrase_num]
        else:
            self.is_playing = False

    def update_song_playhead(self):
        _next = self.song_playhead_pos + 1
        if _next < len(self.song_steps) and self.song_steps[_next] is not None:
            self.song_playhead_pos = _next
            self.phrase_playhead_pos = 0

            # handle case where sequencer is playing and no patterns in phrase track
            playing_phrase_num = self.song_steps[self.song_playhead_pos]
            playing_pattern_num = self.phrases[playing_phrase_num][self.phrase_playhead_pos]
            if playing_pattern_num not in self.patterns.keys():
                self.song_playhead_pos = 0
        else:
            self.song_playhead_pos = 0
            self.phrase_playhead_pos = 0

    def update_phrase_playhead(self):
        _next = self.phrase_playhead_pos + 1
        current_phrase_num = self.song_steps[self.song_playhead_pos]
        current_patterns = self.phrases[current_phrase_num]
        if _next < len(current_patterns) and current_patterns[_next] is not None:
            self.phrase_playhead_pos = _next
        else:
            self.update_song_playhead()  # Move to next song step if no more patterns in current phrase

        self.update_sequencer_params()

    def update_time(self, current_time, last_update_time):
        self.time_since_last_pulse += (current_time - last_update_time)
        if self.time_since_last_pulse >= self.pulse_time:
            self.tick()
        return current_time

    def sync_playheads(self):
        master_playhead_pos = self.playing_pattern.master_track.playhead_pos
        for track in self.playing_pattern.midi_tracks:
            track.is_reversed = False
            if master_playhead_pos > track.length:
                track.playhead_pos = 0
            else:
                track.playhead_pos = master_playhead_pos

    def stop_playback(self):
        self.is_playing = False
        self.ticks = 0
        self.midi_handler.all_notes_off()
        self.midi_handler.send_midi_stop()

    def start_playback(self):
        print('Starting playback')
        for i, track in enumerate(self.playing_pattern.midi_tracks):
            track.is_reversed = False
        self.is_playing = True
        self.midi_handler.send_midi_start()
        self.update_sequencer_params()
        self.reset_track_playheads()

    def play_track_notes(self):
        for i, track in enumerate(self.playing_pattern.midi_tracks):
            if track.tick():
                track.play_note(self.midi_handler)

    def process_master_components(self):
        master_components = self.playing_pattern.master_track.get_components()
        for component in master_components:
            if component == 'R':
                print('Reversing')
                for track in self.playing_pattern.midi_tracks:
                    track.reverse()
            elif component == 'S':
                self.sync_playheads()

    def update_track_playheads(self):
        master_progressed = self.playing_pattern.master_track.tick()
        if master_progressed:
            if self.playing_pattern.master_track.playhead_pos == 0:
                self.update_phrase_playhead()
                self.update_sequencer_params()
                self.reset_track_playheads()
                return

            self.process_master_components()

        self.play_track_notes()

        print(self.playing_pattern.master_track.get_current_tick(),
              self.playing_pattern.midi_tracks[0].get_current_tick())

        return

    def tick(self):
        self.midi_handler.send_midi_clock()
        self.time_since_last_pulse -= self.pulse_time
        if not self.is_playing:
            return
        self.update_track_playheads()
        self.ticks += 1

    def reset_track_playheads(self):
        for track in self.playing_pattern.tracks:
            track.reset()
        for track in self.playing_pattern.tracks:
            if track.is_master:
                self.process_master_components()
            else:
                track.play_note(self.midi_handler)


class Pattern:
    def __init__(self, num, length, lpb, bpm):
        self.num = num
        self.bpm = bpm
        self.master_track = MasterTrack(length, lpb)
        self.midi_tracks = [MidiTrack(i, length, lpb) for i in range(8)]
        self.tracks = [self.master_track] + self.midi_tracks

    def json_serialize(self):
        pass

    def load_from_json(self, data):
        pass






