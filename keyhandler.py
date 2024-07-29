import pygame




class KeyHandler:
    def __init__(self, tracker, ):
        self.tracker = tracker
        self.mods = {
            "ctrl_alt": False,
            "ctrl_shift": False,
            "ctrl": False,
            "shift": False,
            "alt": False
        }
        self.note_mapping = {
            pygame.K_z: "C-3", pygame.K_s: "C#3", pygame.K_x: "D-3", pygame.K_d: "D#3", pygame.K_c: "E-3",
            pygame.K_v: "F-3", pygame.K_g: "F#3", pygame.K_b: "G-3", pygame.K_h: "G#3", pygame.K_n: "A-3",
            pygame.K_j: "A#3", pygame.K_m: "B-3", pygame.K_q: "C-4", pygame.K_2: "C#4", pygame.K_w: "D-4",
            pygame.K_3: "D#4", pygame.K_e: "E-4", pygame.K_r: "F-4", pygame.K_5: "F#4", pygame.K_t: "G-4",
            pygame.K_6: "G#4", pygame.K_y: "A-4", pygame.K_7: "A#4", pygame.K_u: "B-4", pygame.K_a: "OFF"
        }

    def update_modifiers_state(self, event):
        self.mods["ctrl_alt"] = (event.mod & pygame.KMOD_LALT) and (event.mod & pygame.KMOD_LCTRL)
        self.mods["ctrl_shift"] = (event.mod & pygame.KMOD_LSHIFT) and (event.mod & pygame.KMOD_LCTRL)
        self.mods["ctrl"] = event.mod & pygame.KMOD_LCTRL
        self.mods["shift"] = event.mod & pygame.KMOD_LSHIFT
        self.mods["alt"] = event.mod & pygame.KMOD_LALT

    def handle_save(self):
        self.tracker.save_song()

    def handle_load(self):
        self.tracker.load_song()

    def handle_new(self):
        self.tracker.new_project()

    def handle_duplicate(self):
        self.tracker.duplicate_selection()

    def handle_copy(self):
        self.tracker.copy_selection()

    def handle_paste(self):
        self.tracker.paste_selection()

    def handle_tab(self):
        if self.mods["shift"]:
            self.tracker.page = (self.tracker.page - 1) % 3
        else:
            self.tracker.page = (self.tracker.page + 1) % 3

    def handle_up(self):
        if self.mods["ctrl_alt"]:
            self.tracker.adjust_bpm(10)
        elif self.mods["ctrl_shift"]:
            self.tracker.seek("up", expand_selection=True)
        elif self.mods["ctrl"]:
            self.tracker.jump_page('up')
            # self.tracker.seek("up", expand_selection=False)
        elif self.mods["shift"]:
            self.tracker.move_cursor(x=0, y=-1, expand_selection=True)
        elif self.mods["alt"]:
            if self.tracker.page == 2:
                self.tracker.update_vel(10)
            else:
                self.tracker.update_timeline_step(10)
        else:
            self.tracker.move_cursor(x=0, y=-1, expand_selection=False)

    def handle_down(self):
        if self.mods["ctrl_alt"]:
            self.tracker.adjust_bpm(-10)
        elif self.mods["ctrl_shift"]:
            self.tracker.seek("down", expand_selection=True)
        elif self.mods["ctrl"]:
            self.tracker.jump_page('down')
            # self.tracker.seek("down", expand_selection=False)
        elif self.mods["shift"]:
            self.tracker.move_cursor(x=0, y=1, expand_selection=True)
        elif self.mods["alt"]:
            if self.tracker.page == 2:
                self.tracker.update_vel(-10)
            else:
                self.tracker.update_timeline_step(-10)
        else:
            self.tracker.move_cursor(x=0, y=1, expand_selection=False)

    def handle_left(self):
        if self.mods["ctrl_alt"]:
            self.tracker.adjust_bpm(-1)
        elif self.mods["ctrl_shift"]:
            self.tracker.seek("left", expand_selection=True)
        elif self.mods["ctrl"]:
            self.tracker.move_cursor(x=-self.tracker.sequencer.track_count+1, y=0, expand_selection=False)
        elif self.mods["shift"]:
            self.tracker.move_cursor(x=-1, y=0, expand_selection=True)
        elif self.mods["alt"]:
            if self.tracker.page == 2:
                self.tracker.update_vel(-1)
            else:
                self.tracker.update_timeline_step(-1)
        else:
            self.tracker.move_cursor(x=-1, y=0, expand_selection=False)

    def handle_right(self):
        if self.mods["ctrl_alt"]:
            self.tracker.adjust_bpm(1)
        elif self.mods["ctrl_shift"]:
            self.tracker.seek("right", expand_selection=True)
        elif self.mods["ctrl"]:
            self.tracker.move_cursor(x=self.tracker.sequencer.track_count-1, y=0, expand_selection=False)
        elif self.mods["shift"]:
            self.tracker.move_cursor(x=1, y=0, expand_selection=True)
        elif self.mods["alt"]:
            if self.tracker.page == 2:
                self.tracker.update_vel(1)
            else:
                self.tracker.update_timeline_step(1)
        else:
            self.tracker.move_cursor(x=1, y=0, expand_selection=False)

    def handle_kp_plus(self):
        if self.mods["ctrl"]:
            self.tracker.adjust_lpb(1)
        else:
            self.tracker.adjust_length(1)

    def handle_kp_minus(self):
        if self.mods["ctrl"]:
            self.tracker.adjust_lpb(-1)
        else:
            self.tracker.adjust_length(-1)

    def handle_kp_multiply(self):
        self.tracker.octave_mod = min(5, self.tracker.octave_mod + 1)

    def handle_kp_divide(self):
        self.tracker.octave_mod = max(-3, self.tracker.octave_mod - 1)

    def handle_page_up(self):
        if self.mods["shift"]:
            self.tracker.move_cursor(x=0, y=-8, expand_selection=True)
        else:
            self.tracker.move_cursor(x=0, y=-8, expand_selection=False)

    def handle_page_down(self):
        if self.mods["shift"]:
            self.tracker.move_cursor(x=0, y=8, expand_selection=True)
        else:
            self.tracker.move_cursor(x=0, y=8, expand_selection=False)

    def handle_home(self):
        if self.tracker.page == 2:
            y = -self.tracker.sequencer.cursor_pattern.length
        else:
            y = -self.tracker.sequencer.timeline_length
        if self.mods["shift"]:
            self.tracker.move_cursor(x=0, y=y, expand_selection=True)
        else:
            self.tracker.move_cursor(x=0, y=y, expand_selection=False)

    def handle_end(self):
        if self.tracker.page == 2:
            y = self.tracker.sequencer.cursor_pattern.length
        else:
            y = self.tracker.sequencer.timeline_length
        if self.mods["shift"]:
            self.tracker.move_cursor(x=0, y=y, expand_selection=True)
        else:
            self.tracker.move_cursor(x=0, y=y, expand_selection=False)

    def handle_insert(self):
        if self.mods["ctrl"]:
            self.tracker.insert(opt="phrase")
        else:
            self.tracker.insert(opt="pattern")

    def handle_delete(self):
        self.tracker.delete_selection()

    def handle_return(self):
        if self.mods["ctrl_alt"]:
            self.tracker.sequencer.follow_playhead = not self.tracker.sequencer.follow_playhead
            if self.tracker.sequencer.follow_playhead:
                self.tracker.cursor_y_span = 0
        else:  # for debugging
            print(f"cursor_x {self.tracker.cursor_x}, cursor_y: {self.tracker.cursor_y}")
            print(
                f"curr_phrase: {self.tracker.sequencer.cursor_phrase}, curr_pattern: {self.tracker.sequencer.cursor_pattern.num}")
            print(
                f"follow_playhead: {self.tracker.sequencer.follow_playhead}, is_playing: {self.tracker.sequencer.is_playing}")
            print(f"patterns: {self.tracker.sequencer.patterns}, phrases: {self.tracker.sequencer.phrases}")
            print("song steps: ", self.tracker.sequencer.song_steps)
            print("song playhead pos: ", self.tracker.sequencer.song_playhead_pos)
            print("phrase playhead pos: ", self.tracker.sequencer.phrase_playhead_pos)
            print("pattern playhead pos: ", self.tracker.sequencer.pattern_playhead_pos)
            print("Track 1 pattern steps: ")
            print(f"{self.tracker.sequencer.cursor_pattern.tracks[0].print_steps()}")
            print("Ends here")

    def handle_play_pause(self):
        self.tracker.play(init=True)

    def handle_keys(self, event):
        key = event.key
        self.update_modifiers_state(event)

        key_action_mapping = {
            pygame.K_TAB: self.handle_tab,
            pygame.K_UP: self.handle_up,
            pygame.K_DOWN: self.handle_down,
            pygame.K_LEFT: self.handle_left,
            pygame.K_RIGHT: self.handle_right,
            pygame.K_KP_PLUS: self.handle_kp_plus,
            pygame.K_KP_MINUS: self.handle_kp_minus,
            pygame.K_KP_MULTIPLY: self.handle_kp_multiply,
            pygame.K_KP_DIVIDE: self.handle_kp_divide,
            pygame.K_PAGEUP: self.handle_page_up,
            pygame.K_PAGEDOWN: self.handle_page_down,
            pygame.K_HOME: self.handle_home,
            pygame.K_END: self.handle_end,
            pygame.K_DELETE: self.handle_delete,
            pygame.K_INSERT: self.handle_insert,
            pygame.K_RETURN: self.handle_return,
            pygame.K_SPACE: self.handle_play_pause,
        }

        if self.mods["ctrl"] and key == pygame.K_c:
            self.handle_copy()
        elif self.mods["ctrl"] and key == pygame.K_v:
            self.handle_paste()
        elif self.mods["ctrl"] and key == pygame.K_s:
            self.handle_save()
        elif self.mods["ctrl"] and key == pygame.K_l:
            self.handle_load()
        elif self.mods["ctrl"] and key == pygame.K_n:
            self.handle_new()
        elif self.mods["ctrl"] and key == pygame.K_d:
            self.handle_duplicate()
        elif key in key_action_mapping:
            key_action_mapping[key]()
        elif key in self.note_mapping and self.tracker.page == 2:
            self.tracker.add_note(self.note_mapping[key])
