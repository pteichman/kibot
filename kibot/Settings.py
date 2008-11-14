from kibot.PermObjects import translate_cperm

class NoDefaultClass:
    """Special class used for implementing "no default".  Doing the
    standard "default=None" thing makes it hard to set the default
    to None."""
    def __repr__(self): return 'No Default'
    def __str__(self):  return 'No Default'
NoDefault = NoDefaultClass()
class SettingError(Exception): pass

class Setting:
    """Class for implementing settings.

    Basically, this should be instantiated from within a module, and then
    never directly touched again.  The constructor takes several arguments:

    name
      the name of the setting, both from the irc interface, and for
      internal access.

    default
      default value for the setting.  Note that you need to apply the
      defaults, usually with init_settings.

    doc
      documentation for the setting

    get_cperm
      cperm required to get the current value

    set_cperm
      cperm required to set a new value

    conv_func
      function for converting the value.  This should take a string
      and return the converted value, which can be anything.

    get_conv_func
      like conv_func, but is used at get time (after get_func).  For
      example, if you use string.split for conv_func, you might want
      to use string.join for get_conv_func.

    set_func
      a function called to set the new values.  The first arg will be
      the kibot module instance (the python class instance).  The
      second will be the name of the setting (so you can use the same
      function for multiple settings if you like) and the third will
      be the value returned by conv_func (or the original string if
      conv_func is not defined).  If you define set_func, the
      attribute WILL NOT be set in your mudule unless you do it
      yourself in the function.

    get_func
      this should return the current value.  It will be passed the
      kibot module instance and name of the setting.

    update_func
      a function that will be called AFTER the setting is set.  It
      will be passed the kibot module instance and the name of the
      setting.  You may want to use this instead of set_func if you
      want to save the value normally, but then take some action.

    """

    def __init__(self, name, default=NoDefault, doc=None,
                 get_cperm=1, set_cperm='manager',
                 get_func=None, set_func=None,
                 conv_func=None, get_conv_func=None, update_func=None):
        self.name          = name
        self.default       = default
        self.doc           = doc
        self.get_cperm     = translate_cperm(get_cperm)
        self.set_cperm     = translate_cperm(set_cperm)
        self.get_func      = get_func
        self.set_func      = set_func
        self.conv_func     = conv_func
        self.get_conv_func = get_conv_func
        self.update_func   = update_func

    def set_default(self, module):
        if not self.default == NoDefault:
            self.set(module, self.default)

    def update_default(self, module):
        if not hasattr(module, self.name):
            self.set_default(module)

    def set(self, module, new_value):
        if not self.conv_func is None:
            try:
                new_value = self.conv_func(new_value)
            except Exception, e:
                raise SettingError('conversion error (%s)' % e)
            
        try:
            if self.set_func is None:
                setattr(module, self.name, new_value)
            else:
                self.set_func(module, self.name, new_value)
        except Exception, e:
            raise SettingError('assignment error (%s)' % e)

        try:
            if not self.update_func is None:
                self.update_func(module, self.name)
        except Exception, e:
            raise SettingError('update error (%s)' % e)
        
    def get(self, module):
        if self.get_func is None:
            val = getattr(module, self.name)
        else:
            val = self.get_func(module, self.name)

        if self.get_conv_func is None:
            return val
        else:
            return self.get_conv_func(val)

def translate_setting(setting):
    """translate a setting shortcut to a Setting instance
    'foo'        -> Setting('foo')
    ('foo', ...) -> Setting('foo', ...)
    True Setting instances get passed through unchanged.
    """
    if type(setting) == type(''):
        newsetting = Setting(setting)
    elif type(setting) == type( () ):
        newsetting = Setting(*setting)
    else:
        newsetting = setting
    return newsetting

def init_settings(module, setting_list):
    """initialize a list of settings
    translate any setting, set defaults, and pass back the replacement
    list.
    """
    new_list = []
    for setting in setting_list:
        newsetting = translate_setting(setting)
        newsetting.update_default(module)
        new_list.append(newsetting)
    return new_list
