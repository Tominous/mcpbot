from irc_lib.utils.irc_name import get_nick
from commands  import DCCCommands
from rawevents import DCCRawEvents
from irc_lib.IRCBotError import IRCBotError
from irc_lib.protocols.event import Event
from irc_lib.protocols.user import User
from Queue import Queue,Empty
import socket
import thread
import time
import urllib
import select
import traceback

class DCCSocket(object):
    def __init__(self, socket, nick):
        self.buffer = ''
        self.socket = socket
        self.nick   = nick
    
    def fileno(self):
        return self.socket.fileno()

class DCCProtocol(DCCCommands, DCCRawEvents):

    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):
        self.cnick           = _nick
        self.out_msg         = _out_msg
        self.in_msg          = _in_msg
        self.bot             = _bot
        self.locks           = _locks
        
        self.sockets         = {}
        self.ip2nick         = {}

        self.insocket      = socket.socket()
        try:
            self.insocket.listen(10)
            #self.insocket.setblocking(0)
            self.inip, self.inport = self.insocket.getsockname()
            self.inip = self.conv_ip_std_long(urllib.urlopen('http://www.whatismyip.com/automation/n09230945.asp').readlines()[0])
        except socket.error:
            self.bot.printq.put("If you see this, it means you can't create listening sockets. This is a bug from Iron Python. Desactivating dcc.")

        self.bot.threadpool.add_task(self.treat_msg, _threadname='DCCHandler')        
        self.bot.threadpool.add_task(self.inbound_loop, _threadname='DCCInLoop')        

    def treat_msg(self):
        while not self.bot.exit:
            try:
                msg = self.in_msg.get(True, 1)
            except Empty:
                continue  
            self.in_msg.task_done()

            msg = msg.strip()
            if not msg:
                continue

            msg = msg.split()
            
            sender   = get_nick(msg[0])
            cmd      = msg[1]
            destnick = msg[2]
            dcchead  = msg[3][2:]
            dcccmd   = msg[4]
            if len(msg) > 5:
                dccarg   = msg[5]
                dccip    = msg[6]
                dccport  = msg[7][:-1]
            else:
                dccarg   = ''
                dccip    = ''
                dccport  = ''

            if cmd not in ['PRIVMSG', 'NOTICE']:
                raise IRCBotError('Invalid command from DCC : %s'%msg)
                
            if hasattr(self, 'onRawDCC%s'%dcccmd):
                self.bot.threadpool.add_task(getattr(self, 'onRawDCC%s'%dcccmd),sender, dcccmd, dccarg, dccip, dccport)
            else:
                self.bot.threadpool.add_task(getattr(self, 'onRawDCCDefault'),sender, dcccmd, dccarg, dccip, dccport)

            if hasattr(self.bot, 'onDCC%s'%dcccmd):
                self.bot.threadpool.add_task(getattr(self.bot, 'onDCC%s'%dcccmd),sender, dcccmd, dccarg, dccip, dccport)
            else:
                self.bot.threadpool.add_task(getattr(self.bot, 'onDefault'),msg[0], cmd, ' '.join(msg[2:]))

    def conv_ip_long_std(self,longip):
            
        hexip = hex(longip)[2:-1]
        if len(hexip) != 8:
            print 'Error !'
            return '0.0.0.0'
        part1 = int(hexip[0:2], 16)
        part2 = int(hexip[2:4], 16)
        part3 = int(hexip[4:6], 16)
        part4 = int(hexip[6:8], 16)
        ip    = '%s.%s.%s.%s'%(part1, part2, part3, part4)
            
        return ip

    def conv_ip_std_long(self,stdip):
        ip = stdip.split('.')
        hexip ='%2s%2s%2s%2s'%(hex(int(ip[0]))[2:],
              hex(int(ip[1]))[2:],
              hex(int(ip[2]))[2:],
              hex(int(ip[3]))[2:])
        hexip  = hexip.replace(' ', '0')
        longip = int(hexip,16)
        
        return longip

    def inbound_loop(self):
        input = [self.insocket] 
        while not self.bot.exit:
            inputready,outputready,exceptready = select.select(input,[],[],5) 
                    
            for s in inputready:

                if s == self.insocket:
                    self.bot.printq.put('> Received connection request') 
                    # handle the server socket
                    buffsocket, buffip = self.insocket.accept()
                    self.bot.printq.put('> User identified as : %s %s'%(self.ip2nick[buffip[0]], buffip[0]))
                    self.sockets[self.ip2nick[buffip[0]]] = DCCSocket(buffsocket, self.ip2nick[buffip[0]])
                    self.say(self.ip2nick[buffip[0]], 'Connection with user %s established.\r\n'%self.ip2nick[buffip[0]])
                    input.append(self.sockets[self.ip2nick[buffip[0]]])
                        
                else:
                    # handle all other sockets
                    try:
                        data = s.socket.recv(512)
                    except socket.error, msg:
                        if 'Connection reset by peer' in msg:
                            self.bot.printq.put('> Connection closed with : %s'%s.nick) 
                            del self.sockets[s.nick]
                            s.socket.close()
                            input.remove(s)
                            continue
                    if data:
                        s.buffer += data

                        if self.bot.rawmsg:
                            self.bot.printq.put('< ' + s.buffer)                    

                        print r'>%s<'%s.buffer
                        if not s.buffer.strip():
                            s.buffer = ''
                            continue
                                
                        msg_list = s.buffer.splitlines()

                        #We push all the msg beside the last one (in case it is truncated)
                        for msg in msg_list:
                            ev = Event(s.nick, 'DCCMSG', self.cnick, msg.strip(), self.cnick, 'DCCMSG')
                            self.bot.threadpool.add_task(self.onRawDCCMsg,ev)
                            if hasattr(self.bot, 'onDCCMsg'): 
                                self.bot.threadpool.add_task(self.bot.onDCCMsg,ev)
                            else: 
                                self.bot.threadpool.add_task(self.bot.onDefault,ev)
                                
                        s.buffer = ''                    
                                
                    else:
                        self.bot.printq.put('> Connection closed with : %s'%s.nick) 
                        del self.sockets[s.nick]
                        s.socket.close()
                        input.remove(s)
