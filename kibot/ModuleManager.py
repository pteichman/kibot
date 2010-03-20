import string
import sys
import re
import linecache
import pkg_resources
from copy import copy

from ihooks import BasicModuleLoader
Loader = BasicModuleLoader()

import BaseModule
from PermObjects import CPerm, translate_cperm

class NoPerm: pass

class ModuleManager(BaseModule.BaseModule):
    _list_split_re = re.compile(r'\s*[,\s]\s*')
    _tmp_key = 'ModuleManagerData'
    _stash_file = 'modules.repr'
    _stash_format = 'repr'
    _stash_attrs = ['modules_list']
    _primary_modules = ['base', 'auth', 'irc']
    def __init__(self, bot):
        self.bot = bot
        self._load()

    def _load(self):
        if self.bot.tmp.has_key(self._tmp_key):
            # modules are already loaded - just put them in place
            tmp = self.bot.tmp[self._tmp_key]
            del self.bot.tmp[self._tmp_key]
            self.modules = tmp['modules']
            self.modules_list = tmp['modules_list']
            self.bot.log(1, 'MODULES ALREADY LOADED: %s' % \
                         ' '.join(self.modules_list))
        else:
            load_list = []
            self.modules = {}
            if not self.bot.op.admin.forget:
                # load modules we had loaded in last session
                self._unstash(None)
                load_list = self.modules_list
                if not load_list: load_list = []
                self.bot.log(1, 'LOADING REMEMBERED MODULES: %s' % \
                             ' '.join(load_list))

            self.modules_list = [] # must empty it or self.load will refuse
            if not load_list:
                # load the autoload list and primary modules
                load_list = self.bot.op.modules.autoload

            pm = copy(self._primary_modules)
            pm.reverse()
            for p in pm:
                if p in load_list: load_list.remove(p)
                load_list.insert(0, p)

            self.bot.log(1, 'LOADING MODULES: %s' % ' '.join(load_list))
            for name in load_list: self.load(name)

    def _unload(self):
        tmp = {}
        tmp['modules'] = self.modules
        tmp['modules_list'] = self.modules_list
        tmp = self.bot.tmp[self._tmp_key] = tmp
    ################################################################

    def get_list(self):
        """return a list of loaded modules in search-path order
        each item in the returned list is a tuple:
          (modulename, python_module, bot_module)
        Here, python_module is the python_module in which the bot module
        is defined.  bot_module is the class instance that IS the bot module.
        """
        li = []
        for name in self.modules_list:
            tup = self.modules[name]
            li.append( (name, tup[0], tup[1]) )
        return li

    def find_object(self, obj_name):
        """find an object in the modules and return it
        takes the object pathname (as in 'module.command' or just 'command')
        and returns the python object, along with its perm_object.
        """
        parts = obj_name.split('.')
        # only return public objects (nothing that starts with '_')
        for p in parts:
            if not p or p[0] == '_': return (None, None)

        if len(parts) == 1:
            data = self._find_module(parts[0])
            if not data[0]:
                data = self._find_obj_in_module_path(parts[0])
        elif len(parts) == 2:
            data = self._find_obj_in_module(*parts)
        else:
            self.bot.log(5, 'OBJECT NAME too many chunks: %s' % obj_name)
            data = (None, None, None, None)

        obj, cperm, cperm_parent, cperm_name = data

        if not obj: return (None, None)
        elif cperm == NoPerm: return (obj, None)
        elif isinstance(cperm, CPerm): return (obj, cperm)
        else:
            new_cperm = translate_cperm(cperm)
            setattr(cperm_parent, cperm_name, new_cperm)
            self.bot.log(6, 'translating %s to %s' % (cperm, new_cperm))
            return (obj, new_cperm)

    def _find_module(self, modname):
        pymod, inst = self.modules.get(modname, (None, None))
        if pymod: # found it - must be a module
            perm_obj = getattr(inst, '_cperm', NoPerm)
            return (inst, perm_obj, inst, '_cperm')
        return (None, None, None, None)

    def _find_obj_in_module_path(self, object_name):
        for modname in self.modules_list:
            data = self._find_obj_in_module(modname, object_name)
            if data[0]: return data
        return (None, None, None, None)

    def _find_obj_in_module(self, module_name, object_name):
        permname = '_'+object_name+'_cperm'
        pymod, inst = self.modules[module_name]
        if hasattr(inst, object_name):
            perm_obj = getattr(inst, permname, NoPerm)
            return (getattr(inst, object_name), perm_obj, inst, permname)
        return (None, None, None, None)

    def load(self, name):
        """load a bot module by name"""

        self.bot.log(2, 'LOADING: %s' % name)
        if name in self.modules_list:
            self.bot.log(1, 'ALREADY LOADED: %s' % name)
            return 0
        module = None

        # first, try loading from eggs
        for entrypoint in pkg_resources.iter_entry_points("kibot.modules"):
            if entrypoint.name == name:
                self.bot.log(5, 'LOADING MODULE: %s (%s)' % (entrypoint,
                                                             entrypoint.dist))

                module = entrypoint.load()
                if module: break

        # legacy module loading from the load_path
        for directory in self.bot.op.modules.load_path:
            self.bot.log(5, 'LOOKING IN: %s' % directory)
            stuff = Loader.find_module_in_dir(name, directory)
            if stuff:
                module = Loader.load_module(name, stuff)
                if module: break
        if module:
            cls = getattr(module, name) # look for class of same name
            self.modules[name] = (module, cls(self.bot))
            self.modules_list.append(name)
            linecache.checkcache()
            self._stash()
            return 1
        else:
            self.bot.log(0, 'MODULE NOT FOUND: %s' % name)
            return 0

    def unload(self, name):
        """unload a bot module by name"""
        if name in self.modules_list:
            mod, obj = self.modules[name]
            if hasattr(obj, '_unload'): obj._unload()
            del self.modules[name]
            self.modules_list.remove(name)
            self._stash()

            # The following is a good idea.  Unfortunately, I don't
            # know how to write get_defining_module.  That is, I don't
            # know of a reasonably reliable way to find the module in
            # which a given function (or more generally, callable
            # object) was defined.  Furthermore, people could do some
            # not-so-crazy things that resulted in module foo setting
            # a timer/handler whose function is not defined in module
            # foo (a support "pymod" module, for example).

            #for timer in self.bot.ircobj.delayed_commands:
            #    m = get_defining_module(timer.func)
            #    if m is obj:
            #        self.bot.log(2, 'MOD: removing orphaned timer: %s' % \
            #                     repr(timer.func))
            #        timer_list.remove(timer)

            #for handler_group in self.bot.ircobj.handlers.values():
            #    for htup in handler_group:
            #        priority, handler = htup
            #        m = get_defining_module(handler)
            #        if m is obj:
            #            self.bot.log(2, 'MOD: removing orphaned handler: %s' % \
            #                         repr(handler))
            #            handler_group.remove(htup)

            return 1
        else:
            return 0

    def reload(self, name):
        """reload a bot module by name
        This differs from "load; reload;" only in that the path
        order is preserved un successful reload
        """
        ml = copy(self.modules_list)
        self.unload(name)
        ret = self.load(name)
        if len(ml) == len(self.modules_list):
            # preserve path order
            self.modules_list = ml
            self._stash()
        return ret

    def die(self):
        """unload all modules, but keep self.modules_list populated
        This should only be used on bot exit.  This is so modules can
        be unloaded properly, yet the modules_list is stored for the
        next startup"""
        ml = copy(self.modules_list)
        for name in ml:
            self.unload(name)
        self.modules_list = ml
        self._stash()
