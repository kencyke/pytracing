import os
import sys
import json
import time
import threading
from contextlib import contextmanager
from queue import Queue
from types import FrameType
from typing import Any, IO, Iterator


def seconds_to_microseconds(s: float) -> int:
    return int(1000000 * s)


class TraceWriter(threading.Thread):
    def __init__(self, terminator: threading.Event, input_queue: Queue, output_stream: IO[str]) -> None:
        threading.Thread.__init__(self)
        self.daemon = True
        self.terminator = terminator
        self.input = input_queue
        self.output = output_stream

    def run(self) -> None:
        self.output.write('[')
        while not self.terminator.is_set() or not self.input.empty():
            item = self.input.get()
            self.output.write(json.dumps(item) + ',\n')
        self.output.write('{}]')  # empty {} so the final entry doesn't end with a comma


class TraceProfiler(object):
    """A python trace profiler that outputs Chrome Trace-Viewer format (about://tracing).

     Usage:

        from pytracing import TraceProfiler
        tp = TraceProfiler(output=open('/tmp/trace.out', 'wb'))
        with tp.traced():
          ...
    
    """

    TYPES = {'call': 'B', 'return': 'E'}

    def __init__(self, output: IO[str], clock=None) -> None:
        self.output = output
        self.clock = clock or time.time
        self.pid = os.getpid()
        self.queue: Queue = Queue()
        self.terminator = threading.Event()
        self.writer = TraceWriter(self.terminator, self.queue, self.output)

    @property
    def thread_id(self) -> str:
        return threading.current_thread().name

    @contextmanager
    def traced(self) -> Iterator[None]:
        """Context manager for install/shutdown in a with block."""
        self.init()
        try:
            yield
        finally:
            self.shutdown()

    def init(self):
        """Set the profile function, and start the writer thread."""
        self.writer.start()  # Start the writer thread.
        sys.setprofile(self.tracer)  # Set the trace/profile function.
        threading.setprofile(self.tracer)  # Set the trace/profile function for threads.

    def shutdown(self):
        """Unset the profile function and stop the writer thread."""
        sys.setprofile(None)  # Clear the trace/profile function.
        threading.setprofile(None)  # Clear the trace/profile function for threads.
        self.terminator.set()  # Stop the writer thread.
        self.writer.join()  # Join the writer thread.

    def fire_event(
        self,
        event_type: str,
        func_name: str,
        func_filename: str,
        func_line_no: int,
        caller_filename: str,
        caller_line_no: int,
    ) -> None:
        """Queue a trace event."""
        timestamp = seconds_to_microseconds(self.clock())

        # https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU/preview
        event = dict(
            name=func_name,  # Event Name.
            cat=func_filename,  # Event Category.
            tid=self.thread_id,  # Thread ID.
            ph=self.TYPES[event_type],  # Event Type.
            pid=self.pid,  # Process ID.
            ts=timestamp,  # Timestamp.
            args=dict(
                function=':'.join([str(x) for x in (func_filename, func_line_no, func_name)]),
                caller=':'.join([str(x) for x in (caller_filename, caller_line_no)]),
            ),
        )
        self.queue.put(event)

    # https://docs.python.org/ja/3/library/sys.html#sys.setprofile
    def tracer(self, frame: FrameType, event_type: str, arg: Any) -> None:
        """Bound profile function for sys.profile()."""
        try:
            if event_type in self.TYPES.keys() and frame.f_code.co_name != 'write':
                self.fire_event(
                    event_type=event_type,
                    func_name=frame.f_code.co_name,
                    func_filename=frame.f_code.co_filename,
                    func_line_no=frame.f_lineno,
                    caller_filename=frame.f_back.f_code.co_filename,
                    caller_line_no=frame.f_back.f_lineno,
                )
        except Exception:
            pass  # Don't disturb execution if we can't log the trace.
