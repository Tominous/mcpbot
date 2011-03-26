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

class DCCProtocol(DCCCommands, DCCRawEvents):

    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):
        self.cnick           = _nick
        self.out_msg         = _out_msg
        self.in_msg          = _in_msg
        self.bot             = _bot
        self.locks           = _locks
        
        self.sockets         = {}
        self.buffers         = {}
        self.ip2nick         = {}

        self.insocket      = socket.socket()
        try:
            self.insocket.listen(10)
            self.insocket.setblocking(0)
            self.inip, self.inport = self.insocket.getsockname()
            self.inip = self.conv_ip_std_long(urllib.urlopen('http://www.whatismyip.com/automation/n09230945.asp').readlines()[0])
        except socket.error:
            self.bot.printq.put("If you see this, it means you can't create listening sockets. This is a bug from Iron Python. Desactivating dcc.")

        self.bot.threadpool.add_task(self.treat_msg)        
        self.bot.threadpool.add_task(self.inbound_loop)        

    def treat_msg(self):
        while not self.bot.exit:
            try:
                msg = self.in_msg.get(True, 1)
            except Empty:
                continue  
            self.in_msg.task_done()

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
        while not self.bot.exit:
            try:
                if not self.insocket : raise socket.error
                buffsocket, buffip = self.insocket.accept()
                self.sockets[self.ip2nick[buffip[0]]] = buffsocket
                self.sockets[self.ip2nick[buffip[0]]].setblocking(0)
                self.say(self.ip2nick[buffip[0]], 'Connection with user %s established.\r\n'%self.ip2nick[buffip[0]])
            except socket.error as msg:
                pass

            for nick, isocket in self.sockets.items():
                if not isocket:continue
                if not nick in self.buffers: self.buffers[nick]=''

                try:
                    self.buffers[nick]  += isocket.recv(512)
                except socket.error as msg:
                    continue
                msg_list = self.buffers[nick].splitlines()

                #We push all the msg beside the last one (in case it is truncated)
                for msg in msg_list:
                    ev = Event(nick, 'DCCMSG', self.cnick, msg.strip(), self.cnick, 'DCCMSG')
                    self.bot.threadpool.add_task(self.onRawDCCMsg,ev)
                    if hasattr(self.bot, 'onDCCMsg'): 
                        self.bot.threadpool.add_task(self.bot.onDCCMsg,ev)
                    else: 
                        self.bot.threadpool.add_task(self.bot.onDefault,ev)
                
                self.buffers[nick] = ''

            time.sleep(.1)
