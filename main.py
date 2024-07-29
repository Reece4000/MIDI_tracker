import pygame
import pygame.midi
import sys
import time
from time import perf_counter
from tracker import Tracker
from key_handler import KeyHandler
from gui_elements import UserInput
import constants

pygame.init()
pygame.font.init()
pygame.midi.init()
pygame.key.set_repeat(180, 40)


font_mapping = {
    # Info display
    "tracker_info_font": pygame.font.Font(r'fonts\pixel\PixelOperatorMonoHB8.ttf', 8),
    # MIDI out display font
    "tracker_MIDI_out_font": pygame.font.Font(r'fonts\pixel\PixelOperatorSC-Bold.ttf', 24),
    # MIDI track display
    "track_display_font": pygame.font.Font(r'fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
    # Tracker step
    "tracker_font": pygame.font.Font(r'fonts\pixel\PixelOperatorSC.ttf', 16),
    # Bold tracker step
    "tracker_font_bold": pygame.font.Font(r'fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
    # Tracker row numbers
    "tracker_row_label_font": pygame.font.Font(r'fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
    # Tracker timeline numbers
    "tracker_timeline_font": pygame.font.Font(r'fonts\pixel\PixelOperatorSC-Bold.ttf', 16),
}


def render_components(render_queue, draw_screen):
    draw_screen.fill((26, 36, 36))
    for item in render_queue.queue:
        component = item[0]
        if component == "line":
            pygame.draw.line(draw_screen, *item[1])
        elif component == "text":
            text = font_mapping[item[1]].render(*item[2])
            draw_screen.blit(text, item[3])
        elif component == "rect":
            pygame.draw.rect(draw_screen, *item[1])
        elif component == "polygon":
            pygame.draw.polygon(draw_screen, *item[1])
        elif component == "pane":
            s = pygame.Surface(item[1][1])
            s.set_alpha(40)
            s.fill(item[1][0])
            draw_screen.blit(s, item[1][2])
        elif component == "circle":
            pygame.draw.circle(draw_screen, *item[1])

    pygame.display.update()


def main_loop():
    print("Initializing Pygame...")
    print("Setting up MIDI...")
    midi_output, midi_output_name, midi_ix = None, "", 0
    for i in range(pygame.midi.get_count()):
        info = pygame.midi.get_device_info(i)
        if b"Internal MIDI" in info[1] and info[3] == 1:
            midi_output = pygame.midi.Output(i)
            midi_output_name = info[1].decode()
            midi_ix = i
            break
    if midi_output is None:
        print("No suitable MIDI output device found.")
    else:
        print(f"MIDI Output initialized: {midi_output_name}")

    print("Creating window...")
    screen = pygame.display.set_mode((constants.WIDTH, constants.HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Simpl Trakr")

    print("Initializing Tracker...")
    tracker = Tracker(screen, constants.track_count, constants.track_length,
                      midi_output, midi_output_name, midi_ix)
    keyhandler = KeyHandler(tracker=tracker)

    print("Starting main loop...")
    window_size_check_scheduler = 60
    last_update_time = perf_counter()
    running = True

    while running:
        redraw = False
        current_time = perf_counter()
        delta_time = current_time - last_update_time
        last_update_time = current_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("Quit event detected.")
                tracker.is_playing = False
                running = False
            elif event.type == pygame.KEYDOWN:
                keyhandler.handle_keys(event)
                redraw = True
            elif event.type == pygame.MOUSEWHEEL:
                # need to fix issues with selection span when using mousewheel
                tracker.cursor_y -= event.y
                tracker.cursor_y = max(0, min(tracker.cursor_y, tracker.sequencer.cursor_pattern.length - 1))
                redraw = True

        if window_size_check_scheduler == 0:
            tracker.win_height = pygame.display.get_surface().get_height()
            window_size_check_scheduler = 600
            redraw = True
        else:
            window_size_check_scheduler -= 1

        if tracker.sequencer.is_playing:
            tracker.sequencer.time_since_last_step += delta_time
            if tracker.sequencer.time_since_last_step >= tracker.sequencer.step_time:
                tracker.tick()
                redraw = True
                tracker.sequencer.time_since_last_step -= tracker.sequencer.step_time
                if tracker.sequencer.time_since_last_step >= tracker.sequencer.step_time:
                    redraw = False

        if redraw:
            tracker.update_render_queue()
            render_components(tracker.render_queue, screen)

    print("Cleaning up and exiting...")
    for channel in range(tracker.sequencer.track_count):
        if tracker.sequencer.last_note_played[channel] is not None:
            midi_output.note_off(tracker.sequencer.last_note_played[channel], channel=channel)
    midi_output.close()
    pygame.midi.quit()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main_loop()
