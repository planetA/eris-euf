from threading import Thread
from queue import Queue, Empty


class EndOfStream(Exception): pass

class NonBlockingStreamIO:
    def __init__(self, stream):
        self._stream = stream
        self._queue = Queue()

        def populate(stream, queue):
            while True:
                line = stream.readline()
                if line:
                    queue.put(line.decode())
                else:
                    raise EndOfStream

        self._thread = Thread(target=populate, args=(self._stream, self._queue))
        self._thread.daemon = True
        self._thread.start()

    def readline(self, timeout=None):
        try:
            return self._queue.get(block=timeout is not None, timeout=timeout)
        except Empty:
            return None

    def read(self, timeout=None):
        data = ""
        done = False

        while not done:
            line = self.readline(timeout)
            done = line is None
            if not done:
                data += line

        return data

    def clear(self):
        with self._queue.mutex:
            self._queue.queue.clear()


