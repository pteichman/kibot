import sys
import os
import os.path
import socket
import signal
import telnetlib
import time

import kibot.Options
import kibot.OptionParser

def main():
    import kibot.Bot
    bot = kibot.Bot.Bot()

DEBUG=0
def dblog(message):
    if DEBUG: sys.stderr.write(message + '\n')

class UNIXTelnet(telnetlib.Telnet):
    """telnet to a unix socket rather than an inet socket"""

    def open(self, host, port=0):
        """Connect to a host.

        here, host is the filename of the unix socket.  port is ignored
        """
        self.eof = 0
        self.host = host
        self.port = port
        msg = "getaddrinfo returns an empty list"
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(host)
        except socket.error, msg:
            if self.sock:
                self.sock.close()
            self.sock = None
            raise

###########################################################
def get_options(cmd_line):
    o = kibot.OptionParser.OptionParser()
    o = kibot.Options.fill_options(o)
    o.add('bool',   'kill',   '', 'kill',   0)
    o.add('bool',   'reload', '', 'reload', 0)
    o.add('bool',   'pid',    '', 'pid',    0)
    o.add('string', 'signal', '', 'signal', None)
    defaults = o.load_defaults()
    command_line = o.load_getopt(cmd_line)
    tmp = o.overlay([defaults, command_line])
    config_file = os.path.join(tmp.files.base_dir, tmp.files.conf_file)
    file_ops = o.load_ConfigParser(config_file)
    final = o.overlay([defaults, file_ops, command_line])
    kibot.Options.munge_options(final)

    dc_addr = final.admin.dc_addr
    pidfile = final.admin.lockfile

    args = command_line._args
    # for backwards compatibility...
    if args: dc_addr = args.pop(0)

    if final.help:
        dohelp()

    if args:
        sys.exit('Unrecognized option(s): %s' % ' '.join(args))

    return (final, dc_addr, pidfile)

def dohelp():
    sys.stderr.write(
"""kibot-control -- administrative control program for kibot

Usage: kibot-control [options] [DC address]
  -h, --help                print this help message
  -C FILE, --conf=FILE      config file - defaults to kibot.conf
  -b VAL, --base-dir=VAL    kibot base directory
  --lockfile=VAL            file where pid is written
  --dc-addr=VAL             DC address (filename for unix, host:port for inet)
  --kill                    kill the bot, gently if possible
  --reload                  ask the bot to reload its config
  --pid                     print the pid of the bot
  --signal=VAL              send signal VAL to the bot
""")
    sys.exit()

def kibot_control():
    try:
        op, dc_addr, pidfile = get_options(sys.argv[1:])
    except kibot.OptionParser.OptionError, e:
        sys.exit('error: %s' % str(e))

    command = []
    if op.kill: command.append('kill')
    if op.reload: command.append('reload')
    if op.pid: command.append('pid')
    if not op.signal is None: command.append('signal')
    if len(command) > 1:
        sys.exit('You can only use one of: --kill, --reload, --pid, and --signal')

    if not command:
        dc_connect(dc_addr)
        sys.exit()
    else:
        command = command[0]

    pid = _get_pid(pidfile)
    if command == 'signal':
        sig = _parse_signal(op.signal)
        dblog('sending signal %i to %i' % (sig, pid))
        os.kill(pid, sig)
    elif command == 'pid':
        print pid
    elif command == 'reload':
        os.kill(pid, signal.SIGHUP)
    elif command == 'kill':
        kill_bot(pid)
    else:
        # this should never happen
        sys.exit('Unknown command: %s' % command)

def kill_bot(pid):
    dblog('sending SIGTERM to %i' % pid)
    os.kill(pid, signal.SIGTERM)
    step = 0.2
    wait = 30
    start = time.time()
    while 1:
        if not os.path.exists('/proc/%i' % pid):
            break
        if time.time() - start > wait:
            dblog('sending SIGKILL')
            os.kill(pid, signal.SIGKILL)
            break
        
def _get_pid(pidfile):
    try: fo = open(pidfile)
    except IOError, e:
        sys.exit('FATAL: Could not read pidfile: %s\n       %s' \
                 % (pidfile, e.args[1]))
    pid = int(fo.read())
    fo.close()
    return pid

def _parse_signal(sig):
    try:
        numsig = int(sig)
    except ValueError, e:
        sig = sig.upper()
        numsig = getattr(signal, sig, None)
        if numsig is None:
            numsig = getattr(signal, 'SIG'+sig, None)
    dblog('numsig: %i' % numsig)
    return numsig

def dc_connect(dc_addr):
        host = ''
        dblog('DC address: %s' % dc_addr)
        if type(dc_addr) == type('') and ':' in dc_addr:
            host, port = dc_addr.split(':', 1)
        else:
            port = dc_addr
                
        try:
            port = int(port)
        except ValueError, e:
            ctype = 'unix'
            host, port = dc_addr, 0
            addr = host
        else:
            ctype = 'inet'
            lastslash = host.rindex('/')
            host = host[lastslash+1:]
            addr = '%s:%s' % (host, port)
            
        if ctype == 'unix': tn = UNIXTelnet()
        else:               tn = telnetlib.Telnet()

        try:
            tn.open(host, port)
        except socket.error, e:
            sys.exit('FATAL: Failed to connect to %s socket %s\n       %s' \
                     % (ctype, addr, str(e.args[1])))
        print 'connecting on %s socket %s' % (ctype, addr)
        tn.interact()
        tn.close()

if __name__ == '__main__':
    kibot()
