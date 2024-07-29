from sequencer_components import Track





class TimelineStep:
    def __init__(self, pattern_num="---"):
        self.pattern_num = pattern_num
   
        
class TimelineTrack:
    def __init__(self, length):
        self.steps = [TimelineStep() for _ in range(length)]
        self.length = length

    def update_step(self, position, pattern_num=None):
        step = self.steps[position]
        if pattern_num is not None:
            step.pattern_num = str(pattern_num)

    def clear_step(self, position):
        self.steps[position] = TimelineStep()

    def __getitem__(self, position):
        return self.steps[position]