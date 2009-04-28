import traceback
import sys
import os
import os.path
import string
import time
import signal

import kibot.timeoutsocket

import kibot.logger
import kibot.daemon
import kibot.m_irclib
from kibot.m_irclib import Timer

import kibot.Options
import kibot.BaseModule
import kibot.ircDB
import kibot.permDB
import kibot.CommandHandler
import kibot.ModuleManager

"""
handler priorities:
  < 0   internal bot functions
  = 0   fastest module function
  = 10  "automatic" module functions
"""
class Bot:
    def __init__(self):
        # options
        self.op = kibot.Options.options(sys.argv[1:])
        sys.path = self.op.files.py_path + sys.path

        self.lock() # this also daemonizes, if using --daemon

        self.init_logging()
        self.log(1, 'Starting up at: %s' % (time.asctime(), ))
        self.log.write(5, 'CONFIG:\n%s' % self.op)

        self.log(5, 'Setting socket timeout to %s seconds' % \
                 self.op.admin.timeout)
        kibot.timeoutsocket.setDefaultSocketTimeout(self.op.admin.timeout)

        if not os.path.exists(self.op.files.data_dir):
            try: os.makedirs(self.op.files.data_dir)
            except os.error, msg:
                self.log(0, 'FATAL: could not create data dir: %s' % str(msg))
                sys.exit(1)

        self.setup_connections()
        self.load_core_modules()
        self.set_signal_handlers()
        
        try: self.connect()
        except kibot.irclib.ServerConnectionError, msg:
            self.log(0, "FATAL: Couldn't connect to server: '%s:%i'" % \
                     (self.op.irc.server, self.op.irc.port))
            self.log(0, "       " + str(msg))
            sys.exit(1)
            
        try:
            self.ircobj.process_forever()
        except KeyboardInterrupt, msg:
            self.log(1, "EXITING: SIGINT received")
            self.dcm.close()
            self.unlock()
            raise SystemExit
        except SystemExit, msg:
            self.dcm.close()
            self.unlock() # perhaps could tidy the locking on restert,
            # especially, with daemonizing thrown in the mix
            if msg.code == 'restart': self.restart()
            raise SystemExit
        except:
            self.dcm.close()
            self.unlock()
            traceback.print_exc()

    def restart(self):
        os.execv(sys.argv[0], sys.argv)

    def init_logging(self):
        loggers = []
        for level, filename in zip(self.op.admin.debug, self.op.admin.logfile):
            try: level = int(level)
            except ValueError:
                sys.stderr.write('debug level must be an integer: %s' % level)
                sys.exit(1)
            if filename == '-': fo = sys.stdout
            else: fo = open(filename, 'a', 1)
            printtime = lambda : time.strftime('%Y-%m-%d %H:%M:%S ',
                                               time.localtime(time.time()))
            loggers.append(kibot.logger.Logger(threshold=level, file_object=fo,
                                               preprefix=printtime))
        kibot.m_irclib.log = self.log = kibot.logger.LogContainer(loggers)

    def lock(self):
        # set self._true_lockfile because it may be possible in later
        # versions to re-scan the config file while running.
        lf = self._true_lockfile = self.op.admin.lockfile
        kibot.daemon.cleanup_old_lockfile(lf)
        # check and get the lockfile BEFORE we daemonize, so we can write
        # to STDERR if we need to
        try:
            lockfd = kibot.daemon.lock_fd(lf)
        except OSError, e:
            sys.exit('FATAL: cannot create lockfile: %s' % str(e))
        if lockfd is None:
            sys.exit('FATAL: lockfile exists: %s' % lf)
        if self.op.admin.daemon:
            kibot.daemon.daemonize('/dev/null', '/tmp/kibot', '/tmp/kibot')
            os.umask(self.op.admin.umask)
        # now write to it with our NEW pid
        os.write(lockfd, str(os.getpid()))
        os.close(lockfd)

    def setup_connections(self):
        # server connection
        self.ircobj = kibot.m_irclib.IRC()
        self.conn = self.ircobj.server()

        # direct connections
        addr = self.op.admin.dc_addr
        self.dcm = kibot.m_irclib.DirectConnectionMaster(self.ircobj, addr)
        self.dcm.connect()

    def load_core_modules(self):
        # temporary space
        self.tmp = {}

        # modules
        self.ircdb           = kibot.ircDB.ircDB(self)
        self.permdb          = kibot.permDB.permDB(self)
        self.command_handler = kibot.CommandHandler.CommandHandler(self)
        self.mod             = kibot.ModuleManager.ModuleManager(self)

    def unlock(self):
        os.unlink(self._true_lockfile)

    def connect(self):
        server   = self.op.irc.server
        port     = self.op.irc.port
        nick     = self.op.irc.nick
        password = self.op.irc.password
        username = self.op.irc.username
        ircname  = self.op.irc.ircname
        
        self.nick = nick
        self.hostname = None # will be filled in by ircdb - whoreply
        self.hostip   = None # (same)
        self.conn.connect(server, port, nick, password,
                          username, ircname, log_in=0)
        if password:
            self.conn.pass_(password)
        self.conn.user(username, self.conn.localhost, server, ircname)
        self.ircdb.set_nick(-1)
        return self.conn.connected
            
    def set_handler(self, etype, function, priority=10):
        self.log(2, 'SET HANDLER (%s): %s' % (etype, function))
        self.ircobj.add_global_handler(etype, function, priority)
    def del_handler(self, etype, function, priority=10):
        self.log(2, 'DEL HANDLER (%s): %s' % (etype, function))
        self.ircobj.remove_global_handler(etype, function)
    def set_timer(self, timer):
        self.log(2, 'SET TIMER: %s' % (timer))
        self.ircobj.add_timer(timer)
    def del_timer(self, timer):
        self.log(2, 'DEL TIMER: %s' % (timer))
        self.ircobj.del_timer(timer)

    def handle_event(self, connection, event):
        self.log(5, 'HANDLE EVENT: %s' % (event))
        self.ircobj._handle_event(connection, event)

    core_modules = ['ircdb', 'permdb', 'mod', 'command_handler', 'all']
    def reload_core(self, modules=[]):
        if 'all' in modules:
            modules = list(self.core_modules)
            modules.remove('all')
        reload(kibot.BaseModule)
        for name in modules:
            if name not in self.core_modules:
                self.log(1, "RELOAD IGNORING: %s" % name)
                continue

            self.log(1, "RELOADING: %s" % name)
            attr = getattr(self, name)
            if hasattr(attr, '_unload'): attr._unload()
            mod_name = attr.__module__
            mod_obj = sys.modules[mod_name]
            reload(mod_obj)
            cls_name = string.split(mod_name, '.')[-1]
            obj = getattr(mod_obj, cls_name)(self)
            setattr(self, name, obj)
        return 1

    def die_gracefully(self, message="You don't love me any more!"):
        self.conn.quit(message)
        self.mod.die()
        sys.exit(0)

    def reload_config(self):
        for d in self.op.files.py_path:
            if sys.path[0] == d: sys.path.pop(0)
        self.op = kibot.Options.options(sys.argv[1:])
        sys.path = self.op.files.py_path + sys.path

        # close all of the old log files (unless they're <stderr>, etc)
        for log_obj in self.log.logger_list:
            if not log_obj.file_object.name[0] == '<':
                log_obj.file_object.close()

        loggers = []
        for level, filename in zip(self.op.admin.debug, self.op.admin.logfile):
            try: level = int(level)
            except ValueError:
                sys.stderr.write('debug level must be an integer: %s' % level)
                # sys.exit(1)
                continue
            if filename == '-': fo = sys.stdout
            else: fo = open(filename, 'a', 1)
            loggers.append(kibot.logger.Logger(threshold=level, file_object=fo))
        kibot.m_irclib.log = self.log = kibot.logger.LogContainer(loggers)
        
        self.log(1, 'Reloaded config at: %s' % (time.asctime(), ))
        self.log.write(5, 'CONFIG:\n%s' % self.op)

    ### signal handlers
    def set_signal_handlers(self):
        signal.signal(signal.SIGINT,  self._sigterm_handler)
        signal.signal(signal.SIGTERM, self._sigterm_handler)
        signal.signal(signal.SIGHUP,  self._sighup_handler)

    _signals = {1:  'HUP', 2: 'INT',  3:  'QUIT', 4:  'ILL',  6: 'ABRT',
                8:  'FPE', 9: 'KILL', 11: 'SEGV', 13: 'PIPE', 14: 'ALRM',
                15: 'TERM'}
    def _sigterm_handler(self, signal_number, frame):
        sigdesc = self._signals.get(signal_number,
                                    'something strange, look it up')
        message = "exiting on signal %i (%s)" \
                  % (signal_number, sigdesc)
        self.set_timer(Timer(0, self.die_gracefully, args=(message, )))

    def _sighup_handler(self, signal_number, frame):
        self.set_timer(Timer(0, self.reload_config))
        
if __name__ == '__main__':
    bot = Bot()
    
