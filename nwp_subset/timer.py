import time
import logging


_LOG = logging.getLogger('nwp_subset')


class Timer:
    def __init__(self):
        self.t = time.time()

    def tick(self, label=''):
        now = time.time()
        time_since_last_tick = now - self.t
        self.t = now
        _LOG.info('{} took {:.2f} secs.'.format(label, time_since_last_tick))
