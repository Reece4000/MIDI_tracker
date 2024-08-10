
class Step:
    def __init__(self, index):
        self.index = index
        self.type = None

    def has_data(self):
        return False


class MidiStep(Step):
    def __init__(self, index, note=None, vel=None, pitchbend=None, modwheel=None):
        super().__init__(index)
        self.type = 'midi'
        self.note = note
        self.vel = vel
        self.ccs = []
        self.pitchbend = pitchbend
        self.modwheel = modwheel

    def has_data(self):
        return any([self.note, self.vel, self.pitchbend, self.modwheel])

    def has_mod(self):
        return any([self.pitchbend, self.modwheel, (self.ccs != [])])

    def json_serialize(self):
        return {
            "note": self.note,
            "vel": self.vel,
            "pitchbend": self.pitchbend,
            "modwheel": self.modwheel
        }

    def load_from_json(self, data):
        self.note = data.get('note')
        self.vel = data.get('vel')
        self.pitchbend = data.get('pitchbend')
        self.modwheel = data.get('modwheel')

    def get_visible_components(self):
        if self.note == 'OFF':
            return [(f'OFF', (255, 150, 150))]
        else:
            note = '---' if self.note is None else self.note
            vel = '--' if self.vel is None else self.vel
            mod = 'M' if self.has_mod() else '--'
            # pitchbend = '00' if self.pitchbend is None else self.pitchbend
            # modwheel = '00' if self.modwheel is None else self.modwheel

            return [(f'{note}', (100, 255, 100)),
                    (f'{vel:0>2}', (255, 150, 150)),
                    (f'{mod}', (150, 210, 255))]


class MasterStep(Step):
    def __init__(self, index, components=None):
        super().__init__(index)
        self.type = 'master'
        self.components = components if components is not None else []

    def add_component(self, component):
        if len(self.components) < 6:
            self.components.append(component)

    def remove_component(self, component):
        self.components.remove(component)

    def get_visible_components(self):
        colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255),
                  (255, 255, 100), (255, 100, 255), (100, 255, 255)]
        components = []
        for i in range(6):
            if i < len(self.components):
                components.append((f'{self.components[i]}', colors[i]))
            else:
                components.append(('', colors[i]))
        return components

    def has_data(self):
        return self.components != []

    def json_serialize(self):
        return {f'component_{i}': component for i, component in enumerate(self.components)}

    def load_from_json(self, data):
        for key, value in data.items():
            self.components.append(value)
