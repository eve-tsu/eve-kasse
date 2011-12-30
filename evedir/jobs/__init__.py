import logging
from multiprocessing import Process as VanillaProcess
import signal

from anzu.options import options

__all__ = ['Process']

class Process(VanillaProcess):

    def run(self):
        try:
            super(Process, self).run()
        except KeyboardInterrupt:
            pass
        except Exception, e:
            if not self.exitcode == -signal.SIGTERM:
                logging.exception("Unhandled exception %s (signal is %r)", e, self.exitcode)
                if options.debug:
                    raise
                else:
                    super(Process, self).run()

    # _bootstrap is not overwritten: we let the useless and harmless error messages be displayed

