from config import constants, themeing
from config.constants import master_component_mapping
from src.utils import midi_to_note, chord_id, join_notes, timing_decorator
import numpy as np


class Step:
    __slots__ = 'empty', 'type', 'state_changed'

    def __init__(self):
        self.empty = True
        self.type = None
        self.state_changed = True

    def clone(self):
        return self

    def has_data(self):
        return False


class PatternStep:
    def __init__(self):
        self.number = None  # pattern or phrase num
        self.bpm = None
        self.transposition = [0, 0, 0, 0, 0, 0, 0, 0]  # independent transposition per track
        self.repeats = 1  # number of repeats
        self.fit_to_scale = [0, 0, 0, 0, 0, 0, 0, 0]  # independent scale per track
        self.swing = [0, 0, 0, 0, 0, 0, 0, 0]  # independent swing per track


class MidiStep(Step):
    __slots__ = ('notes', 'velocities', 'components',
                 'component_x_vals', 'component_y_vals',
                 'ccs', 'cached_display_text')

    def __init__(self):
        super().__init__()
        self.type = 1
        self.notes = None
        self.velocities = None
        self.components = None
        self.component_x_vals = None
        self.component_y_vals = None
        self.ccs = None
        self.cached_display_text = None

    def flag_state_change(self):
        self.cached_display_text = None
        self.state_changed = True

    def initialise(self):
        self.notes = constants.empty.copy()
        self.velocities = constants.empty.copy()
        self.components = constants.empty.copy()
        self.component_x_vals = constants.empty.copy()
        self.component_y_vals = constants.empty.copy()
        self.ccs = constants.empty_sixteen.copy()
        self.empty = False

    def clone(self):
        new_step = MidiStep()
        new_step.copy_from(self)
        return new_step

    def copy_from(self, other):
        self.empty = other.empty
        if self.empty:
            return

        self.notes = other.notes.copy()
        self.velocities = other.velocities.copy()
        self.components = other.components.copy()
        self.component_x_vals = other.component_x_vals.copy()
        self.component_y_vals = other.component_y_vals.copy()
        self.ccs = other.ccs.copy()

    def add_note(self, index, note, vel):
        if self.empty:
            self.initialise()
        self.notes[index] = note
        self.velocities[index] = vel
        self.flag_state_change()

    def update_note(self, index, note):
        if self.empty:
            self.initialise()
        self.notes[index] = note
        self.flag_state_change()
        return note

    def update_velocity(self, index, vel):
        if self.empty:
            self.initialise()
        self.velocities[index] = vel
        self.flag_state_change()
        return vel

    def update_cc(self, index, cc):
        if self.empty:
            self.initialise()
        self.ccs[index] = cc
        self.flag_state_change()
        return cc

    def update_component(self, index, component):
        if self.empty:
            self.initialise()
        self.components[index] = component
        self.flag_state_change()
        return component

    def clear(self, opt="all"):
        if not self.empty:
            if opt == "all":
                self.empty = True
            elif opt == "notes":
                self.notes = constants.empty.copy()
            elif opt == "velocities":
                self.velocities = constants.empty.copy()
            elif opt == "components":
                self.components = constants.empty.copy()
                self.component_x_vals = constants.empty.copy()
                self.component_y_vals = constants.empty.copy()
            elif opt == "ccs":
                self.ccs = constants.empty_sixteen.copy()
            self.flag_state_change()

    def all_notes_off(self):
        self.flag_state_change()
        self.notes, self.velocities = constants.note_off.copy(), constants.zeroes.copy()

    def has_data(self):
        if self.empty:
            return False

        return (any(note is not None for note in self.notes) or
                any(component is not None for component in self.components))

    @staticmethod
    def transpose_note(note, increment):
        if note is not None and note != -1:
            note = note + increment
            if note < 0:
                note = 0
            elif note > 127:
                note = 127
        return note

    def transpose(self, increment):
        if self.empty:
            return None

        self.flag_state_change()
        self.notes = [self.transpose_note(note, increment) for note in self.notes]

        for n in self.notes:
            if n is not None:
                return n
        return None

    def has_mod(self):
        if self.empty:
            return False

        return (self.components != constants.empty or
                self.ccs != constants.empty_sixteen)

    def json_serialize(self):
        return {
            "notes": self.notes,
            "components": self.components
        }

    def load_from_json(self, data):
        self.notes = data.get('note')

    @staticmethod
    def get_chord_name(notes):
        midi_notes = [n for n in notes if n is not None]
        chord_name = chord_id(midi_notes)
        if not chord_name:
            chord = join_notes(midi_notes)
        else:
            chord = chord_name[0]
        return chord

    # @timing_decorator
    def get_display_text(self):
        if self.empty:
            return [('---', themeing.NOTE_COLOR),
                    ('--',  themeing.VELOCITY_COLOR),
                    ('-',   themeing.STEP_MOD_COLOR)]

        if self.cached_display_text is not None:
            return self.cached_display_text
        notes = [n for n in self.notes if n is not None]
        vels = [v for v in self.velocities if v is not None]
        mod_display = 'M' if self.has_mod() else '-'
        if not notes:
            note_display = '---'
            vel_display = "--"
        elif notes[0] == -1:
            note_display, vel_display = "OFF", "--"
        elif len(notes) == 1:  # second note blank so just one note
            note_display = midi_to_note(notes[0])
            vel_display = vels[0]
        else:
            self.cached_display_text = [(f'{self.get_chord_name(self.notes)}', themeing.NOTE_COLOR)]
            return self.cached_display_text

        note_color = themeing.NOTE_OFF_COLOR if note_display == "OFF" else themeing.NOTE_COLOR
        self.cached_display_text = [(f'{note_display}', note_color),
                                    (f'{vel_display: >3}', themeing.VELOCITY_COLOR),
                                    (f'{mod_display}', themeing.STEP_MOD_COLOR)]

        return self.cached_display_text


class MasterStep(Step):
    __slots__ = 'components', 'component_x_vals', 'component_y_vals', 'component_track_masks'
    def __init__(self):
        super().__init__()
        self.type = 0
        self.components = None
        self.component_x_vals = None
        self.component_y_vals = None
        self.component_track_masks = None

    def initialise(self):
        self.components = constants.empty.copy()
        self.component_x_vals = constants.empty.copy()
        self.component_y_vals = constants.empty.copy()
        self.component_track_masks = [constants.track_mask.copy() for _ in range(4)]
        self.empty = False

    def clear(self):
        self.state_changed = self.empty = True

    def clone(self):
        new_step = MasterStep()
        if not self.empty:
            new_step.components = self.components.copy()
            new_step.component_x_vals = self.component_x_vals.copy()
            new_step.component_y_vals = self.component_y_vals.copy()
            new_step.component_track_masks = self.component_track_masks.copy()
            new_step.empty = False
        return new_step

    def add_component(self, component, index):
        if self.empty:
            self.initialise()  # ensure lists are initialised
        self.components[index] = component
        self.component_x_vals[index] = master_component_mapping[component]["x"]
        self.component_y_vals[index] = master_component_mapping[component]["y"]
        self.state_changed = True

    def remove_component(self, index):
        if not self.empty:
            self.components[index] = None
            self.component_x_vals[index] = None
            self.component_y_vals[index] = None
            self.state_changed = True

    def get_display_text(self):
        if self.empty:
            return []

        display_elements, m = [], constants.master_component_mapping
        for i in range(4):
            c = self.components[i]
            if c is not None:
                step_display = m[c]["step display"]
                color = m[c]["color"]
                display_elements.append([step_display, color])

        return display_elements

    def has_data(self):
        return False if self.empty else self.components != constants.empty

    def json_serialize(self):
        pass

    def load_from_json(self, data):
        pass


EMPTY_MIDI_STEP = MidiStep()
