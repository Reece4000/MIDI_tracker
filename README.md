# **Work in progress!**

A tracker style sequencer inspired by Teenage Engineering's OP-Z and the Dirtywave M8. The sequencer aims to prioritise fun and experimentation, while allowing for fast composition and editing.

![image](https://github.com/user-attachments/assets/7e0140f2-c54e-446c-8762-79c7c1915c73)



This is a sequencer only; it does not create sound. A loopback MIDI device such as Tobias Erichsen's **LoopMIDI** is required in order to send MIDI data to an external source https://www.tobias-erichsen.de/software/loopmidi.html


## Features (many not yet implemented):
- Independent length, LPB, swing and scale per track
  
- 4 note polyphony per step
  
- 16 CCs per step
  
- 4 components per step: inspired by the OP-Z and tracker FX-commands, the sequencer will incorporate components that facilitate a departure from deterministic sequencing. Parameterised components will support randomness. These will include:
  - Reverse (reverse the track playhead, starting from the current step)
  - Retrig (retriger the last played note(s), with control over retrig rate and velocity fade-in/out)
  - CC envelopes and LFOs
  - Randomise notes/velocities
  - Hold - pause the track playhead on the current step for a duration of _x_ steps
  - Repeat - repeat the current step _x_ times
  - Probability - assign a probability for the step notes, CCs or components to be played
  - Randomise Velocity - randomise the step's velocity within a range
  - Randomise Notes - randomise the step's notes within a range
  - LPB change - change the lines per beat of the track, starting at the current step
  - Playhead skip - jump the playhead forward or backward by _x_ steps
    
- A master track which allows for control of the MIDI tracks via master components (max 8 per step), such as:
  - Reverse - reverse selected tracks
  - Sync - sync all track playheads to the current master playhead position
  - Transpose - transpose selected tracks by _x_ semitones
  - Scale - change the scale of selected tracks
  - Repeat - repeat the current master step x times
  - Hold - pause all playheads for a duration of _x_ master steps
  - All notes off - stop all notes for selected tracks

- Fully controllable via gamepad

- Patterns and phrases which can be combined to create full tracks, editing features such as copy/paste, cloning, deep cloning
  
- A chord selection tool, similar to pandabot's ChordGun script for REAPER (https://forum.cockos.com/showthread.php?t=213180)
