import sqlite3
import threading

from contextlib import contextmanager


class DBConnection(object):
    def __init__(self, db_name):
        self._db_lock = threading.Lock()
        self.db_name = db_name

    @contextmanager
    def get_db(self):
        with self._db_lock:
            db = sqlite3.connect(self.db_name)
            db.text_factory = sqlite3.OptimizedUnicode
            db.row_factory = sqlite3.Row
            try:
                yield db
                db.rollback()
            except BaseException as exc:
                try:
                    db.rollback()
                except sqlite3.Error:
                    pass
                raise exc
