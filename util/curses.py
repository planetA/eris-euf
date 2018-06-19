from enum import IntEnum
from locale import setlocale, LC_ALL, getpreferredencoding
import re

import curses


class Curses:
    # Keys which can be listened on
    class Keys(IntEnum):
        LEFT        = curses.KEY_LEFT
        RIGHT       = curses.KEY_RIGHT
        UP          = curses.KEY_UP
        DOWN        = curses.KEY_DOWN
        HOME        = curses.KEY_HOME
        END         = curses.KEY_END
        PAGE_UP     = curses.KEY_PPAGE
        PAGE_DOWN   = curses.KEY_NPAGE
        ESC         = 27
        BACKSPACE   = curses.KEY_BACKSPACE
        F0          = curses.KEY_F0
        F1          = curses.KEY_F1
        F2          = curses.KEY_F2
        F3          = curses.KEY_F3
        F4          = curses.KEY_F4
        F5          = curses.KEY_F5
        F6          = curses.KEY_F6
        F7          = curses.KEY_F7
        F8          = curses.KEY_F8
        F9          = curses.KEY_F9
        F10         = curses.KEY_F10
        F11         = curses.KEY_F11
        F12         = curses.KEY_F12
        MOUSE       = curses.KEY_MOUSE
        RESIZE      = curses.KEY_RESIZE
        REFRESH     = curses.KEY_REFRESH
        NOKEY       = -1


    # Available Colors
    class Colors(IntEnum):
        DEFAULT     = -1
        BLACK       = curses.COLOR_BLACK
        BLUE        = curses.COLOR_BLUE
        CYAN        = curses.COLOR_CYAN
        GREEN       = curses.COLOR_GREEN
        MAGENTA     = curses.COLOR_MAGENTA
        RED         = curses.COLOR_RED
        WHITE       = curses.COLOR_WHITE
        YELLOW      = curses.COLOR_YELLOW


    # Available Modes
    class Modes(IntEnum):
        BLINK       = curses.A_BLINK
        BOLD        = curses.A_BOLD
        DIM         = curses.A_DIM
        NORMAL      = curses.A_NORMAL
        REVERSE     = curses.A_REVERSE
        UNDERLINE   = curses.A_UNDERLINE


    _next_pair_number = 1
    _color_pairs = {}

    def __init__(self):
        self._root = None
        self._root_window = None

    def __enter__(self):
        if not self._root is None:
            return

        # Initialize the locale for UTF-8 support
        setlocale(LC_ALL, "")
        Curses.encoding = getpreferredencoding()

        # Initialize curses
        self._root = curses.initscr()
        self._root_window = Window(self._root)

        curses.noecho()
        curses.cbreak()

        # Invisible cursor
        curses.curs_set(0)

        # Enable colors
        curses.start_color()
        curses.use_default_colors()

        # Make curses interpret keys
        self._root.keypad(1)

        return self

    def __exit__(self, type, value, traceback):
        if self._root is None:
            return

        # Tear down curses
        self._root.keypad(0)
        curses.curs_set(1)
        curses.echo()
        curses.nocbreak()
        curses.endwin()

        self._root = None
        self._root_window = None

    @classmethod
    def init_color_pair(cls, fg, bg):
        if (fg, bg) in cls._color_pairs:
            return

        if cls._next_pair_number > curses.COLOR_PAIRS - 1:
            # Use the default colors instead
            cls._color_pairs[(fg, bg)] = curses.color_pair(0)
            return

        curses.init_pair(cls._next_pair_number, fg, bg)
        cls._color_pairs[(fg,bg)] = curses.color_pair(cls._next_pair_number)

        cls._next_pair_number += 1

    @classmethod
    def get_color_pair(cls, fg, bg):
        if not (fg, bg) in cls._color_pairs:
            cls.init_color_pair(fg, bg)

        return cls._color_pairs[(fg, bg)]

    @staticmethod
    def new_window(x, y, width, height):
        return curses.newwin(height, width, y, x)

    def root_window(self):
        return self._root_window

    def nodelay(self, value=True):
        curses.nodelay(value)

class Window:
    # Sequence Interpreter used in the safe_print method
    class SequenceInterpreter:
        def can_interpret(self, text, position):
            raise NotImplementedError()

        def interpret(self, text, position, window):
            raise NotImplementedError()

        def clean_up(self, window):
            raise NotImplementedError()


    class DefaultInterpreter(SequenceInterpreter):
        def can_interpret(self, text, position):
            return True

        def interpret(self, text, position, window):
            window.pretty_print(text[position], modes=[Curses.Modes.UNDERLINE])

            return position + 1

        def clean_up(self, window):
            # Nothing to do here.
            pass


    class ModeInterpreter(SequenceInterpreter):
        regex = re.compile(r"\033\[([0-9]+;?)+m")

        def can_interpret(self, text, position):
            return self.regex.match(text[position:]) is not None

        def interpret(self, text, position, window):
            fg_colors = {
                "30"      : Curses.Colors.BLACK,
                "31"      : Curses.Colors.RED,
                "32"      : Curses.Colors.GREEN,
                "33"      : Curses.Colors.YELLOW,
                "34"      : Curses.Colors.BLUE,
                "35"      : Curses.Colors.MAGENTA,
                "36"      : Curses.Colors.CYAN,
                "37"      : Curses.Colors.WHITE,
                "39"      : Curses.Colors.DEFAULT,
            }

            bg_colors = {
                "40"      : Curses.Colors.BLACK,
                "41"      : Curses.Colors.RED,
                "42"      : Curses.Colors.GREEN,
                "43"      : Curses.Colors.YELLOW,
                "44"      : Curses.Colors.BLUE,
                "45"      : Curses.Colors.MAGENTA,
                "46"      : Curses.Colors.CYAN,
                "47"      : Curses.Colors.WHITE,
                "49"      : Curses.Colors.DEFAULT,
            }

            attributes = {
                "1"       : Curses.Modes.BOLD,
                "2"       : Curses.Modes.DIM,
                "22"      : Curses.Modes.NORMAL,
            }

            # Extract the escape sequence.
            sequence = self.regex.match(text[position:]).group(0)
            position += len(sequence)

            # Remove everything which is unimportant.
            sequence = sequence[len("\033["):-len("m")]

            # Interpret the sequence
            fg = Curses.Colors.DEFAULT
            bg = Curses.Colors.DEFAULT

            for option in sequence.split(";"):
                if option in fg_colors:
                    fg = fg_colors[option]
                elif option in bg_colors:
                    bg = bg_colors[option]
                elif option in attributes:
                    window._window.attron(attributes[option])
                elif option == "0":
                    # Reset all
                    window._window.attrset(0)
                    fg = Curses.Colors.DEFAULT
                    bg = Curses.Colors.DEFAULT
                else:
                    # TODO: Handle gracefully.
                    pass

            # At the end set the color.
            window._window.attron(Curses.get_color_pair(fg, bg))

            return position

        def clean_up(self, window):
            # Clear all colors again.
            window._window.attrset(0)


    class MoveInterpreter(SequenceInterpreter):
        regex = re.compile(r"\033\[([0-9]+);([0-9]+)H")

        def can_interpret(self, text, position):
            return self.regex.match(text[position:]) is not None

        def interpret(self, text, position, window):
            sequence = self.regex.match(text[position:]).group(0)
            position += len(sequence)

            # Remove everything which is unneeded.
            sequence = sequence[len("\033["):-len("H")]

            # Interpret the sequence.
            (y, x) = sequence.split(";")
            (width, height) = window.dimension

            if x >= 0 and y >= 0 and x < width and y < height:
                window._window.move(y, x)
            else:
                # TODO: Handle gracefully.
                pass

            return position

        def clean_up(self, window):
            # Nothing to do here.
            pass


    class ClearInterpreter(SequenceInterpreter):
        regex = re.compile(r"\033\[[0-9]J")

        def can_interpret(self, text, position):
            return self.regex.match(text[position:]) is not None

        def interpret(self, text, position, window):
            modes = {
                "2" : window._window.clear
            }

            sequence = self.regex.match(text[position:]).group(0)
            position += len(sequence)

            # Remove everything which is unneeded.
            sequence = sequence[len("\033["):-len("J")]

            if sequence in modes:
                modes[sequence]()
            else:
                # TODO: Handle gracefully
                pass

            return position

        def clean_up(self, window):
            # Nothing to do here.
            pass


    class GraphicsInterpreter(SequenceInterpreter):
        regex = re.compile(r"\033(\(|\))(A|B|0|1|2).\033(\(|\))(A|B|0|1|2)")

        def can_interpret(self, text, position):
            return self.regex.match(text[position:]) is not None

        def interpret(self, text, position, window):
            graphisc = {
                "\x71"  : curses.ACS_HLINE,
                "\x78"  : curses.ACS_VLINE,
                "\x6A"  : curses.ACS_LRCORNER,
                "\x6B"  : curses.ACS_URCORNER,
                "\x6C"  : curses.ACS_ULCORNER,
                "\x6D"  : curses.ACS_LLCORNER,
                "\x6E"  : curses.ACS_PLUS,
                "\x74"  : curses.ACS_LTEE,
                "\x75"  : curses.ACS_RTEE,
                "\x76"  : curses.ACS_BTEE,
                "\x77"  : curses.ACS_TTEE
            }

            sequence = self.regex.match(text[position:]).group(0)
            position += len(sequence)

            # Remove everything which is unneeded.
            sequence = sequence[len("\033(0"):-len("\033(B")]

            if sequence in graphisc:
                window._window.addch(graphisc[sequence])
            else:
                # TODO: Handle gracefully.
                pass

            return position

        def clean_up(self, window):
            # Nothing to do here.
            pass


    def __init__(self, window, parent = None):
        self._parent = parent
        self._window = window

        self._timeout = -1

    def clear(self, refresh = True):
        self._window.clear()

        if refresh:
            self.refresh()

    def clear_line(self, line_nr, refresh = True):
        (old_y, old_x) = self._window.getyx()

        self._window.move(line_nr, 0)
        self._window.clrtoeol()

        self._window.move(old_y, old_x)

        if refresh:
            self.refresh()

    @property
    def cursor_pos(self):
        (y, x) = self._window.getyx()

        return (x, y)

    @property
    def dimension(self):
        (height, width) = self._window.getmaxyx()

        return (width, height)

    def timeout(self, timeout):
        if self._timeout != timeout:
            self._window.timeout(timeout)
            self._timeout = timeout

    def get_user_input(self, timeout=-1):
        self.timeout(timeout)
        user_input = self._window.getch()

        if not user_input in list(Curses.Keys) and \
                user_input < curses.KEY_MIN:
            # Convert the int which curses returns to a string if no definition
            # is already given for it and if it is an ASCII symbol.
            user_input = str(chr(user_input))

        return user_input

    def pretty_print(self, string = "", pos = None, refresh = True,
            fg = None, bg = None, modes = []):
        if fg is None:
            fg = Curses.Colors.DEFAULT
        if bg is None:
            bg = Curses.Colors.DEFAULT

        # First reset all attributes
        self._window.attrset(0)

        # Mode
        for mode in modes:
            self._window.attron(mode)

        # Color
        self._window.attron(Curses.get_color_pair(fg, bg))

        complete = self.print(string, pos, refresh)

        # Reset all attributes again
        self._window.attrset(0)

        return complete

    def print(self, string = "", pos = None, refresh = True):
        complete = True
        width, height = self.dimension

        if pos is not None:
            x, y = pos
            self._window.move(int(y), int(x))

        # Print the string line wise until the end of the string or the screen.
        for line in string.splitlines(keepends=True):
            # Check if the line still fits in the screen before displaying it.
            cur_x, cur_y = self.cursor_pos
            length = len(line)

            new_y = cur_y + int((cur_x + length) / width)

            # Where are we on the screen?
            if new_y < height - 1:
                # Still enough height - print with newline.
                self._window.addstr(line.encode(Curses.encoding))
            elif new_y == height - 1:
                # Last line on the screen - leave the newline out.
                self._window.addstr((line.rstrip()).encode(Curses.encoding))

                complete = False
                break
            else:
                # Overflowing screen so just print what still fits on it.
                end = (width - cur_x) + ((height - 1) - cur_y) * width

                self._window.addstr(line[:end].encode(Curses.encoding))
                complete = False
                break

        if refresh:
            self.refresh()

        return complete

    def refresh(self):
        if self._parent is not None:
            self._parent.refresh()

        self._window.refresh()

    def new_window(self, x = 0, y = 0, width = None, height = None):
        w, h = self.dimension

        if width is None:
            width = w - x
        if height is None:
            height = h - y

        if x < 0 or x > w:
            raise ValueError("x is out of range")
        if y < 0 or y > h:
            raise ValueError("y is out of range")
        if width < 0 or width > (w - x):
            raise ValueError("width is out of range")
        if height < 0 or height > (h - y):
            raise ValueError("height is out of range")

        return Window(Curses.new_window(x, y, width, height), self)

    def safe_print(self, string = "", pos = None, refresh = True):
        """
        Print a string at a given position but also interpret escape sequences
        as well as other non-ASCII characters.
        """
        interpreters = [
            Window.ModeInterpreter(),
            Window.MoveInterpreter(),
            Window.ClearInterpreter(),
            Window.GraphicsInterpreter(),
            Window.DefaultInterpreter()
        ]

        if pos is not None:
            x, y = pos
            self._window.move(int(y), int(x))

        cur_pos = 0
        complete = True
        cur_interpreter = Window.DefaultInterpreter()

        while cur_pos < len(string):
            # Try to find the next escape sequence.
            try:
                esc_seq = string.index('\033', cur_pos)

                # Print everything until the sequence.
                next_to_print = string[cur_pos:esc_seq]
                if len(next_to_print) > 0 and \
                        not self.print(next_to_print, refresh=False):
                    # Leave the loop, as the print method indicated that the
                    # screen is full.
                    complete = False
                    break

                # Reset what the previous interpreter did set.
                cur_interpreter.clean_up(self)

                # Find the proper interpreter for the given sequence.
                for interpreter in interpreters:
                    if interpreter.can_interpret(string, esc_seq):
                        cur_interpreter = interpreter
                        break

                # Interpret the sequence.
                cur_pos = cur_interpreter.interpret(string, esc_seq, self)
            except ValueError:
                # Print the rest of the string.
                complete = self.print(string[cur_pos:], refresh=False)

                # Leave the loop as everything is printed.
                break

        # Clear all colors and attributes.
        self._window.attrset(0)

        # Refresh if requested.
        if refresh:
            self.refresh()

        return complete

    def wait_for_input(self, reactions = {}, timeout=-1):
        while True:
            user_input = self.get_user_input(timeout)

            if user_input in reactions:
                # If there is a reaction already predefined use it.
                reactions[user_input]()

            else:
                # Else give the user the possibility to react.
                yield user_input

    def move(self, new_x, new_y):
        """
        Move the window to a new location on the screen.
        """
        self._window.mvwin(int(new_y), int(new_x))

        return self

    def resize(self, new_width, new_height):
        """
        Resize the window to the new given size.
        """
        self._window.resize(int(new_height), int(new_width))

        return self
