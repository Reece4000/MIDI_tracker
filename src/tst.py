import random
from pyo import *

pm_list_devices()

s = Server()

# Open all MIDI output devices.
s.setMidiOutputDevice(99)

# Then boot the Server.
s.boot()

# Generates an audio ramp from 36 to 84, from
# which MIDI pitches will be extracted.
pitch = Phasor(freq=11, mul=48, add=36)

# Global variable to count the down and up beats.
count = 0


def midi_event():
    global count
    # Retrieve the value of the pitch audio stream and convert it to an int.
    pit = int(pitch.get())

    # If the count is 0 (down beat), play a louder and longer event, otherwise
    # play a softer and shorter one.
    if count == 0:
        vel = random.randint(90, 110)
        dur = 500
    else:
        vel = random.randint(50, 70)
        dur = 125

    # Increase and wrap the count to generate a 4 beats sequence.
    count = (count + 1) % 4

    print("pitch: %d, velocity: %d, duration: %d" % (pit, vel, dur))

    # The Server's `makenote` method generates a noteon event immediately
    # and the correponding noteoff event after `duration` milliseconds.
    s.makenote(pitch=pit, velocity=vel, duration=dur)


# Generates a MIDI event every 125 milliseconds.
pat = Pattern(midi_event, 0.005).play()

s.gui(locals())