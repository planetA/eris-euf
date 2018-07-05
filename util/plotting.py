from subprocess import Popen, PIPE
from enum import Enum
import logging

from util.io import NonBlockingStreamIO, EndOfStream

logger = logging.getLogger(__name__)

class PlotError(Exception): pass

class Plot:
    def __init__(self):
        self._gnuplot = Popen(["gnuplot", "-p"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        self._in = self._gnuplot.stdin
        self._out = NonBlockingStreamIO(self._gnuplot.stdout)
        self._err = NonBlockingStreamIO(self._gnuplot.stderr)

    def _send_command(self, command):
        self._err.clear()

        logger.debug("send to gnuplot:\n{}".format(command))

        self._in.write(command.encode())
        self._in.flush()

        error = self._err.read(timeout=.1)
        if len(error) != 0:
            raise PlotError("gnuplot reported an error:\n{}".format(error))

    def set(self, option, *values):
        command = "set {} ".format(option)
        command += " ".join([str(v) for v in values])
        command += "\n"

        self._send_command(command)
        return self

    def unset(self, option):
        command = "unset {}\n".format(option)

        self._send_command(command)
        return self

    def plot(self, *funcs):
        command = "plot "
        command += ", ".join([str(f) for f in funcs])
        command += "\n"

        self._send_command(command)
        return self

    def plot_data(self, data, *funcs, name="data"):
        command = "${} << EOD\n".format(name)
        command += "\n".join([" ".join([str(v) for v in row]) for row in data])
        command += "\nEOD\n"

        self._send_command(command)

        command = "plot "
        command += ", ".join([str(f) for f in funcs])
        command += "\n"
        self._send_command(command)
        return self

    def replot(self):
        self._send_command("replot")
        return self


class AsciiPlot(Plot):
    class Colors(Enum):
        MONO = "mono"
        ANSI = "ansi"
        ANSI256 = "ansi256"
        ANSIRGB = "ansirgb"

    def __init__(self, width, height, color=Colors.ANSI, feed=False):
        super().__init__()

        self._width = width
        self._height = height
        self._color = color
        self._feed = feed

        self._set_term()

    def _set_term(self):
        super().set("term", "dumb", "size {},{}".format(self._width, self._height),
                "feed" if self._feed else "nofeed", self._color.value)

    def resize(self, width, height):
        self._width = width
        self._height = height

        self._set_term()

    def color(self, color):
        self._color = color

        self._set_term()

    def feed(self, feed):
        self._feed = feed

        self._set_term()

    def set(self, option, *values):
        if option == "term":
            raise ValueError("Can't set term. Use different Plot type")

        return super().set(option, *values)

    def unset(self, option):
        if option == "term":
            raise ValueError("Can't unset term. Use different Plot type!")

        return super().unset(option)

    def plot(self, *funcs):
        self._out.clear()

        super().plot(*funcs)

        return self._out.read(timeout=.1)

    def plot_data(self, data, *funcs, name="data"):
        self._out.clear()

        super().plot_data(data, *funcs, name=name)

        return self._out.read(timeout=.1)

    def replot(self):
        self._out.clear()

        super().replot()

        return self._out.read(timeout=.1)
