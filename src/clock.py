from threading import Thread, Lock, Event
from time import perf_counter, sleep


class Clock:
    def __init__(self, bpm, callback):
        self._mutex = Lock()
        self.bpm = bpm
        self.interval = 60.0 / (bpm * 96)
        self.running = Event()
        self.running.set()
        self.callback = callback
        self.thread = Thread(target=self._run)
        self.thread.start()

    def _run(self):
        next_time = perf_counter()
        while self.running.is_set():
            current_time = perf_counter()
            elapsed = current_time - next_time
            if elapsed >= self.interval:
                # print("callback")
                self.callback()
                next_time += self.interval
            else:
                sleep(self.interval - elapsed)

            # check if execution paused:
            elapsed = current_time - next_time
            if elapsed >= self.interval * 24:
                next_time = current_time

    def set_bpm(self, bpm):
        with self._mutex:
            if bpm != self.bpm:
                self.bpm = bpm
                self.interval = 60.0 / (bpm * 96)

    def stop(self):
        self.running.clear()
        self.thread.join()
