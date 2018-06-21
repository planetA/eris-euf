import sys
import os
from os.path import join
from datetime import datetime

def read_file(path):
    with open(path) as f:
        return f.read().strip()


class RAPLCounter:
    class Counter:
        def __init__(self, base_path):
            self.name = read_file(join(base_path, "name"))
            self.uj = int(read_file(join(base_path, "energy_uj")))
            self.max = int(read_file(join(base_path, "max_energy_range_uj")))
            self.timestamp = datetime.now()

        @property
        def joules(self):
            return self.uj / 1000000

    class DomainCounters:
        def __init__(self, base_path):
            self.timestamp = datetime.now()
            self._values = {}

            pkg_ctr = RAPLCounter.Counter(base_path)
            self._values[pkg_ctr.name] = pkg_ctr

            for entry in os.scandir(base_path):
                if entry.name.startswith("intel-rapl:"):
                    ctr = RAPLCounter.Counter(entry.path)
                    self._values[ctr.name] = ctr

        def counters(self):
            return self._values.keys()

        def counter(self, ctr):
            return self._values[ctr]

        def items(self):
            return self._values.items()

    def __init__(self):
        self._values = {}
        self.timestamp = datetime.now()

        if not os.path.exists("/sys/class/powercap/intel-rapl"):
            raise ValueError("No RAPL sysfs interface available")

        for entry in os.scandir("/sys/class/powercap/intel-rapl"):
            if entry.name.startswith("intel-rapl:"):
                domain = int(entry.name[len("intel-rapl:"):])
                d_values = RAPLCounter.DomainCounters(entry.path)

                self._values[domain] = d_values

    def __sub__(self, other):
        return self.diff(other)

    def domains(self):
        return self._values.keys()

    def domain(self, domain):
        return self._values[domain]

    def items(self):
        return self._values.items()

    def diff(self, other):
        if self.timestamp < other.timestamp:
            return RAPLCounterDiff(self, other)
        else:
            return RAPLCounterDiff(other, self)


class RAPLCounterDiff:
    class Counter:
        def __init__(self, earlier, later):
            self.timediff = later.timestamp - earlier.timestamp
            self.timestamp = later.timestamp

            self.name = later.name
            self.max = later.max
            if later.uj < earlier.uj:
                self.uj = max_val - earlier.uj + later.uj
            else:
                self.uj = later.uj - earlier.uj

        @property
        def joules(self):
            return self.uj / 1000000

        @property
        def uwatts(self):
            return self.uj / self.timediff.total_seconds()

        @property
        def watts(self):
            return self.joules / self.timediff.total_seconds()

    class DomainCounters:
        def __init__(self, earlier, later):
            self.timestamp = later.timestamp
            self.timediff = later.timestamp - earlier.timestamp

            self._values = {}

            for n, ec in earlier.items():
                lc = later.counter(n)

                self._values[n] = RAPLCounterDiff.Counter(ec, lc)

        def counters(self):
            return self._values.keys()

        def counter(self, ctr):
            return self._values[ctr]

        def items(self):
            return self._values.items()

    def __init__(self, earlier, later):
        self.timestamp = later.timestamp
        self.timediff = later.timestamp - earlier.timestamp

        self._values = {}

        for d, edc in earlier.items():
            ldc = later.domain(d)

            self._values[d] = RAPLCounterDiff.DomainCounters(edc, ldc)

    def domains(self):
        return self._values.keys()

    def domain(self, domain):
        return self._values[domain]

    def items(self):
        return self._values.items()
