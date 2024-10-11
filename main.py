import sys
import os
import asyncio
import tracemalloc
from src import utils
from src.tracker import Tracker
import cProfile
import traceback
import pstats
import psutil

PROFILE = True
RUN_ASYNC = True
TRACE_MALLOC = False
SET_PRIORITY = False

os.chdir(os.path.abspath(os.path.dirname(__file__)))
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

if SET_PRIORITY:
    isWindows = True
    try:
        sys.getwindowsversion()
    except AttributeError:
        isWindows = False

    p = psutil.Process(os.getpid())
    if not isWindows:
        p.nice(10)
    else:
        p.nice(psutil.REALTIME_PRIORITY_CLASS)


class EventBus:
    def __init__(self):
        self._handlers = {}

    def subscribe(self, event_type, handler):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def publish(self, event_type, data=None):
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                if data is None:
                    handler()
                else:
                    handler(data)


def print_timings():
    print("\nAverage execution times per method:")
    for method_name, times in utils.measured_times.items():
        avg_time = times[0]
        print(f"{method_name}: {avg_time * 1000000:.2f} µs")


def main():
    if PROFILE:
        tracemalloc.start()

    event_bus = EventBus()
    tracker = Tracker(event_bus)

    if RUN_ASYNC:
        asyncio.run(tracker.running_loop())
    else:
        tracker.running_loop_non_async()

    if PROFILE:
        print_timings()
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        print("Memory allocation, top 10 lines")
        for stat in top_stats[:10]:
            print(stat)

        tracemalloc.stop()


if __name__ == "__main__":
    try:
        if not PROFILE:
            main()
        else:
            # Profile the `main` function and save the stats in memory
            cProfile.run('main()', 'main_stats')
            p = pstats.Stats('main_stats')
            # Load the profile stats and sort by cumulative time
            p.strip_dirs().sort_stats('cumtime').print_stats()

    except Exception as e:
        print(traceback.format_exc())

    # input("Press enter to exit")
