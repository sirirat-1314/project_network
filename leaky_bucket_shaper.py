"""Bounded FIFO and paced output; Python timing is best effort, not real time."""
import queue
import threading
import time


class LeakyBucket:
    def __init__(self, drain_rate_pps, capacity, output_callback):
        if drain_rate_pps <= 0 or capacity < 1:
            raise ValueError("Rate and capacity must be positive")
        self.interval = 1.0 / drain_rate_pps
        self.buffer = queue.Queue(maxsize=capacity)
        self.output = output_callback
        self.sent = 0
        self.dropped = 0
        self.error = None
        self.worker = threading.Thread(target=self._drain, daemon=True)
        self.worker.start()

    def add_packet(self, packet):
        if self.error:
            raise RuntimeError("Leaky bucket output failed") from self.error
        try:
            self.buffer.put_nowait(packet)
        except queue.Full:
            self.dropped += 1

    def _drain(self):
        next_send = 0.0
        while True:
            packet = self.buffer.get()
            try:
                if packet is None:
                    return
                if self.error is not None:
                    continue
                time.sleep(max(0.0, next_send - time.perf_counter()))
                self.output(packet)
                self.sent += 1
                # No catch-up bursts after an OS scheduling pause.
                next_send = time.perf_counter() + self.interval
            except Exception as exc:
                self.error = exc
            finally:
                self.buffer.task_done()

    def close(self):
        self.buffer.join()
        self.buffer.put(None)
        self.worker.join()
        if self.error:
            raise RuntimeError("Leaky bucket output failed") from self.error


if __name__ == "__main__":
    from generate_burst_traffic import main
    main(default_mode="leaky")

