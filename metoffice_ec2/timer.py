import logging
import time

_LOG = logging.getLogger("metoffice_ec2")


class Timer:
    def __init__(self):
        self.t = time.time()

    def tick(self, label=""):
        now = time.time()
        time_since_last_tick = now - self.t
        self.t = now
        _LOG.info("{} took {:.2f} secs.".format(label, time_since_last_tick))
