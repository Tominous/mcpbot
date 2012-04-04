import sqlite3
import threading

from contextlib import contextmanager


class DBHandler(object):
    def __init__(self, db_name):
        self._db_lock = threading.Lock()
        self.db_name = db_name

    @contextmanager
    def get_db(self):
        with self._db_lock:
            with sqlite3.connect(self.db_name) as db:
                db.text_factory = sqlite3.OptimizedUnicode
                db.row_factory = sqlite3.Row
                yield db
