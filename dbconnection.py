import sqlite3
import threading

from contextlib import contextmanager, closing


class DBConnection(object):
    def __init__(self, db_name):
        self._db_lock = threading.Lock()
        self.db_name = db_name

    @contextmanager
    def get_cursor(self):
        with self._db_lock:
            with sqlite3.connect(self.db_name) as con:
                con.text_factory = sqlite3.OptimizedUnicode
                with closing(con.cursor()) as cur:
                    yield cur
