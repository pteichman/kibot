import sys

import kibot.Options
from kibot.BaseModule import BaseModule
from kibot.PermObjects import translate_cperm, CPerm
# help policy:
#   help (no args)   print help syntax, brief explanation, and

mainhelp = """syntax: help <topic>
<topic> can be either a module or a command.  \
Typing "help modules" provides a list of loaded modules.
You may also find "help help" useful.
Help using the standard module (with a little more detail) \
can be found online at: %shelp/""" \
   % kibot.Options._URL


class base(BaseModule):
    """base bot functions
    These functions are for basic bot operations.
    """

    _commands = """about help phelp perm path which get set
    load unload reload RELOAD die reconnect restart""".split()
    
    _command_groups = (
        ('info',     ('about',  'help',   'phelp')),
        ('commands', ('perm',   'path',   'which')),
        ('modules',  ('get',    'set',    'load', 'unload')),
        ('admin',    ('RELOAD', 'reload', 'die',  'reconnect', 'restart'))
        )

    def __init__(self, bot):
        self.bot = bot
        self._mainhelp = mainhelp
        
    _about_cperm = 1
    def about(self, cmd):
        """give basic bot information
        about"""
        cmd.reply('kibot v%s - %s' % (kibot.Options.__version__,
                                      kibot.Options._URL))

    ##################################################################
    # help functions

    _help_cperm = 1
    def help(self, cmd):
        """get help on something
        help <thing>
        <thing> can be any one of "modules", "<module>", "<module> <command group>", "[<module>.]<command>", or "<module>.<setting>"."""
        # this is sneaky :)  make it look like they asked privately
        cmd.channel = None
        cmd._reply_object.channel = None
        cmd.reply = cmd.notice
        self.phelp(cmd)
        
    _phelp_cperm = 1
    def phelp(self, cmd):
        """print help to a channel (publicly)
        phelp <thing>
        <thing> can be any one of "modules", "<module>", "<module> <command group>", "[<module>.]<command>", or "<module>.<setting>"."""
        if not cmd.args:
            self._main_help(cmd)
            return

        args = cmd.asplit()
        obj, perm_obj = self.bot.mod.find_object(args[0])
        
        if cmd.args == 'modules':
            self._module_list(cmd)
        elif type(obj) == type(self):  ## instance
            self._module_help(cmd, obj)
        elif type(obj) == type(self.help): ## instance method
            self._function_help(cmd, obj)
        else:
            try:
                # assume it's a setting
                module_name, variable = cmd.args.split('.', 1)
                module, cperm = self.bot.mod.find_object(module_name)
                settings = getattr(module, '_settings', None)
                havesetting = 0
                for s in settings:
                    if s.name == variable:
                        havesetting = 1
                        break
                if not havesetting: raise Exception()
                doc = s.doc or '(no description)'
                cmd.reply('%s - %s [%s]' % (cmd.args, doc, s.default))
            except Exception, e:
                self.bot.log(0, str(e))
                cmd.reply('No such object: %s' % cmd.args)
        
    def _fixdoc(self, obj):
        doc = getattr(obj, '__doc__', '')
        if not doc: doc = '(no documentation)'
        lines = [ line.strip() for line in doc.split('\n') ]
        return lines

    def _main_help(self, cmd):
        for line in self._mainhelp.split('\n'):
            if line: cmd.reply(line)

    def _module_list(self, cmd):
        cmd.reply('Get help on a specific module with "help <module>"')
        mod_list = self.bot.mod.get_list()
        longest = 0
        for name, mod, inst in mod_list:
            if len(name) > longest: longest = len(name)
        format = "  %-" + str(longest) + "s - %s"
        for name, mod, inst in mod_list:
            firstline = self._fixdoc(inst)[0]
            cmd.reply(format % (name, firstline))
            
    def _get_command_groups(self, obj):
        command_groups = getattr(obj, '_command_groups', None)

        # first get all the legal functions
        real_functions = {}
        found_funcs = []
        for fname in dir(obj):
            attr = getattr(obj, fname, None)
            if (attr is None) or (not callable(attr)) or \
                   (fname.startswith('_') and fname != '__call__'):
                continue
            else:
                real_functions[fname] = attr
            found_funcs.append(fname)

        found_names = {}
        groups = []
        allgroup = []
        othergroup = []
        if command_groups:
            for gname, commands in command_groups:
                thisgroup = []
                for command in commands:
                    if not real_functions.has_key(command): continue
                    found_names[command] = 1
                    thisgroup.append(command)
                    allgroup.append(command)
                if thisgroup: groups.append( (gname, thisgroup) )
                
        commands = getattr(obj, '_commands', []) + real_functions.keys()
        for command in commands:
            if not real_functions.has_key(command): continue
            if found_names.has_key(command): continue
            found_names[command] = 1
            othergroup.append(command)
            allgroup.append(command)
                
        if groups and othergroup: groups.append( ('other', othergroup) )

        return real_functions, groups, allgroup

    def _module_help(self, cmd, obj):
        functions, groups, all = self._get_command_groups(obj)

        args = cmd.asplit(1)
        modname = args[0]
        if len(args) == 2: group_name = args[1].lower()
        else: group_name = None

        if groups:
            if not group_name: group_name = groups[0][0]
            commands = None
            group_names = []
            for gname, group_commands in groups:
                if gname == group_name:
                    group_names.append(gname.upper())
                    commands = group_commands
                else:
                    group_names.append(gname)
            groupline = 'command groups: %s' % ' '.join(group_names)
            if group_name == 'all':
                commands = all
            if not commands:
                cmd.reply('bad group: %s' % group_name)
                cmd.reply(groupline)
                return
        else:
            groupline = None
            commands = all
                
        doc = obj.__doc__
        if obj.__doc__:
            for line in self._fixdoc(obj):
                if line: cmd.reply(line)
        if groupline: cmd.reply(groupline)

        lines = []
        longest = 0
        for fname in commands:
            attr = functions[fname]
            func = '%s.%s' % (modname, fname)
            if len(func) > longest: longest = len(func)
            doc  = self._fixdoc(attr)[0]
            lines.append( (func, doc) )
        format = '  %-' + str(longest) + 's - %s'
        for func, doc in lines:
            cmd.reply(format % (func, doc))
        
    def _function_help(self, cmd, obj):
        lines = self._fixdoc(obj)
        lines[0] = cmd.args + ' - ' + lines[0]
        for line in lines:
            if line: cmd.reply(line)
            
    ##################################################################
    # function functions

    _which_cperm = 1
    def which(self, cmd):
        """find where a command lives
        which <command>
        This is usually used to find which module a command resides in.
        """
        command_name = self.bot.permdb.expand_alias(cmd.args)
        obj, perm_obj = self.bot.mod.find_object(command_name)
        if type(obj) is type(self):
            cmd.reply("%s -> %s" % (cmd.args, obj.__class__.__name__))
        elif type(obj) is type(self.which):
            cmd.reply("%s -> %s.%s" % (cmd.args, obj.im_class.__name__,
                                       obj.im_func.__name__))
        else: cmd.reply('Not found')

    _perm_cperm = 1
    def perm(self, cmd):
        """find required perms for a command
        perm <command>
        """
        command_name = self.bot.permdb.expand_alias(cmd.args)
        obj, perm_obj = self.bot.mod.find_object(command_name)
        if not obj:
            cmd.reply('Not found')
            return

        #if perm_obj == 1: p = "(none)"
        #elif perm_obj in (0, None): p = "(forbidden)"
        #else: p = repr(perm_obj)
        p = perm_obj.format()

        cmd.reply('%s requires: %s' % (cmd.args, p))


    ##################################################################
    # module control

    _path_cperm = ['or', 'manager', ':sargs == ""']
    def path(self, cmd):
        """view or set the path
        path [newpath]"""
        if cmd.args:
            # trying to change the path
            mod_list = self.bot.mod.get_list()
            names = [ name for name, modname, mod in mod_list ]
            names.sort()
            newpath = cmd.asplit()
            newpath.sort()
            if not names == newpath:
                cmd.reply("Sorry, some modules are missing, added or wrong.")
                return
            else:
                self.bot.mod.modules_list = cmd.asplit()
                self.bot.mod._stash()
        mod_list = self.bot.mod.get_list()
        names = [ name for name, modname, mod in mod_list ]
        cmd.reply('path: %s' % ' '.join(names))

    _load_cperm = 'load'
    def load(self, cmd):
        """load a bot module
        load <module>
        """
        if self.bot.mod.load(cmd.args): cmd.reply('OK')
        else: cmd.reply('failed')

    _unload_cperm = 'load'
    def unload(self, cmd):
        """unload a bot module
        unload <module>
        """
        if self.bot.mod.unload(cmd.args): cmd.reply('OK')
        else: cmd.reply('failed')
        
    _reload_cperm = 'load'
    def reload(self, cmd):
        """reload a bot module
        reload <module>
        """
        if self.bot.mod.reload(cmd.args): cmd.reply('OK')
        else: cmd.reply('failed')

    _RELOAD_cperm = 'load'
    def RELOAD(self, cmd):
        """reload a core module
        reload <module>
        """
        mods = cmd.asplit()
        if self.bot.reload_core(mods): cmd.reply('OK')
        else: cmd.reply('failed')
        
    ##################################################################
    # module settings
    _get_cperm = 1 # handled internally
    def get(self, cmd):
        """get a module setting
        get <modulename>[.<settingname>]
        if <.settingname> is omitted, all module settings will be listed"""
        context = {'bot': self.bot, 'cmd':cmd}
        user = self.bot.ircdb.get_user(cmd.nick)
        if user is None: uperms = self.bot.permdb.get_unknown_perms()
        else: uperms = user.get_perms()

        if '.' in cmd.args: # getting a specific variable
            module, variable, setting = self._find_variable(cmd)
            if module is None: return
            if not setting.get_cperm.trycheck(uperms, context):
                cmd.reply('you do not have permission to get %s' % cmd.args)
                return
            try: value = repr(setting.get(module))
            except AttributeError, e: value = '(not set)'
            cmd.reply('%s = %s' % (cmd.args, value))
        else: # get all settings from a module
            module, settings = self._get_module_settings(cmd, cmd.args)
            maxlen = 0
            items = []
            for s in settings:
                if not s.get_cperm.trycheck(uperms, context):
                    value = '(permission denied)'
                else:
                    try: value = repr(s.get(module))
                    except AttributeError, e: value = '(not set)'
                    
                if len(s.name) > maxlen: maxlen = len(s.name)
                items.append((s.name, value))
            for name, value in items:
                cmd.reply(('%-'+str(maxlen)+'s = %s') % (name, value))
            
    _set_cperm = 1 # handled internally
    def set(self, cmd):
        """set a module setting
        set <modulename.settingname> <new value>"""
        context = {'bot': self.bot, 'cmd':cmd}
        user = self.bot.ircdb.get_user(cmd.nick)
        if user is None: uperms = self.bot.permdb.get_unknown_perms()
        else: uperms = user.get_perms()

        module, variable, setting = self._find_variable(cmd)
        if module is None: return
        args = cmd.asplit(1)

        if not setting.set_cperm.trycheck(uperms, context):
            return cmd.reply('you do not have permission to set %s' % args[0])

        try: newvalue = args[1]
        except IndexError, e: return cmd.reply('provide a new value')

        try: setting.set(module, newvalue)
        except Exception, e: cmd.reply(str(e))
        else: cmd.reply('done')
            
    def _find_variable(self, cmd):
        args = cmd.asplit()
        if not args:
            cmd.reply("what setting?")
            return (None, None, None)
        
        try: module_name, variable = args[0].split('.', 1)
        except ValueError, e:
            cmd.reply("bad setting, use 'module.varname'")
            return (None, None, None)

        module, settings = self._get_module_settings(cmd, module_name)
        if module is None: return (None, None, None)

        have_setting = 0
        for s in settings:
            if s.name == variable:
                havespec = 1
                break
        if not havespec:
            cmd.reply("module '%s' has no setting '%s'" % \
                      (module_name, variable))
            return (None, None, None)

        return (module, variable, s)
        
    def _get_module_settings(self, cmd, module_name):
        module, cperm = self.bot.mod.find_object(module_name)
        if module is None:
            cmd.reply("module '%s' is not loaded" % module_name)
            return (None, None)

        settings = getattr(module, '_settings', None)
        if settings is None:
            cmd.reply("module '%s' has no settings" % module_name)
            return (None, None)

        return (module, settings)

    ##################################################################
    # Basic bot control

    _die_cperm = 'manager'
    def die(self, cmd):
        """tell the bot to exit
        die"""
        self.bot.die_gracefully()

    _restart_cperm = 'manager'
    def restart(self, cmd):
        """tell the bot to restart fully
        restart"""
        self.bot.conn.quit("if you say so")
        # first remove all modules, giving them a chance to save data
        self.bot.mod.die()
        sys.exit('restart')

    _reconnect_cperm = 'manager'
    def reconnect(self, cmd):
        """tell the bot to reconnect
        reconnect"""
        self.bot.conn.quit("be right back!")
    
