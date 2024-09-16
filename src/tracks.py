from config import events
from typing import Union
from src.steps import Step, MidiStep, MasterStep
from src.midi_handler import MidiHandler
from src.utils import transpose_to_scale


class Track:
    def __init__(self, length: int, lpb: int, tracker) -> None:
        self.tracker = tracker
        self.is_master: bool = False
        self.length: int = length
        self.lpb: int = lpb
        self.length_in_ticks: int = (96 // lpb) * length
        self.ticks: int = 0
        self.ticks_per_step: int = 96 // lpb
        self.steps: list = [Step() for _ in range(length)]
        self.swing: int = 12
        self.swing_factor: int = int((self.swing / self.lpb) * 4)
        self.step_pos = self.get_step_pos()

    def update_properties(self, length: int, lpb: int) -> None:
        pos: float = self.ticks / self.ticks_per_step
        self.length = length
        self.lpb = lpb
        self.length_in_ticks = (96 // lpb) * length
        self.ticks_per_step = 96 // lpb
        self.ticks = int(pos * self.ticks_per_step)
        self.swing_factor = int((self.swing / self.lpb) * 4)

    def get_step_pos(self) -> int:
        return self.ticks // self.ticks_per_step

    def reset(self) -> None:
        self.ticks = 0

    def get_current_tick(self) -> int:
        return self.ticks % self.ticks_per_step

    def is_on_downbeat(self) -> bool:
        lpb_div4: int = self.lpb // 4
        if lpb_div4 == 0:
            return True
        sixteenth_pos: int = self.step_pos // lpb_div4
        is_on_downbeat: bool = sixteenth_pos % 2 == 0
        return is_on_downbeat

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

    def adjust_length(self, increment: int) -> None:
        current_len: int = self.length
        min_len: int = 1
        max_len: int = 256
        new_len: int = min(max(min_len, current_len + increment), max_len)

        if new_len > current_len:
            self.extend_steps(new_len)
        self.update_properties(new_len, self.lpb)

    def adjust_lpb(self, increment: int) -> None:
        # Define current LPB, and fixed min/max values
        current_lpb: int = self.lpb
        new_lpb: int = current_lpb

        min_lpb: int = 1
        max_lpb: int = 96

        # Calculate the new LPB based on the increment
        if increment > 0:
            # Moving to the next higher divisor of 96
            for new_lpb in range(current_lpb + 1, max_lpb + 1):
                if 96 % new_lpb == 0:
                    break
        else:
            # Moving to the next lower divisor of 96
            for new_lpb in range(current_lpb - 1, min_lpb - 1, -1):
                if 96 % new_lpb == 0:
                    break

        # Update the properties with the new LPB
        self.update_properties(self.length, new_lpb)


class MidiTrack(Track):
    def __init__(self, channel: int, length: int, lpb: int, tracker) -> None:
        super().__init__(length, lpb, tracker)
        self.last_notes_played: list = [None, None, None, None]
        self.is_muted: bool = False
        self.channel: int = channel
        self.is_reversed: bool = False
        self.steps: list = [MidiStep() for _ in range(length)]
        self.scale = [1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0]  # lets try C minor pentatonic
        # so we have 24 ticks per step at 4 lpb
        # lets set the swing in this way and then divide it as necessary when the lpb changes
        # a max swing of 23

    def reset(self) -> None:
        super().reset()
        self.is_reversed = False

    def handle_mute(self, send_note_offs: bool, midi_handler: MidiHandler):
        self.is_muted = not self.is_muted
        if send_note_offs:
            for note in midi_handler.last_notes_played[self.channel]:
                if note is not None:
                    midi_handler.note_off(self.channel, note)

    def reverse(self) -> None:
        self.is_reversed = not self.is_reversed
        if self.is_reversed:
            self.ticks = (self.ticks - 1) % self.length_in_ticks
        else:
            self.ticks = (self.ticks + 1) % self.length_in_ticks

    def tick(self, increment=None) -> bool:
        increment = 1 if not self.is_reversed else -1
        return super().tick(increment)  # returns true if on new step

    def handle_ccs(self, channel_ccs: list[int], values: list[int], midi_handler: MidiHandler):
        for i, val in enumerate(values):
            cc = channel_ccs[i]
            if val is None or cc is None:
                continue
            try:
                midi_handler.send_cc(self.channel, cc, val)
            except TypeError as e:
                print(e, cc, val, self.channel)

    def handle_notes(self, notes: list[int], velocities: list[int], midi_handler: MidiHandler):
        note_played = False
        if self.scale is not None:
            notes = transpose_to_scale(notes, self.scale)

        for i, note in enumerate(notes):
            vel = velocities[i]
            if note is not None:
                last_played = midi_handler.last_notes_played[self.channel][i]
                if last_played is not None:
                    midi_handler.note_off(self.channel, last_played, i)

                if note != -1:  # not a note off message
                    note_played = True
                    while note in midi_handler.last_notes_played[self.channel]:
                        index = midi_handler.last_notes_played[self.channel].index(note)
                        midi_handler.note_off(self.channel, note, index)

                    midi_handler.note_on(self.channel, note, vel, i)
        if note_played:
            self.tracker.event_bus.publish(events.NOTE_PLAYED, self.channel)

    def play_step(self, channel_ccs: list[int], midi_handler: MidiHandler, step_pos: int = -1) -> None:
        if step_pos == -1:
            step_pos = self.get_step_pos()
        if not self.is_muted:
            self.handle_ccs(channel_ccs, self.steps[step_pos].ccs, midi_handler)
            self.handle_notes(self.steps[step_pos].notes, self.steps[step_pos].velocities, midi_handler)

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
    def __init__(self, length: int, lpb: int, tracker) -> None:
        super().__init__(length, lpb, tracker)
        self.is_master: bool = True
        self.steps: list = [MasterStep() for _ in range(length)]

    def clear_step(self, position: int) -> None:
        self.steps[position]: MasterStep = MasterStep()

    def get_components(self) -> list:
        return self.steps[self.get_step_pos()].components
