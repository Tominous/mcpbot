import time
import socket
import re
from Queue import Empty


_LINESEP_REGEXP = re.compile(r'\r?\n')


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
                continue
            try:
                msg = self.out_msg.get(True, 1)
            except Empty:
                continue
            self.out_msg.task_done()
            if self.rawmsg:
                self.log('> %s' % repr(msg))
            out_line = msg + '\r\n'
            if len(out_line) > int(allowed_chars):
                time.sleep((len(out_line) * 1.25) / (self.floodprotec / 30.0))
            try:
                self.irc_socket.send(out_line)
                allowed_chars -= len(out_line)
            except socket.timeout:
                self.out_msg.put(msg)
                continue

    def inbound_loop(self):
        """Incoming message thread. Check for new data on the socket and push the data to the dispatcher queue if any."""
        buf = ''
        while not self.exit:
            if not self.irc_socket:
                print 'no socket'
                continue

            # breaks with error: [Errno 104] Connection reset by peer
            try:
                new_data = self.irc_socket.recv(512)
            except socket.timeout:
                continue
            if not new_data:
                continue

            msg_list = _LINESEP_REGEXP.split(buf + new_data)

            # Push last line back into buffer in case its truncated
            buf = msg_list.pop()

            for msg in msg_list:
                if self.rawmsg:
                    self.log('< %s' % repr(msg))
                self.in_msg.put(msg)

    def print_loop(self):
        """Loop to handle console output. Only way to have coherent output in a threaded environement.
        To output something to the console, just push it on the printq queue (self.printq.put('aaa') or self.bot.printq('aaa') from inside the procotols."""
        while not self.exit:
            try:
                msg = self.printq.get(True, 1)
            except Empty:
                continue
            self.printq.task_done()
            print msg

    def logging_loop(self):
        while not self.exit:
            try:
                ev = self.loggingq.get(True, 1)
            except Empty:
                continue

            c = self.acquiredb()
            try:
                c.execute("""INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?, ?)""", (None, ev.type, ev.cmd, ev.sender, ev.target, ev.msg, int(time.time())))
            except Exception:
                pass
            self.releasedb(c)
