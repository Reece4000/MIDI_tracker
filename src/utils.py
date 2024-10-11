import time
from collections import defaultdict
from typing import Callable, TypeVar, Any
from config.constants import note_base_names, timeline_length, INCREMENTS
# import src.cython.c_utils as c_utils

measured_times = defaultdict(list)
R = TypeVar('R')


def get_polygon_coords(x, y, w, h, opt=0):
    """ widths should be even numbers """
    if opt == 0:  # down
        return tuple(((x, y), (x + w//2, y + h), (x + w, y)))
    elif opt == 1:  # up
        return tuple(((x, y + h), (x + w//2, y), (x + w, y + h)))
    elif opt == 2:  # left
        return tuple(((x + w, y), (x, y + h//2), (x + w, y + h)))
    elif opt == 3:  # right
        return tuple(((x, y), (x + w, y + h//2), (x, y + h)))


def get_increment(increment, val_type):
    if increment == 0:
        return 0
    size = "large" if abs(increment) > 1 else "small"
    return INCREMENTS[val_type][size] if increment > 0 else -INCREMENTS[val_type][size]


def transpose_note(note, scale):
    if note is None or note == -1:
        return note

    scale_degree = note % 12
    if scale[scale_degree] == 1:
        return note
    else:
        for i in range(1, 6):
            if scale[(scale_degree + i) % 12] == 1 and note + i <= 127:
                return note + i
            elif scale[(scale_degree - i) % 12] == 1 and note - i >= 0:
                return note - i

def transpose_to_scale(notes, scale):
    return [transpose_note(note, scale) for note in notes]

def timing_decorator(func):
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        result = func(self, *args, **kwargs)
        elapsed_time = time.time() - start_time

        # Update the mean time
        if func.__name__ not in measured_times:
            measured_times[func.__name__] = (elapsed_time, 1)  # (mean time, count)
        else:
            current_mean, count = measured_times[func.__name__]
            new_count = count + 1
            new_mean = (current_mean * count + elapsed_time) / new_count
            measured_times[func.__name__] = (new_mean, new_count)

        return result

    return wrapper


def midi_to_note(midi_note):
    if midi_note == -1:
        return 'OFF'
    if midi_note is not None:
        octave = (midi_note // 12) - 1
        note_index = midi_note % 12
        note_name = note_base_names[note_index]
        return f"{note_name}{octave}"
    return None


def calculate_timeline_increment(current_value, increment):
    if current_value is None:
        return None if increment < 0 else increment - 1
    elif current_value == 0 and increment < 0:
        return None
    elif current_value > 0 > increment:
        return max(0, current_value + increment)
    else:
        return min(timeline_length, current_value + increment)

"""
def midi_to_note(midi_note):
    return None if midi_note is None else c_utils.midi_to_note(midi_note)
"""


def note_to_midi(note):
    if note == 'OFF':
        return -1
    if note:
        note_name = note[:-1]
        octave = int(note[-1])
        note_index = note_base_names.index(note_name)
        return 12 * (octave + 1) + note_index
    return None


def keep_time(func: Callable[..., R]) -> Callable[..., R]:
    """Decorator to maintain sequencer timing while performing render ops."""
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
        self.tracker.update_sequencer_time()
        return func(self, *args, **kwargs)
    return wrapper


def join_notes(notes: list[int]) -> str:
    base_notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    str_notes = []
    for note in notes:
        if note == -1:
            str_notes.append("OFF")
        else:
            str_notes.append(base_notes[note % 12])
    return ",".join(str_notes)


chord_cache = {}


def chord_id(midi_notes: list[int]) -> list[str]:
    base_notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    chordNotes = []
    for note in midi_notes:
        if note != -1:
            chordNotes.append(base_notes[note % 12])

    if not chordNotes:
        return []

    sorted_notes = tuple(sorted(chordNotes))
    if sorted_notes in chord_cache:
        return chord_cache[sorted_notes]

    # ... logic here

    # Takes in an array called "chordNotes" and returns an array of possible
    # chord names associated with the pitches defined in chordNotes.
    # NOTE: Current version ignores inversions.
    #
    # e.g. ChordID(['C','E','A']) returns ['C Maj6', 'A min']
    #
    # Evan Czako, 10.27.2020.

    notesSharps = ['A', 'A#', 'B', 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#']
    notesFlats = ['A', 'Bb', 'B', 'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab']

    possibleChords = []

    chordNotesIndices = set()
    for note in chordNotes:
        if note in notesSharps:
            chordNotesIndices.add(notesSharps.index(note))
        elif note in notesFlats:
            chordNotesIndices.add(notesFlats.index(note))

    checkList = list(chordNotesIndices)

    ### Power Chord ###
    powerChordSet = {0, 7}

    ### Check Power Chords ###
    for k in range(0, 12):

        tempSet = set([(x + k) % 12 for x in checkList])

        if tempSet == powerChordSet:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 5th")
            break

            ### Major Chords ###
    majSet = {0, 4}
    maj7Set = {0, 4, 11}
    maj9Set = {0, 4, 11, 2}
    maj11Set = {0, 4, 11, 2, 5}
    maj13Set = {0, 4, 11, 2, 5, 9}
    majAdd9Set = {0, 4, 2}
    majAdd11Set = {0, 4, 5}
    maj6Set = {0, 4, 9}
    majAdd9Add11Set = {0, 4, 2, 5}
    sixNineSet = {0, 4, 2, 9}
    majAdd11Add13Set = {0, 4, 5, 9}
    majAdd9Add11Add13Set = {0, 4, 2, 5, 9}
    maj9Add13Set = {0, 4, 11, 2, 9}

    ### Check major chords ###
    for k in range(0, 12):

        tempSet = set([(x + k) % 12 for x in checkList])
        tempSet.discard(7)

        if tempSet == majSet:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M")
        elif tempSet == maj7Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M7")
        elif tempSet == maj9Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M9")
        elif tempSet == maj11Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M11")
        elif tempSet == maj13Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M13")
        elif tempSet == majAdd9Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " MA9")
        elif tempSet == majAdd11Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " MA11")
        elif tempSet == maj6Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M6")
        elif tempSet == majAdd9Add11Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " MA9A11")
        elif tempSet == sixNineSet:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M69")
        elif tempSet == majAdd11Add13Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " MA11A13")
        elif tempSet == majAdd9Add11Add13Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " MA9A11A13")
        elif tempSet == maj9Add13Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M9A13")

    ### Minor Chords ###
    minSet = {0, 3}
    min6Set = {0, 3, 9}
    min7Set = {0, 3, 10}
    min9Set = {0, 3, 10, 2}
    min11Set = {0, 3, 10, 2, 5}
    min13Set = {0, 3, 10, 2, 5, 9}
    minAdd9Set = {0, 3, 2}
    minAdd11Set = {0, 3, 5}
    minAdd9Add11Set = {0, 3, 2, 5}
    min6Add9Set = {0, 3, 2, 9}
    minAdd9Add11Add13Set = {0, 3, 2, 5, 9}
    min7Add11Set = {0, 3, 10, 5}

    ### Check minor chords ###
    for k in range(0, 12):

        tempSet = set([(x + k) % 12 for x in checkList])
        tempSet.discard(7)

        if tempSet == minSet:
            possibleChords.append(notesSharps[(0 - k) % 12] + " m")
        elif tempSet == min6Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " m6")
        elif tempSet == min7Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " m7")
        elif tempSet == min9Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " m9")
        elif tempSet == min11Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " m11")
        elif tempSet == min13Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " m13")
        elif tempSet == minAdd9Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " mA9")
        elif tempSet == minAdd11Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " mA11")
        elif tempSet == minAdd9Add11Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " mA9A11")
        elif tempSet == min6Add9Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " m6A9")
        elif tempSet == minAdd9Add11Add13Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " mA9A11A13")
        elif tempSet == min7Add11Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " m7A11")

    ### Dominant Chords ###
    dom7Set = {0, 4, 10}
    dom9Set = {0, 4, 10, 2}
    dom11Set = {0, 4, 10, 2, 5}
    dom13Set = {0, 4, 10, 2, 5, 9}
    dom7b9Set = {0, 4, 10, 1}
    dom7Sharp9Set = {0, 4, 10, 3}
    dom7b5Set = {0, 4, 10, 6}
    dom7b13Set = {0, 4, 10, 8}
    dom9b5Set = {0, 4, 10, 2, 6}
    alteredSet = {0, 4, 10, 1, 3, 6, 8}

    ### Check dominant chords ###
    for k in range(0, 12):

        tempSet = set([(x + k) % 12 for x in checkList])
        tempSet.discard(7)

        if tempSet == dom7Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 7")
        if tempSet == dom9Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 9")
        if tempSet == dom11Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 11")
        if tempSet == dom13Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 13")
        if tempSet == dom7b9Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 7b9")
        if tempSet == dom7Sharp9Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 7#9")
        if tempSet == dom7b5Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 7b5")
        if tempSet == dom7b13Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 7b13")
        if tempSet == dom9b5Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 9b5")
        if tempSet == alteredSet:
            possibleChords.append(notesSharps[(0 - k) % 12] + " Alt")

    ### Sus Chords ###
    sus4Set = {0, 5}
    sus2Set = {0, 2}
    sus2sus4Set = {0, 2, 5}
    dom7sus4Set = {0, 5, 10}
    dom7sus2Set = {0, 2, 10}
    dom9Sus4Set = {0, 5, 10, 2}
    dom7b9SusSet = {0, 5, 10, 1}
    sus13Set = {0, 10, 2, 5, 9}
    sus13b9Set = {0, 10, 1, 5, 9}
    sus4b9Set = {0, 5, 1}

    ### Check sus chords ###
    for k in range(0, 12):

        tempSet = set([(x + k) % 12 for x in checkList])
        tempSet.discard(7)

        if tempSet == sus4Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " sus4")
        if tempSet == sus2Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " sus2")
        if tempSet == sus2sus4Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " sus2sus4")
        if tempSet == dom7sus4Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 7sus4")
        if tempSet == dom7sus2Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 7sus2")
        if tempSet == dom9Sus4Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 9sus4")
        if tempSet == dom7b9SusSet:
            possibleChords.append(notesSharps[(0 - k) % 12] + " 7b9sus")
        if tempSet == sus13Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " sus13")
        if tempSet == sus13b9Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " sus13b9")
        if tempSet == sus4b9Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " sus4b9")

    ### Dim Chords ###
    dimSet = {0, 3, 6}
    halfDimSet = {0, 3, 6, 10}
    fullDimSet = {0, 3, 6, 9}

    ### Check dim chords ###
    for k in range(0, 12):

        tempSet = set([(x + k) % 12 for x in checkList])

        if tempSet == dimSet:
            possibleChords.append(notesSharps[(0 - k) % 12] + " dm")
        if tempSet == halfDimSet:
            possibleChords.append(notesSharps[(0 - k) % 12] + " hDm")
        if tempSet == fullDimSet:
            possibleChords.append(notesSharps[(0 - k) % 12] + " flDm")

    ### MinMaj Chords ###
    minMajSet = {0, 3, 11}
    minMaj9Set = {0, 3, 11, 2}
    minMaj9b13Set = {0, 3, 11, 2, 8}

    ### Check minMaj chords ###
    for k in range(0, 12):

        tempSet = set([(x + k) % 12 for x in checkList])
        tempSet.discard(7)

        if tempSet == minMajSet:
            possibleChords.append(notesSharps[(0 - k) % 12] + " mM")
        if tempSet == minMaj9Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " mM")
        if tempSet == minMaj9b13Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " mM9b13")

    ### Aug Chords ###
    AugSet = {0, 4, 8}
    Aug7Set = {0, 4, 8, 10}
    AugMaj7Set = {0, 4, 8, 11}

    ### Check aug chords ###
    for k in range(0, 12):

        tempSet = set([(x + k) % 12 for x in checkList])

        if tempSet == AugSet:
            possibleChords.append(notesSharps[(0 - k) % 12] + " Aug")
        if tempSet == Aug7Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " Aug7")
        if tempSet == AugMaj7Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " AugM7")

    ### b5 and #11 Chords ###
    Majb5Set = {0, 4, 6}
    Maj7b5Set = {0, 4, 6, 11}
    Maj9b5Set = {0, 4, 6, 11, 2}
    maj7AddSharp11Set = {0, 4, 7, 11, 6}
    maj9AddSharp11Set = {0, 4, 7, 11, 2, 6}
    maj13Sharp11Set = {0, 4, 7, 11, 2, 6, 9}
    majAddSharp11Set = {0, 4, 7, 6}

    ### Check b5 and #11 chords ###
    for k in range(0, 12):

        tempSet = set([(x + k) % 12 for x in checkList])

        if tempSet == Majb5Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " Mb5")
        if tempSet == Maj7b5Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M7b5")
        if tempSet == Maj9b5Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M9b5")
        elif tempSet == maj7AddSharp11Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M7A#11")
        elif tempSet == maj9AddSharp11Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M9A#11")
        elif tempSet == maj13Sharp11Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " M13#11")
        elif tempSet == majAddSharp11Set:
            possibleChords.append(notesSharps[(0 - k) % 12] + " MA#11")

    chord_cache[sorted_notes] = possibleChords

    return possibleChords