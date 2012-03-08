import time
import socket
import re
import sqlite3
from Queue import Empty


LINESEP_REGEXP = re.compile(r'\r?\n')


class IRCBotIO(object):
    def outbound_loop(self):
        """Outgoing messages thread. Check for new messages on the queue and push them to the socket if any."""
        # This is how the flood protection works :
        # We have a char bucket corresponding of the max number of chars per 30 seconds
        # Every looping, we add chars to this bucket corresponding to the time elapsed in the last loop * number of allowed char / second
        # If when we want to send the message and the number of chars is not enough, we sleep until we have enough chars in the bucket (in fact, a bit more, to replanish the bucket).
        # This way, everything slow down when we reach the flood limit, but after 30 seconds, the bucket is full again.

        allowed_chars = self.floodprotec
        start_time = time.time()
        while not self.exit:
            delta_time = time.time() - start_time
            allowed_chars = min(allowed_chars + (self.floodprotec / 30.0) * delta_time, self.floodprotec)
            start_time = time.time()

            if not self.irc_socket:
                self.log('*** IRCBotIO.outbound_loop: no socket')
                continue

            try:
                msg = self.out_msg.get(True, 1)
            except Empty:
                continue

            if self.rawmsg:
                self.log('> %s' % repr(msg))
            out_line = msg + '\r\n'
            if len(out_line) > int(allowed_chars):
                time.sleep((len(out_line) * 1.25) / (self.floodprotec / 30.0))
            try:
                self.irc_socket.send(out_line)
            except socket.timeout as exc:
                self.log('*** IRCBotIO.outbound_loop: socket.timeout: %s' % exc)
                self.out_msg.put(msg)
                self.out_msg.task_done()
                continue
            allowed_chars -= len(out_line)
            self.out_msg.task_done()


    def inbound_loop(self):
        """Incoming message thread. Check for new data on the socket and send the data to the irc protocol handler."""
        buf = ''
        while not self.exit:
            if not self.irc_socket:
                self.log('*** IRCBotIO.inbound_loop: no socket')
                continue

            # breaks with error: [Errno 104] Connection reset by peer
            try:
                new_data = self.irc_socket.recv(512)
            except socket.timeout as exc:
                continue
            if not new_data:
                self.log('*** IRCBotIO.inbound_loop: no data')
                continue

            msg_list = LINESEP_REGEXP.split(buf + new_data)

            # Push last line back into buffer in case its truncated
            buf = msg_list.pop()

            for msg in msg_list:
                if self.rawmsg:
                    self.log('< %s' % repr(msg))
                self.irc.process_msg(msg)

    def print_loop(self):
        """Loop to handle console output. Only way to have coherent output in a threaded environement."""
        while not self.exit:
            try:
                msg = self.printq.get(True, 1)
            except Empty:
                continue
            print msg
            self.printq.task_done()

    def logging_loop(self):
        with sqlite3.connect(self.dbconf) as db:
            db.text_factory = str
            while not self.exit:
                try:
                    ev = self.loggingq.get(True, 1)
                except Empty:
                    continue

                db.execute("""INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (None, ev.type, ev.cmd, ev.sender, ev.target, ev.msg, int(time.time())))
                db.commit()
                self.loggingq.task_done()

