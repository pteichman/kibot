#!/usr/bin/python2
import re
import getopt
import ConfigParser
import pprint
import os
import os.path

DEBUG = 0

class OptionError(Exception): pass
class NoDefault: pass
class NoValue: pass

class baseOption:
    def __init__(self, name, short=None, long=None, default=NoDefault, \
        cp_name=(), desc=None):
        self.name = self._split_name(name)
        self.short = short
        self.long = long
        self.default = default
        if cp_name is None: self.cp_name = None
        elif cp_name == (): self.cp_name = self._split_cp_name(name)
        else: self.cp_name = self._split_name(cp_name)
        self.desc = desc

    def overlay(self, lower, upper):
        return upper

    def _split_name(self, name):
        if not type(name) == type(''): return name
        return tuple(name.split('.'))

    def _split_cp_name(self, name):
        if not type(name) == type(''): return name
        ns = name.split('.', 1)
        if len(ns) == 1: ns = ('main', ns[0])
        return tuple(ns)

    def value_from_string(self, st):
        return st

    def value_from_ConfigParser(self, st):
        return self.value_from_string(st)

    getopt_takes_arg = 1
    def value_from_getopt(self, st):
        return self.value_from_string(st)

class stringOption(baseOption):
    pass

class boolOption(baseOption):
    getopt_takes_arg = 0
    true_regex  = re.compile(r'^\s*(1|yes|true|t|y)\s*$')
    false_regex = re.compile(r'^\s*(0|no|false|f|n)\s*$')
    def value_from_string(self, st):
        if self.true_regex.match(st): return 1
        elif self.false_regex.match(st): return 0
        else:
            raise OptionError("illegal boolean value: %s" % `st`)

    def value_from_getopt(self, st):
        # this will only ever be called if it's true :)
        return 1

class intOption(baseOption):
    def value_from_string(self, st):
        try:
            i = int(st)
        except ValueError:
            raise OptionError("illegal integer value: %s" % st)
        return i

class floatOption(baseOption):
    def value_from_string(self, st):
        try:
            f = float(st)
        except ValueError:
            raise OptionError("illegal float value: %s" % st)
        return f

class listOption(baseOption):
    listsplit_re = re.compile(r'\s*[,\s]\s*')
    def value_from_string(self, st):
        li = self.listsplit_re.split(st)
        return li

    def overlay(self, lower, upper):
        new = []
        for i in upper:
            if i == 'PREV': new.extend(lower)
            else: new.append(i)
        return new

########################################################################

class OptionParser:
    _otypes = {
        'bool': boolOption,
        'string': stringOption,
        'list': listOption,
        'int': intOption,
        'float': floatOption,
        }

    def __init__(self):
        self._oplist = []

    def help(self, width=20):
        form1 = '  %-' + str(width) + 's  %s\n'
        form2 = '  %s\n' + ' '*(2 + width + 2) + '%s\n'
        hp = []
        for op in self._oplist:
            ol = []
            if op.short:
                st = '-' + op.short
                if op.getopt_takes_arg: st = st + ' VAL'
                ol.append(st)
            if op.long:
                st = '--' + op.long
                if op.getopt_takes_arg: st = st + '=VAL'
                ol.append(st)
            op_st = ', '.join(ol)
            if op_st:
                if len(op_st) > width: form = form2
                else: form = form1
                hp.append(form % (op_st, op.desc))
        return ''.join(hp)

    def sample_file(self):
        sections = {}
        section_list = []
        for op in self._oplist:
            if not op.cp_name: continue
            section, option = op.cp_name
            if not sections.has_key(section):
                section_list.append(section)
                sections[section] = []
            if type(op.default) == type([]):
                dflt = ', '.join(map(str, op.default))
            else:
                dflt = str(op.default)
            tmp = '%-10s = %-0s' % (option, dflt)
            sections[section].append('%-25s  # %s\n' % (tmp, op.desc))
        st = ''
        for s in section_list:
            st = st + '[%s]\n' % s
            st = st + ''.join(sections[s]) + '\n'
        return st

    def add(self, otype, *args, **kwargs):
        klass = self._otypes[otype]
        self._oplist.append(klass(*args, **kwargs))

    def load_defaults(self):
        oc = OptionContainer()
        for op in self._oplist:
            if not op.default is NoDefault:
                oc.set(op.name, op.default)
        return oc

    def load_getopt(self, cmd_line):
        oc = OptionContainer()
        # build the options lists for getopt
        short = ''
        long = []
        opmap = {}
        for op in self._oplist:
            if op.short:
                short = short + op.short
                if op.getopt_takes_arg:
                    short = short + ':'
                opmap['-' + op.short] = op
            if op.long:
                a = ''
                if op.getopt_takes_arg: a = '='
                long.append(op.long + a)
                opmap['--' + op.long] = op

        if DEBUG:
            print 'DEBUG: getopt(%s, %s, %s)' % (`cmd_line`, `short`, `long`)
        try: cl_ops, args = getopt.getopt(cmd_line, short, long)
        except getopt.GetoptError, msg: raise OptionError(str(msg))
        oc._args = args
        for cl_op, val in cl_ops:
            op = opmap.get(cl_op)
            # make this more flexible - call some user-definable function
            if not op: raise OptionError('bad command line option: %s' % cl_op)
            oc.set(op.name, op.value_from_getopt(val))
        return oc

    def load_ConfigParser(self, filename, include_unknown=1):
        """Load the config file and return an OptionContainer

        If filename does not exist, an empty OC will be returned.  If
        it exists but cannot be read, an OptionError will be raised.

        include_unknown determines the behavior if an unrecognized option
        is encountered.  It has 4 possible values:

          1          include the option/value
          0          ignore the option/value
          -1         raise an OptionError exception
          callback   if include_unknown is callable, it will be called
                     like this:
                         ret = include_unknown((section, option), value)
                     It can return one of [1, 0, -1], which will then be
                     interpreted as above.  It is also reasonable to take
                     some action (print stuff, for example) or raise an
                     exception (which will NOT be caught here).
        """

        oc = OptionContainer()
        opmap = {}
        for op in self._oplist:
            if op.cp_name:
                opmap[op.cp_name] = op

        # a missing config file is OK, but an unreadable one is not
        if os.path.exists(filename) and not os.access(filename, os.R_OK):
            raise OptionError('cannot read config file: %s' % filename)

        cfg_parser = ConfigParser.ConfigParser()
        cfg_parser.read(filename)
        sections = cfg_parser.sections() # get a list of sections
        for section in sections: # loop through the list
            options = cfg_parser.options(section) # get a list of options
                                                  # in that section
            for option in options:
                if option == '__name__': continue # the section name
                value = cfg_parser.get(section, option)
                name = (section, option)
                op = opmap.get(name)
                if op:
                    oc.set(op.name, op.value_from_ConfigParser(value))
                else:
                    ## the section/option pair were not recognized
                    if callable(include_unknown):
                        ret = include_unknown(name, value)
                    else:
                        ret = include_unknown

                    if ret == 1:   # set it anyway
                        oc.set(name, value)
                    elif ret == 0: # ignore it
                        pass
                    #elif ret == -1: # complain
                    else:
                        msg = 'bad option in section [%s]: %s = %s'
                        raise OptionError(msg % (section, option, value))

        return oc

    def overlay(self, oc_list, keep_unknown=1): #should this be an OptionContainer method?
        new = OptionContainer()
        for oc in oc_list:
            self._overlay(new, oc, keep_unknown=keep_unknown)
        return new

    def _overlay(self, lower, upper, keep_unknown):
        opmap = {}
        for op in self._oplist:
            opmap[op.name] = op

        olist = upper.options_list()
        for n, v in olist:
            op = opmap.get(n)
            if op:
                lower.set(n, op.overlay(lower.get(n), v))
            elif keep_unknown:
                lower.set(n, v)
#########################################################################333

class OptionContainer:
    def set(self, name, value, fullname=None):
        if not fullname: fullname = name
        if len(name) > 1:
            if not hasattr(self, name[0]):
                setattr(self, name[0], OptionContainer())
            oc = getattr(self, name[0])
            if not isinstance(oc, OptionContainer):
                msg = 'error setting %s, name refers to group and option'
                raise OptionError(msg % str(fullname))
            oc.set(name[1:], value, fullname)
        else:
            if hasattr(self, name[0]):
                v = getattr(self, name[0])
                if isinstance(v, OptionContainer):
                    msg = 'error setting %s, name refers to group and option'
                    raise OptionError(msg % str(fullname))
            setattr(self, name[0], value)

    def get(self, name, default=NoValue):
        obj = self
        n = list(name)
        while n:
            obj = getattr(obj, n.pop(0), default)
        return obj

    def options_list(self):
        li = []
        for k, v in self.__dict__.items():
            if isinstance(v, OptionContainer):
                sub_li = v.options_list()
                li.extend([ ( (k, ) + sub_k, v) for sub_k, v in sub_li ])
            else:
                li.append( ((k, ), v) )
        return li

    def __repr__(self):
        return self._pprint()

    def _pprint(self, prefix='op'):
        buf = ''
        for k, v in self.__dict__.items():
            if hasattr(v, '_pprint'):
                buf = buf + v._pprint(prefix + '.' + k)
            else:
                buf = buf + '%-25s = %s\n' % ( prefix + '.' + k, repr(v) )
        return buf


if __name__ == '__main__':
    import sys
    DEBUG = 0
    o = OptionParser()
    o.add('int', 'admin.debug', 'd', 'debug', 0, \
          desc='debug level (-1 to 10, higher prints more)')
    o.add('string', 'admin.logfile', '', 'logfile', '', \
          desc='file to write log data to, no value means STDOUT')
    o.add('float', 'stuff.price', 'p', 'price', 1.62, \
          desc='file to write log data to, no value means STDOUT')
    o.add('list', 'stuff.list', 'l', 'list', [1, 4], \
          desc='foo')

    o.load_defaults()
    o.load_getopt(sys.argv[1:])
    # get config file
    o.load_ConfigParser('options.test')
    final = o.overlay(['defaults', 'config file', 'command line'])
    sys.stdout.write(`final`)
    print o.help()
    print o.sample_file()
