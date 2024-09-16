from rtmidi import MidiOut
from rtmidi.midiconstants import CONTROL_CHANGE, NOTE_ON, NOTE_OFF
from rtmidi.midiconstants import TIMING_CLOCK, SONG_START, SONG_STOP
from src.utils import timing_decorator
from config import constants


class MidiHandler:
    # need to store last played note for each channel, send note offs etc
    def __init__(self):
        # self.midi_scaling = {i: int(i / 0.7874) for i in range(100)}
        self.note_base_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 
                                'G-', 'G#', 'A-', 'A#', 'B-', 'OFF']
        self.midi_out = MidiOut()
        self.midi_name = self.initialise_midi()
        self.last_notes_played = [[None, None, None, None] for _ in range(16)]
        self.pulse = 0

    def initialise_midi(self):
        available_ports = self.midi_out.get_ports()
        if available_ports:
            for index, port in enumerate(available_ports):
                if "Internal MIDI" in port:
                    self.midi_out.open_port(index)
                    return f"{port} ({index})"
        return None

    @timing_decorator
    def send_midi_clock(self):
        self.pulse += 1
        if not self.pulse % 4:
            self.midi_out.send_message([TIMING_CLOCK])

    def send_midi_start(self):
        self.midi_out.send_message([SONG_START])

    def send_midi_stop(self):
        self.midi_out.send_message([SONG_STOP])

    def send_cc(self, channel, control, value):
        self.midi_out.send_message([CONTROL_CHANGE | channel, control, value])

    def note_on(self, channel, note, velocity, index):
        self.midi_out.send_message([NOTE_ON + channel, note, velocity])
        self.last_notes_played[channel][index] = note

    def note_off(self, channel, note, index):
        self.midi_out.send_message([NOTE_OFF + channel, note, 0])
        self.last_notes_played[channel][index] = None

    def all_notes_off(self, channel=-1):
        for ch in range(constants.track_count):
            if ch == channel or channel == -1:
                for i, note in enumerate(self.last_notes_played[ch]):
                    if note is not None:
                        self.note_off(ch, note, i)
                        self.last_notes_played[ch][i] = None
