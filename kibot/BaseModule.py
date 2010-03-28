import os

from . import Stasher
from .Settings import init_settings

class NoDefault: pass

class BaseModule:
    """This class is intended to provide a number of convenient and common
    features for kibot modules."""

    def __init__(self, bot):
        """
        1) set the bot attribute
        2) load the stasher if any _stash_attrs are defined
        3) initialize the settings (setting any defaults if empty)
        4) set any _on_XXXX handlers with priority 0
        """
        self.bot = bot
        if self._stash_attrs: self._unstash()

        try: self._settings = init_settings(self, self._settings)
        except AttributeError, e: pass

        self._set_handlers()

    def _unload(self):
        """
        1) save the stasher if any _stash_attrs are defined
        2) remove any _on_XXXX handlers
        """
        if self._stash_attrs: self._stash()
        self._del_handlers()

    ######################################################################
    # stasher
    _stash_format = 'pickle'
    _stash_attrs = []
    #_stash_file = 'foo.pickle'    # will appear in the "data_dir"
    def _get_stasher(self, filename=None, stash_format=None, **kwargs):
        if not stash_format: stash_format = self._stash_format
        if not filename:
            def_stash_basename = "%s.%s" % (self.__class__.__name__,
                                            stash_format)
            filename = getattr(self, '_stash_file', def_stash_basename)
        stash_file = os.path.join(self.bot.op.files.data_dir, filename)
        return Stasher.get_stasher(stash_file, stash_format, **kwargs)

    def _stash(self, default=NoDefault):
        """Store the attributes listed in self._stash_attrs in a stasher.
        One will be created if necessary.  If a value isn't set and
        a default is provided, that value will be used."""
        if not hasattr(self, '_stasher'):
            self._stasher = self._get_stasher(autosync=0)
        for attr in self._stash_attrs:
            try: value = getattr(self, attr)
            except AttributeError, e:
                if not default == NoDefault:
                    self._stasher[attr] = default
            else: self._stasher[attr] = value
        self._stasher.sync()

    def _unstash(self, default=NoDefault):
        """Reload the attributes listed in self._stash_attrs from the
        stasher.  If the attribute was not in the stasher (or if the file
        didn't exist) then the attribute will be set to 'default'.  If
        default is not provided, then the attribute will not be set at all."""

        if not hasattr(self, '_stasher'):
            self._stasher = self._get_stasher(autosync=0)

        for attr in self._stash_attrs:
            if default == NoDefault:
                try: value = self._stasher[attr]
                except KeyError, e: pass
                else: setattr(self, attr, value)
            else:
                value = self._stasher.get(attr, default)
                setattr(self, attr, value)

    ##################################################################3
    # handlers
    def _get_handlers(self, prefix):
        """return a list of all event types for which it looks like
        the module has handlers.  If the module has defined _on_join and
        _on_kick, then this will return ['join', 'kick']

        if the attribute self._handlers is defined, it will be returned
        instead
        """
        try:
            handlers = self._handlers
        except AttributeError:
            handlers = []
            L = len(prefix)
            for f in dir(self):
                a = getattr(self, f)
                if callable(a) and f.startswith(prefix):
                    handlers.append(f[L:])
        return handlers

    def _set_handlers(self, priority=0, prefix="_on_"):
        """set handlers for all methods with prefix <prefix>
        For example, if the method _on_join is defined, then that method
        will be registered as handler for the "join" event.

        If the attribute self._handlers is defined, it will be used instead.
        each element of the self._handlers list should be the event type.

          def _handle_join(self, conn, event): pass
          def _handle_kick(self, conn, event): pass
          def _handle_part(self, conn, event): pass
          self._handlers = ['join', 'kick']
          self._set_handlers(prefix='_handle_')

        In this case, only the first two will be set.  If self._handlers
        were not defined, then all three would be set.
        """
        handlers = self._get_handlers(prefix)
        for h in handlers:
            self.bot.set_handler(h, getattr(self, prefix + h), priority)

    def _del_handlers(self, priority=0, prefix="_on_"):
        """This "undoes" self._set_handlers"""
        handlers = self._get_handlers(prefix)
        for h in handlers:
            self.bot.del_handler(h, getattr(self, prefix + h), priority)
