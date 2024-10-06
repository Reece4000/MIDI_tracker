import pygame
from src.utils import timing_decorator
from config import constants, controller, events
from config.pages import *


class InputHandler:
    def __init__(self, tracker):
        pygame.key.set_repeat(180, 40)
        self.control_map = controller.PS4
        self.select_held = False
        self.mods = {
            "l1": False,
            "r1": False,
            "ctrl": False,
            "shift": False,
            "alt": False
        }
        self.joy_btn_mapping = self.control_map["Buttons"]
        self.joy_axis_mapping = self.control_map["Axes"]

        self.joy_btn_state = {
            v: {"Held": False, "Time Pressed": 0, "Repeating": False} for v in self.joy_btn_mapping.values()
        }

        self.joy_axis_state = {
            v: {"Held": False, "Time Pressed": 0, "Repeating": False, "Last Value": None} for v in self.joy_axis_mapping.values()
        }

        self.joy_repeat_start = 0.15
        self.joy_repeat_interval = 0.035
        self.axis_repeat_interval = 0.08
        self.joystick = None
        pygame.joystick.init()

        joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
        self.joystick = None
        for joystick in joysticks:
            if "PS4" in joystick.get_name():
                self.joystick = joystick
                break

        self.initial_mouse_pos = None
        self.final_mouse_pos = None
        self.tracker = tracker

        self.note_mapping = {
            pygame.K_z: 12, pygame.K_s: 13, pygame.K_x: 14, pygame.K_d: 15, pygame.K_c: 16,
            pygame.K_v: 17, pygame.K_g: 18, pygame.K_b: 19, pygame.K_h: 20, pygame.K_n: 21,
            pygame.K_j: 22, pygame.K_m: 23, pygame.K_q: 24, pygame.K_2: 25, pygame.K_w: 26,
            pygame.K_3: 27, pygame.K_e: 28, pygame.K_r: 29, pygame.K_5: 30, pygame.K_t: 31,
            pygame.K_6: 32, pygame.K_y: 33, pygame.K_7: 34, pygame.K_u: 35, pygame.K_a: -1
        }

        self.tracker.event_bus.subscribe(events.RENDERER_INITIALISED, self.initialise)

    def initialise(self):
        pygame.key.set_repeat(180, 40)
        self.joystick = None
        pygame.joystick.init()

        joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
        self.joystick = None
        for joystick in joysticks:
            if "PS4" in joystick.get_name():
                self.joystick = joystick
                break

    def check_for_events(self, current_time):
        mods = pygame.key.get_mods()
        self.update_modifiers_state(mods)
        self.handle_joy_repeat(current_time)

        iterations = 0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("Quit event detected.")
                self.tracker.is_playing = False
                return "Exit"

            elif event.type == pygame.VIDEOEXPOSE:
                pass

            elif event.type == pygame.KEYDOWN:
                self.handle_keys(event.key)

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_f:
                    self.select_held = False

            elif (event.type == pygame.JOYBUTTONDOWN or
                  event.type == pygame.JOYBUTTONUP or
                  event.type == pygame.JOYAXISMOTION):
                self.handle_joystick_event(event, current_time)

            elif event.type == pygame.MOUSEWHEEL:
                self.tracker.move_cursor(x=0, y=-event.y, expand_selection=False)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    self.initial_mouse_pos = event.pos
                    self.tracker.temp_y = self.tracker.mouse_y
                    self.tracker.process_mouse(self.initial_mouse_pos, self.initial_mouse_pos, s=0)

            elif event.type == pygame.MOUSEMOTION:
                self.tracker.mouse_x, self.tracker.mouse_y = event.pos
                if pygame.mouse.get_pressed()[0]:  # Check if left button is held down
                    self.final_mouse_pos = event.pos
                    if self.final_mouse_pos != self.initial_mouse_pos:
                        self.tracker.process_mouse(self.initial_mouse_pos, self.final_mouse_pos, s=1)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left mouse button
                    self.final_mouse_pos = event.pos
                    self.tracker.process_mouse(self.initial_mouse_pos, self.final_mouse_pos, s=2)

            iterations += 1
        return

    def update_modifiers_state(self, mods):
        if self.joystick is not None:
            joy_l1 = self.joystick.get_button(self.joy_btn_mapping["L1"])
            joy_r1 = self.joystick.get_button(self.joy_btn_mapping["R1"])
        else:
            joy_l1 = joy_r1 = joy_r2 = joy_l2 = None

        self.mods["l1"] = (mods & pygame.KMOD_LCTRL) or joy_l1
        self.mods["r1"] = (mods & pygame.KMOD_LALT) or joy_r1

        if (self.mods["r1"] and self.mods["l1"]) != self.tracker.pages[TIMELINE].active:
            self.tracker.toggle_timeline_view()
        elif not self.tracker.pages[TIMELINE].active and (self.mods["r1"] != self.tracker.pages[EDITOR].active):
            self.tracker.toggle_editor_window()


    def handle_save(self):
        self.tracker.save_song()

    def handle_load(self):
        self.tracker.load_song()

    def handle_new(self):
        self.tracker.new_song()

    def handle_duplicate(self):
        self.tracker.handle_duplicate()

    def handle_tab(self):
        self.tracker.page_switch(-1 if self.mods["shift"] else 1)

    def handle_up(self, repeat_press=False):
        if self.tracker.page == TIMELINE:
            if self.joy_btn_state[0]["Held"] or self.select_held:
                self.tracker.handle_param_adjust(10)
            else:
                self.tracker.move_cursor(x=0, y=-1, expand_selection=self.joy_btn_state[2]["Held"])
        elif self.joy_btn_state[2]["Held"] and self.tracker.page == EDITOR:
            if not repeat_press:
                self.tracker.pages[EDITOR].open_page(page_index=None, increment=-1)
        elif self.joy_btn_state[2]["Held"] and self.mods["l1"]:
            self.tracker.move_in_place(0, -1)
        elif self.joy_btn_state[0]["Held"] or self.select_held:
            self.tracker.handle_param_adjust(12)
        elif self.mods["ctrl"] and self.mods["shift"]:
            self.tracker.seek("up", expand_selection=True)
        elif self.mods["ctrl"]:
            self.tracker.jump_page('up')
            # self.tracker.seek("up", expand_selection=False)
        else:  # self.mods["shift"]:
            self.tracker.move_cursor(x=0, y=-1, expand_selection=self.joy_btn_state[2]["Held"])

    def handle_down(self, repeat_press=False):
        if self.tracker.page == TIMELINE:
            if self.joy_btn_state[0]["Held"] or self.select_held:
                self.tracker.handle_param_adjust(-10)
            else:
                self.tracker.move_cursor(x=0, y=1, expand_selection=self.joy_btn_state[2]["Held"])
        elif self.joy_btn_state[2]["Held"] and self.tracker.page == EDITOR:
            if not repeat_press:
                self.tracker.pages[EDITOR].open_page(page_index=None, increment=1)
        elif self.joy_btn_state[2]["Held"] and self.mods["l1"]:
            self.tracker.move_in_place(x=0, y=1)
        elif self.joy_btn_state[0]["Held"] or self.select_held:
            self.tracker.handle_param_adjust(-12)
        elif self.mods["ctrl"] and self.mods["shift"]:
            self.tracker.seek("down", expand_selection=True)
        elif self.mods["ctrl"]:
            self.tracker.jump_page('down')
            # self.tracker.seek("down", expand_selection=False)
        else:  # self.mods["shift"]:
            self.tracker.move_cursor(x=0, y=1, expand_selection=self.joy_btn_state[2]["Held"])

    def handle_left(self, repeat_press=False):
        if self.tracker.page == TIMELINE:
            if self.joy_btn_state[0]["Held"] or self.select_held:
                self.tracker.handle_param_adjust(-1)
            else:
                self.tracker.move_cursor(x=-1, y=0, expand_selection=self.joy_btn_state[2]["Held"])
        elif self.mods["l1"] and self.joy_btn_state[2]["Held"]:
            self.tracker.move_in_place(x=-1, y=0)
        elif self.mods["l1"]:
            if not repeat_press:
                self.tracker.page_switch()
        elif self.joy_btn_state[0]["Held"] or self.select_held:
            self.tracker.handle_param_adjust(-1)
        elif self.mods["ctrl"] and self.mods["shift"]:
            self.tracker.seek("left", expand_selection=True)
        elif self.mods["ctrl"]:
            self.tracker.move_cursor(x=-constants.track_count + 1, y=0, expand_selection=False)
        else:
            self.tracker.move_cursor(x=-1, y=0, expand_selection=self.joy_btn_state[2]["Held"])

    def handle_right(self, repeat_press=False):
        if self.tracker.page == TIMELINE:
            if self.joy_btn_state[0]["Held"] or self.select_held:
                self.tracker.handle_param_adjust(1)
            else:
                self.tracker.move_cursor(x=1, y=0, expand_selection=self.joy_btn_state[2]["Held"])
        elif self.mods["l1"] and self.joy_btn_state[2]["Held"]:
            self.tracker.move_in_place(x=1, y=0)
        elif self.mods["l1"]: # and self.mods["r1"]:
            if not repeat_press:
                self.tracker.page_switch()
        elif self.joy_btn_state[0]["Held"] or self.select_held:
            self.tracker.handle_param_adjust(1)
            return
        elif self.mods["ctrl"] and self.mods["shift"]:
            self.tracker.seek("right", expand_selection=True)
        else:  # self.mods["shift"]:
            self.tracker.move_cursor(x=1, y=0, expand_selection=self.joy_btn_state[2]["Held"])

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
        self.tracker.octave_mod = min(8, self.tracker.octave_mod + 1)

    def handle_kp_divide(self):
        self.tracker.octave_mod = max(0, self.tracker.octave_mod - 1)

    def handle_page_up(self):
        self.tracker.move_cursor(x=0, y=-8, expand_selection=self.mods["shift"])

    def handle_page_down(self):
        self.tracker.move_cursor(x=0, y=8, expand_selection=self.mods["shift"])

    def handle_home(self):
        if self.tracker.page == 2:
            sel_track = self.tracker.cursor_pattern.tracks[self.tracker.pattern_cursor_x]
            y = -sel_track.length
        else:
            y = -self.tracker.timeline_length

        self.tracker.move_cursor(x=0, y=y, expand_selection=self.mods["shift"])

    def handle_end(self):
        if self.tracker.page == 2:
            sel_track = self.tracker.cursor_pattern.tracks[self.tracker.pattern_cursor_x]
            y = sel_track.length
        else:
            y = self.tracker.timeline_length

        self.tracker.move_cursor(x=0, y=y, expand_selection=self.mods["shift"])

    def handle_insert(self):
        pass
        # self.tracker.handle_insert(opt="phrase" if self.mods["ctrl"] else "pattern")

    def handle_delete(self):
        self.tracker.handle_delete()

    def handle_return(self):
        # self.tracker.options_menu()
        pass

    def handle_play_pause(self):
        self.tracker.toggle_playback()

    def handle_select_press(self):
        self.tracker.handle_select()

    def handle_keys(self, key):
        if key == pygame.K_F11:
            self.tracker.event_bus.publish(events.FULLSCREEN)
            return
        if key == pygame.K_ESCAPE:
            self.tracker.event_bus.publish(events.QUIT)
        if key == pygame.K_f:
            self.select_held = True
            self.handle_select_press()

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
            pygame.K_SPACE: self.handle_play_pause
        }

        if self.mods["ctrl"] and key == pygame.K_c:
            self.tracker.handle_copy()
        elif self.mods["ctrl"] and key == pygame.K_v:
            self.tracker.handle_paste()
        elif self.mods["ctrl"] and key == pygame.K_s:
            self.handle_save()
        elif self.mods["ctrl"] and key == pygame.K_l:
            self.handle_load()
        elif self.mods["ctrl"] and key == pygame.K_n:
            self.handle_new()
        elif self.mods["ctrl"] and key == pygame.K_d:
            self.tracker.handle_duplicate()
        elif key == pygame.K_HASH:
            self.tracker.toggle_mute()
        elif key in key_action_mapping:
            key_action_mapping[key]()
        elif key in self.note_mapping and self.tracker.page == PATTERN:
            self.tracker.keyboard_insert(self.note_mapping[key])

    def joystick_functions(self, button, repeat_press=False):
        if button == self.joy_btn_mapping["Down"]:
            self.handle_down(repeat_press)

        elif button == self.joy_btn_mapping["Up"]:
            self.handle_up(repeat_press)

        elif button == self.joy_btn_mapping["Right"]:
            self.handle_right(repeat_press)

        elif button == self.joy_btn_mapping["Left"]:
            self.handle_left(repeat_press)

        elif button == self.joy_btn_mapping["Start"]:
            if not repeat_press:
                self.tracker.toggle_editor_window()

        elif button == self.joy_btn_mapping["Triangle"]:
            if self.mods["l1"] and self.mods["r1"]:
                self.tracker.handle_copy()
            elif self.mods["l1"]:
                self.tracker.handle_copy()
            else:
                if not repeat_press:
                    self.handle_play_pause()

        elif button == self.joy_btn_mapping["Circle"]:
            if self.mods["l1"] and self.mods["r1"]:
                self.tracker.handle_paste()
            elif self.mods["l1"]:
                self.tracker.handle_paste()
                # self.tracker.handle_delete(remove_steps=True)
            else:
                if not repeat_press:
                    self.tracker.handle_delete(remove_steps=False)

        elif button == self.joy_btn_mapping["Cross"]:
            if self.mods["l1"] and self.mods["r1"]:
                self.handle_select_press()
            elif self.mods["l1"]:  # L1
                # self.tracker.insert()
                pass
            else:
                if not self.joy_btn_state[0]["Held"]:
                    self.handle_select_press()

    def handle_joy_repeat(self, time):
        if self.joystick is None:
            return
        for button, state in self.joy_btn_state.items():
            if state["Held"]:
                # print(button, state)
                time_pressed = state["Time Pressed"]
                if not state["Repeating"] and (time - time_pressed) > self.joy_repeat_start:
                    self.joystick_functions(button, repeat_press=True)
                    state["Time Pressed"] = time
                    state["Repeating"] = True
                elif state["Repeating"] and (time - time_pressed) > self.joy_repeat_interval:
                    self.joystick_functions(button, repeat_press=True)
                    state["Time Pressed"] = time

        for axis, state in self.joy_axis_state.items():
            if state["Held"]:
                # print(button, state)
                start_time = state["Time Pressed"]
                if (time - start_time) > self.axis_repeat_interval:
                    if axis == 5 and self.joy_btn_state[0]["Held"]:
                        self.tracker.handle_param_adjust(1, axis=True)
                    elif axis == 4 and self.joy_btn_state[0]["Held"]:
                        self.tracker.handle_param_adjust(-1, axis=True)
                    state["Time Pressed"] = time

    def handle_joystick_event(self, event, time):
        if event.type == pygame.JOYBUTTONDOWN:
            self.joystick_functions(event.button)
            self.joy_btn_state[event.button]["Held"] = True
            self.joy_btn_state[event.button]["Time Pressed"] = time

        elif event.type == pygame.JOYBUTTONUP:
            self.joy_btn_state[event.button]["Held"] = False
            self.joy_btn_state[event.button]["Time Pressed"] = 0
            self.joy_btn_state[event.button]["Repeating"] = False
            if event.button == 0:
                self.tracker.stop_preview()

        elif event.type == pygame.JOYAXISMOTION:
            if event.axis in [4, 5]:
                # Determine increment based on event value
                inc = 1  # Default value if no match is found
                for threshold in controller.axis_repeat_mapping.keys():
                    if event.value >= threshold:
                        self.axis_repeat_interval = controller.axis_repeat_mapping[threshold]
                    else:
                        break

                # Handle axis movement and state
                if not self.joy_axis_state[event.axis]["Held"]:
                    if self.joy_btn_state[0]["Held"]:
                        self.tracker.handle_param_adjust(-inc if event.axis == 4 else inc, axis=True)

                if event.value < -1:
                    if self.joy_axis_state[event.axis]["Held"]:
                        self.tracker.preview_step()
                    self.joy_axis_state[event.axis]["Held"] = False
                    self.joy_axis_state[event.axis]["Time Pressed"] = 0

                else:
                    if not self.joy_axis_state[event.axis]["Held"]:
                        self.joy_axis_state[event.axis]["Held"] = True
                        self.joy_axis_state[event.axis]["Time Pressed"] = time
