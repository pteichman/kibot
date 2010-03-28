# -*- python -*-
import sys
import os
import os.path

from .OptionParser import OptionParser, OptionError

DEBUG = 0
DEF_BOTMOD_PATH = ['modules']
DEF_PYMOD_PATH  = ['pymod']
_PACKAGE = 'kibot'
_URL     = 'http://wiki.github.com/pteichman/kibot/'

def fill_options(o):
    #     type      name                short long default
    o.add('bool',   'help',                'h', 'help', 0,
          cp_name=None, desc='print this help message')

    o.add('string', 'files.base_dir',      'b', 'base-dir', '.',
          desc='base dir, other files are relative to this')
    o.add('string', 'files.conf_file',     'C', 'conf', 'kibot.conf',
          cp_name=None, desc='config file - defaults to kibot.conf')
    o.add('string', 'files.override_file', '', '', 'override.conf',
          desc='file for overriding default permissions')
    o.add('string', 'files.data_dir',      '', '', 'data',
          desc='directory where kibot will put data')
    o.add('string', 'files.ircdb_file',    '', '', 'data/ircdb.pickle',
          desc='file where kibot stores user profiles')
    o.add('list',   'files.py_path',       '', 'py-path', DEF_PYMOD_PATH,
          desc='prepended to the python search path')

    o.add('list',   'admin.debug',    'd', 'debug', [0],
          desc='logging level (-1 to 10, higher for more)')
    o.add('list',   'admin.logfile',  '',  'logfile', ['-'],
          desc='log file, "-" means STDOUT')
    o.add('bool',   'admin.forget',   'f', 'forget', 0,
          desc='forget previous state (channels, modules, etc)')
    o.add('bool',   'admin.daemon',   '', 'daemon', 0,
          desc='run as a daemon')
    o.add('string', 'admin.lockfile', '', 'lockfile', 'kibot.pid',
          desc='file to write pid to')
    o.add('string', 'admin.dc_addr', '',  'dc-addr',  'DC_SOCKET',
          desc='DC address (filename for unix, port for tcp)')
    o.add('string', 'admin.umask',   '',  'umask', '0077',
          desc='octal umask used when running daemonized')
    o.add('int',    'admin.timeout', '',  'timeout', 5,
          desc='timeout (in seconds) used for sockets')

    o.add('list',   'modules.autoload', '', 'autoload', [],
          desc='modules to load on startup')
    o.add('list',   'modules.load_path',  '', 'load-path', DEF_BOTMOD_PATH,
          desc='list of directories to look in for bot modules')

    o.add('string', 'irc.server',   's', 'server', '',
          desc='irc server to which kibot should connect')
    o.add('int',    'irc.port',     'p', 'port', 6667,
          desc='port to connect on')
    o.add('list',   'irc.channels', 'c', 'channels', [],
          desc='list of channels to connect on')
    o.add('string', 'irc.nick',     'n', 'nick', 'kibot',
          desc='nick to connect with')
    o.add('string', 'irc.password', '',  'password', '',
          desc='password to connect with')
    o.add('string', 'irc.username', 'u', 'username', '',
          desc='username, same as nick if empty')
    o.add('string', 'irc.ircname',  'N', 'ircname', '',
          desc='descriptive name, same as nick if empty')
    o.add('int',    'irc.reconnect_interval', '', '', 30,
          desc='number of seconds between attempts to reconnect')
    return o

def printhelp(o):
    print "%s -- a modular python-based IRC bot" % _PACKAGE
    print "  %s" % _URL
    print
    print "Usage: %s [options]" % _PACKAGE
    print o.help(width=24),

def munge_options(f):
    # normalize the path, because the pwd may change
    bdir = f.files.base_dir = os.path.abspath(f.files.base_dir)
    join = os.path.join

    f.files.override_file = join(bdir, f.files.override_file)
    f.files.ircdb_file    = join(bdir, f.files.ircdb_file)
    f.files.data_dir      = join(bdir, f.files.data_dir)
    f.admin.lockfile      = join(bdir, f.admin.lockfile)
    try:
        port = int(f.admin.dc_addr)
    except ValueError:
        f.admin.dc_addr   = join(bdir, f.admin.dc_addr)
    else:
        f.admin.dc_addr = port

    try:
        orig = f.admin.umask
        f.admin.umask = int(orig, 8)
        if f.admin.umask < 0 or f.admin.umask > 0777:
            raise ValueError
    except ValueError:
        sys.exit('invalid umask: %s' % orig)

    tmp = []
    for l in f.admin.logfile:
        if not l == '-': l = join(bdir, l)
        tmp.append(l)
    f.admin.logfile = tmp

    tmp = []
    for d in f.modules.load_path: tmp.append(join(bdir, d))
    f.modules.load_path = tmp

    tmp = []
    for d in f.files.py_path: tmp.append(join(bdir, d))
    f.files.py_path = tmp

    if not f.irc.username: f.irc.username = f.irc.nick
    if not f.irc.ircname:  f.irc.ircname  = f.irc.nick

def _options(cmd_line):
    o = OptionParser()
    o = fill_options(o)
    defaults = o.load_defaults()
    if DEBUG: print 'DEFAULTS\n%s' % defaults

    command_line = o.load_getopt(cmd_line)
    if DEBUG: print 'COMMAND LINE\n%s' % command_line
    if command_line._args:
        sys.stderr.write('ERROR: unknown arguments: %s\n' \
                         % ' '.join(command_line._args))
        sys.exit(1)

    tmp = o.overlay([defaults, command_line])
    if DEBUG: print 'TMP\n%s' % tmp
    if tmp.help:
        printhelp(o)
        sys.exit(0)

    config_file = os.path.join(tmp.files.base_dir, tmp.files.conf_file)
    if DEBUG: print 'CONFIG FILE: %s\n' % config_file
    file_ops = o.load_ConfigParser(config_file, include_unknown=cp_callback)
    if DEBUG: print 'FILE OPTIONS\n%s' % file_ops
    final = o.overlay([defaults, file_ops, command_line])
    if DEBUG: print 'COLLAPSED VALUES\n%s' % final
    munge_options(final)
    if DEBUG: print 'MUNGED VALUES\n%s' % final

    return final

def cp_callback(name, value):
    section, option = name
    if section.startswith('mod_'): return 1 # module section, quietly accept it
    return -1 # bad option - complain

def options(cmd_line):
    try:
        return _options(cmd_line)
    except OptionError, msg:
        sys.exit('ERROR: %s\n' % msg)

if __name__ == '__main__':
    if sys.argv[1:] == ['conf']:
        _o = OptionParser()
        _o = fill_options(_o)
        _m = \
          "# These values are the built-in defaults.  Using these values\n" \
          "# in a config file is exactly the same as using no config file\n" \
          "# at all.  This is provided so that you can see:\n" \
          '#  a) what options are available (see "man kibot")\n' \
          '#  b) what the defaults are (again, see "man kibot")\n' \
          '#  c) how to use them\n' \
          '\n'
        sys.stdout.write(_m)
        sys.stdout.write(_o.sample_file())
        sys.exit(0)
    DEBUG = 1
    options(sys.argv[1:])
