import logging
from Queue import Queue
from threading import Thread


class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks):
        Thread.__init__(self)
        self.ncalls = 0
        self.nscalls = 0
        self.nfcalls = 0
        self.tasks = tasks
        self.logger = logging.getLogger('IRCBot.ThreadPool')
        self.daemon = True
        self.start()

    def run(self):
        while True:
            func, args, kargs = self.tasks.get()
            if '_threadname' in kargs:
                self.name = kargs.pop('_threadname')
            self.ncalls += 1
            try:
                func(*args, **kargs)  # pylint: disable-msg=W0142
                self.nscalls += 1
            except Exception:  # pylint: disable-msg=W0703
                self.nfcalls += 1
                self.logger.exception('ERROR in %s', self.name)
            self.tasks.task_done()


class ThreadPool(object):
    """Pool of threads consuming tasks from a queue"""
    def __init__(self, num_threads):
        self.logger = logging.getLogger('IRCBot.ThreadPool')
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks)

    def add_task(self, func, *args, **kargs):
        """Add a task to the queue"""
        self.tasks.put((func, args, kargs))

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue"""
        self.logger.info('waiting for threads')
        self.tasks.join()
