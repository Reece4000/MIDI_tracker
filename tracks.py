from steps import Step, MidiStep, MasterStep


class Track:
    def __init__(self, length, lpb):
        self.is_master = False
        self.length = length
        self.lpb = lpb
        self.steps = [Step(i) for i in range(length)]
        self.playhead_pos = 0
        self.prev_playhead_pos = 0
        self.ticks = 0

    def reset(self):
        self.playhead_pos = 0
        self.ticks = 0

    def get_current_tick(self):
        ticks_per_step = 96 // self.lpb
        return self.ticks % ticks_per_step

    def update_playhead(self):
        self.playhead_pos = (self.playhead_pos + 1) % self.length

    def tick(self):
        self.ticks += 1
        ticks_per_step = 96 // self.lpb

        if self.ticks % ticks_per_step == 0:
            self.update_playhead()
            return True
        return False

    def extend_steps(self, new_length):
        if new_length > self.length:
            for i in range(new_length - self.length):
                step = MidiStep(i) if isinstance(self, MidiTrack) else MasterStep(i)
                self.steps.append(step)

    def adjust_length(self, increment):
        current_len, min_len, max_len = self.length, 1, 256
        new_len = min(max(min_len, current_len + increment), max_len)
        if new_len > current_len:
            self.extend_steps(new_len)
        self.length = new_len

    def adjust_lpb(self, increment):
        current_lpb, min_lpb, max_lpb = self.lpb, 1, 32
        new_lpb = min(max(min_lpb, current_lpb + increment), max_lpb)
        self.lpb = new_lpb


class MidiTrack(Track):
    def __init__(self, channel, length, lpb):
        super().__init__(length, lpb)
        self.is_muted = False
        self.channel = channel
        self.is_reversed = False
        self.steps = [MidiStep(i) for i in range(length)]

    def reset(self):
        super().reset()
        self.is_reversed = 0

    def reverse(self):
        self.is_reversed = not self.is_reversed
        if (self.is_reversed and self.playhead_pos == 0) or not self.is_reversed:
            self.update_playhead(-1)
        else:
            self.update_playhead(1)

    def play_note(self, midi_handler):
        note = self.steps[self.playhead_pos].note
        if note is not None and not self.is_muted:
            print(f'Playing note {note} at {self.playhead_pos}, ticks: {self.ticks}')
            vel = self.steps[self.playhead_pos].vel
            midi_handler.handle_note(self.channel, note, vel)

    def update_playhead(self, increment=None):
        if increment is not None:
            self.playhead_pos += increment
        else:
            self.playhead_pos += 1 if not self.is_reversed else -1
        self.playhead_pos %= self.length

    def json_serialize(self):
        pass

    def load_from_json(self, data):
        pass

    def update_step(self, position, note=None, vel=None, pitchbend=None, modwheel=None):
        step = self.steps[position]
        if note is not None:
            step.note = note
        if vel is not None:
            step.vel = vel
        if pitchbend is not None:
            step.pitchbend = pitchbend
        if modwheel is not None:
            step.modwheel = modwheel

    def print_steps(self):
        for i, step in enumerate(self.steps):
            if step.note is not None:
                print(f'{i}: {step.note} {step.vel} {step.pitchbend} {step.modwheel})')

    def clear_step(self, position):
        self.steps[position] = MidiStep(position)


class MasterTrack(Track):
    def __init__(self, length, lpb):
        super().__init__(length, lpb)
        self.is_master = True
        self.steps = [MasterStep(i) for i in range(length)]

    def clear_step(self, position):
        self.steps[position] = MasterStep(position)

    def get_components(self):
        return self.steps[self.playhead_pos].components

    def add_component(self, position, component):
        self.steps[position].add_component(component)

    def remove_component(self, position, component):
        self.steps[position].remove_component(component)
