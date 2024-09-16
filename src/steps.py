from config import constants
from src.utils import midi_to_note, chord_id, join_notes, timing_decorator


class Step:
    def __init__(self):
        self.type = None
        self.state_changed = True

    def has_data(self):
        return False


class PhraseStep:
    def __init__(self):
        self.number = None  # pattern or phrase num
        self.bpm = None
        self.transposition = [0, 0, 0, 0, 0, 0, 0, 0]  # independent transposition per track
        self.repeats = 1  # number of repeats
        self.fit_to_scale = [0, 0, 0, 0, 0, 0, 0, 0]  # independent scale per track
        self.swing = [0, 0, 0, 0, 0, 0, 0, 0]  # independent swing per track


class MidiStep(Step):
    def __init__(self):
        super().__init__()
        self.type = 'midi'
        self.notes = [None, None, None, None]
        self.velocities = [None, None, None, None]
        self.components = [None, None, None, None]
        self.ccs = [None, None, None, None, None, None, None, None]
        self.cached_display_text = None

    def flag_state_change(self):
        self.cached_display_text = None
        self.state_changed = True

    def add_note(self, index, note, vel):
        self.notes[index] = note
        self.velocities[index] = vel
        self.flag_state_change()

    def update_note(self, index, note):
        self.notes[index] = note
        self.flag_state_change()
        return note

    def update_velocity(self, index, vel):
        self.velocities[index] = vel
        self.flag_state_change()
        return vel

    def update_cc(self, index, cc):
        self.ccs[index] = cc
        self.flag_state_change()
        return cc

    def update_component(self, index, component):
        self.components[index] = component
        self.flag_state_change()
        return component

    def clear(self, opt="all"):
        if opt == "all" or opt == "notes":
            self.notes = [None, None, None, None]
        if opt == "all" or opt == "notes":
            self.velocities = [None, None, None, None]
        if opt == "all" or opt == "components":
            self.components = [None, None, None, None]
        if opt == "all" or opt == "ccs":
            self.ccs = [None, None, None, None, None, None, None, None]
        self.flag_state_change()

    def all_notes_off(self):
        self.flag_state_change()
        self.notes, self.velocities = [-1, -1, -1, -1], [0, 0, 0, 0]

    def has_data(self):
        return any(note is not None for note in self.notes) or any(
            component is not None for component in self.components)

    def transpose(self, increment):
        self.flag_state_change()
        self.notes = [note + increment if (note is not None and note != -1)
                      else note for note in self.notes]

        for n in self.notes:
            if n is not None:
                return n
        return None

    def has_mod(self):
        return (self.components != [None, None, None, None] or
                self.ccs != [None, None, None, None, None, None, None, None])

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
            self.cached_display_text = [(f'{self.get_chord_name(self.notes)}', (100, 255, 100))]
            return self.cached_display_text

        self.cached_display_text = [(f'{note_display}', (100, 255, 100)),
                                    (f'{vel_display: >3}', (255, 150, 150)),
                                    (f'{mod_display}', (150, 210, 255))]

        return self.cached_display_text


class MasterStep(Step):
    def __init__(self):
        super().__init__()
        self.type = 'master'
        self.components = [None, None, None, None]

    def clear(self):
        self.components = [None, None, None, None]

    def add_component(self, component):
        for i in range(4):
            if self.components[i] is None:
                self.components[i] = component
                break

    def remove_component(self, component):
        self.components.remove(component)

    def get_display_text(self):
        return [[constants.master_component_mapping[c[0]]['Abbreviation'],
                 constants.master_component_mapping[c[0]]['Color']] for c in self.components if c is not None]

    def has_data(self):
        return self.components != []

    def json_serialize(self):
        pass

    def load_from_json(self, data):
        pass
