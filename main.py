import pygame
import constants
import sys
from time import perf_counter
from tracker import Tracker

"""
Functions to add:
- Fade down: with a selected range, fade down the vel of the notes in each track
- Fade up: with a selected range, fade up the vel of the notes in each track
- Fill: with a selected range, fill the notes in each track, harmonic or percussive
- Add notes: allow users to add more than one note or cc to a given step:
    -    this will require a new data structure to hold multiple notes per step
    -    on the tracker, will display as the root note with an asterisk

- Add keyboard shortcut to increase/decrease note/octave of selection

- CTRL and up/ ctrl down should go up one or down one in the phrase sequencer - if no next pattern,
should create a new one
"""


# create a function which integrates with the rendering queue to emit an event when it's time to send a
# 24PPQ midi clock signal


if __name__ == "__main__":
    tracker = Tracker(track_count=constants.track_count, length=constants.track_length)
    tracker.running_loop()
    sys.exit()

