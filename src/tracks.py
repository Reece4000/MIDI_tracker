from config import events, constants
from config.scales import *
from typing import Union
from src.steps import Step, MidiStep, MasterStep, EMPTY_MIDI_STEP
from src.midi_handler import MidiHandler
from src.utils import transpose_to_scale, transpose_note, get_increment


class Track:
    __slots__ = ('pattern', 'midi_handler', 'event_bus', 'is_master',
                 'length', 'lpb', 'length_in_ticks', 'ticks',
                 'ticks_per_step', 'step_pos', 'steps', 'swing', 'swing_factor')

    def __init__(self, length: int, lpb: int, pattern) -> None:
        self.pattern = pattern
        self.midi_handler: MidiHandler = pattern.tracker.midi_handler
        self.event_bus = pattern.tracker.event_bus
        self.is_master: bool = False
        self.length: int = length
        self.lpb: int = lpb
        self.length_in_ticks: int = (96 // lpb) * length
        self.ticks: int = 0
        self.ticks_per_step: int = 96 // lpb
        self.step_pos = 0
        self.steps: list = [Step() for _ in range(length)]
        self.swing: int = -1
        self.swing_factor = int((self.pattern.swing / self.lpb) * 4)

    def reset(self) -> None:
        # need to flag state change on current playhead step
        self.steps[self.step_pos].state_changed = True
        self.ticks = self.step_pos = 0

    def clone(self):
        pass

    def adjust_channel(self, increment: int) -> None:
        pass

    def adjust_scale(self, increment: int) -> None:
        pass

    def update_properties(self, length: int, lpb: int) -> None:
        pos: float = self.ticks / self.ticks_per_step
        self.length = length
        self.lpb = lpb
        self.length_in_ticks = (96 // lpb) * length
        self.ticks_per_step = 96 // lpb
        self.ticks = int(pos * self.ticks_per_step)
        if self.swing >= 0:
            self.swing_factor = int((self.swing / self.lpb) * 4)
        else:
            self.swing_factor = int((self.pattern.swing / self.lpb) * 4)

    def get_step_pos(self) -> int:
        return self.ticks // self.ticks_per_step

    def get_current_tick(self) -> int:
        return self.ticks % self.ticks_per_step

    def is_on_downbeat(self) -> bool:
        lpb_div4: int = self.lpb // 4
        if lpb_div4 == 0:
            return True
        sixteenth_pos: int = self.step_pos // lpb_div4
        on_downbeat: bool = sixteenth_pos % 2 == 0
        return on_downbeat

    def tick(self, increment: int = 1) -> bool:
        self.ticks += increment
        self.ticks %= self.length_in_ticks

        self.steps[self.step_pos].state_changed = True

        self.step_pos = self.get_step_pos()

        if self.swing == 0 or self.is_on_downbeat():
            on_next_step: bool = self.ticks % self.ticks_per_step == 0
        else:
            on_next_step: bool = self.ticks % self.ticks_per_step == self.swing_factor

        if on_next_step:
            self.steps[self.step_pos].state_changed = True

        return on_next_step

    def insert_steps(self, pos: int, num_steps: int) -> None:
        self.length += num_steps
        new_steps: list[Step] = [(MidiStep() if not self.is_master else MasterStep())
                                 for _ in range(pos, pos + num_steps)]
        self.steps[pos:pos] = new_steps
        for step in self.steps:
            step.state_changed = True
        self.length = len(self.steps)
        self.length_in_ticks = self.length * (96 // self.lpb)

    def remove_steps(self, steps_to_remove: list[int]) -> None:
        for step_index in sorted(steps_to_remove, reverse=True):
            if len(self.steps) <= 1:
                break
            del self.steps[step_index]

        self.length = len(self.steps)
        self.length_in_ticks = self.length * (96 // self.lpb)

    def extend_steps(self, new_length: int) -> None:
        if new_length > self.length:
            for i in range(new_length - self.length):
                self.steps.append(MasterStep() if self.is_master else MidiStep())

    def adjust_swing(self, increment: int) -> None:
        current_swing: int = self.swing
        new_swing: int = min(max(-1, current_swing + increment), 24)
        self.swing = new_swing
        if self.swing >= 0:
            self.swing_factor = int((self.swing / self.lpb) * 4)
        else:
            self.swing_factor = int((self.pattern.swing / self.lpb) * 4)

    def adjust_transpose(self, increment: int) -> None:
        pass

    def adjust_length(self, increment: int) -> None:
        current_len: int = self.length
        min_len: int = 1
        max_len: int = 256
        new_len: int = min(max(min_len, current_len + increment), max_len)

        if new_len > current_len:
            self.extend_steps(new_len)
        self.update_properties(new_len, self.lpb)

    def adjust_lpb(self, increment: int) -> None:
        current_lpb: int = self.lpb
        min_lpb: int = 1
        max_lpb: int = 96
        new_lpb = min(max(min_lpb, current_lpb + increment), max_lpb)

        self.update_properties(self.length, new_lpb)

    def handle_mute(self, send_note_offs: bool) -> None:
        pass

    def handle_solo(self) -> None:
        pass


class MidiTrack(Track):
    __slots__ = ('last_notes_played', 'is_muted', 'is_soloed',
                 'channel', 'is_reversed', 'steps', 'transpose',
                 'scale', 'retrig', 'retrig_state')

    def __init__(self, channel: int, length: int, lpb: int, pattern, steps=None) -> None:
        super().__init__(length, lpb, pattern)
        self.last_notes_played: list = [None, None, None, None]
        self.is_muted: bool = False
        self.is_soloed: bool = False
        self.channel: int = channel
        self.is_reversed: bool = False
        if steps is None:
            self.steps: list = [MidiStep() for _ in range(length)]
        else:
            self.steps = steps
        self.transpose: int = 0
        self.scale = PATTERN
        # so we have 24 ticks per step at 4 lpb
        # lets set the swing in this way and then divide it as necessary when the lpb changes
        # a max swing of 23

        # maybe makes sense to put this in the midi handler ?
        self.retrig: bool = True
        self.retrig_state: list[int] = [1, 0, 60, 80]  # [rate, ticks since last retrig, note, velocity]

    def reset(self) -> None:
        super().reset()
        self.is_reversed = False

    def clone(self):
        new_steps = [step.clone() for step in self.steps]
        new_track = MidiTrack(self.channel, self.length, self.lpb, self.pattern, new_steps)
        new_track.transpose = self.transpose
        new_track.scale = self.scale
        new_track.is_reversed = self.is_reversed
        new_track.swing = self.swing
        new_track.swing_factor = self.swing_factor
        new_track.is_muted = self.is_muted
        new_track.is_soloed = self.is_soloed
        return new_track

    def adjust_channel(self, increment: int) -> None:
        self.midi_handler.all_notes_off(self.channel)
        self.channel = max(0, min(15, self.channel + increment))

    def adjust_scale(self, increment: int) -> None:
        self.scale = min(20, max(-1, self.scale + increment))

    def adjust_transpose(self, increment: int) -> None:
        current_transpose: int = self.transpose
        new_transpose: int = min(max(-48, current_transpose + increment), 48)
        self.transpose = new_transpose

    def handle_mute(self, send_note_offs: bool):
        self.is_muted = not self.is_muted
        if send_note_offs:
            self.midi_handler.all_notes_off(self.channel)

    def reverse(self) -> None:
        self.is_reversed = not self.is_reversed
        if self.is_reversed:
            self.ticks = (self.ticks - 1) % self.length_in_ticks
        else:
            self.ticks = (self.ticks + 1) % self.length_in_ticks

    def tick(self, increment=None) -> bool:
        increment = 1 if not self.is_reversed else -1
        on_next_step = super().tick(increment)  # returns true if on new step

        """
        if self.retrig:
            self.retrig_state[1] += 1
            if self.retrig_state[1] >= self.retrig_state[0]:
                self.retrig_state[1] = 0
                self.retrig_state[3] -= 2
                if self.retrig_state[3] < 0:
                    self.retrig_state[3] = 80
                else:
                    midi_handler = self.tracker.midi_handler
                    note = self.retrig_state[2]
                    vel = self.retrig_state[3]
                    last_played = midi_handler.last_notes_played[self.channel][0]
                    if last_played is not None:
                        midi_handler.note_off(self.channel, last_played, 0)

                    if note != -1:  # not a note off message
                        while note in midi_handler.last_notes_played[self.channel]:
                            index = midi_handler.last_notes_played[self.channel].index(note)
                            midi_handler.note_off(self.channel, note, index)

                        midi_handler.note_on(self.channel, note, vel, 0)
        """

        return on_next_step

    def handle_ccs(self, values: list[int]) -> None:
        channel_ccs = self.pattern.tracker.channel_ccs[self.channel]
        for i, val in enumerate(values):
            cc = channel_ccs[i]
            if val is None or cc is None:
                continue
            try:
                self.midi_handler.send_cc(self.channel, cc, val)
            except TypeError as e:
                print(e, cc, val, self.channel)

    def handle_notes(self, notes: list[int], velocities: list[int]) -> None:
        note_played = False
        scale_key = self.pattern.scale if self.scale == PATTERN else self.scale
        scale = SCALES[scale_key]["indices"]

        for i in range(constants.max_polyphony):
            note = notes[i]
            if note is not None:
                last_played = self.midi_handler.last_notes_played[self.channel][i]
                if last_played is not None:
                    self.midi_handler.note_off(self.channel, last_played, i)

                if note != -1:  # not a note off message
                    note_played = True
                    # track transpose applied pre-quantization, pattern transpose applied after
                    if scale != CHROMATIC:
                        note = transpose_note(note + self.transpose, scale) + self.pattern.transpose
                    else:
                        note += self.transpose + self.pattern.transpose

                    note = min(max(0, note), 127)

                    while note in self.midi_handler.last_notes_played[self.channel]:
                        index = self.midi_handler.last_notes_played[self.channel].index(note)
                        self.midi_handler.note_off(self.channel, note, index)

                    self.midi_handler.note_on(self.channel, note, velocities[i], i)
        if note_played:
            self.event_bus.publish(events.NOTE_PLAYED, self.channel)

    def play_step(self, step_pos: int = -1) -> None:
        if step_pos == -1:
            step_pos = self.get_step_pos()
        if not self.is_muted and not self.steps[step_pos].empty:
            self.handle_ccs(self.steps[step_pos].ccs)
            self.handle_notes(self.steps[step_pos].notes, self.steps[step_pos].velocities)

    def json_serialize(self):
        pass

    def load_from_json(self, data):
        pass

    def update_step(self, position: int, notes: list, velocities: list) -> None:
        step: MidiStep = self.steps[position]
        step.notes = notes
        step.velocities = velocities

    def clear_step(self, position) -> None:
        self.steps[position]: MidiStep = MidiStep()


class MasterTrack(Track):
    __slots__ = 'steps'

    def __init__(self, length: int, lpb: int, pattern, steps=None) -> None:
        super().__init__(length, lpb, pattern)
        self.is_master: bool = True
        if steps is None:
            self.steps: list = [MasterStep() for _ in range(length)]
        else:
            self.steps = steps

    def clone(self):
        new_steps = [step.clone() for step in self.steps]
        return MasterTrack(self.length, self.lpb, self.pattern, new_steps)

    def clear_step(self, position: int) -> None:
        self.steps[position]: MasterStep = MasterStep()

    def get_current_step(self) -> MasterStep:
        return self.steps[self.step_pos]
