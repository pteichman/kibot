#!/usr/bin/python2 -t

import sys
import re
import os.path
from ihooks import BasicModuleLoader
Loader = BasicModuleLoader()
import kibot.Options
import kibot.OptionParser
from kibot.PermObjects import translate_cperm, CPerm
from kibot.Settings import translate_setting

class _dummy: pass
def log(message, newline=1):
    if newline: sys.stderr.write(message + '\n')
    else:       sys.stderr.write(message)
###########################################################
def get_options(cmd_line):
    o = kibot.OptionParser.OptionParser()
    o = kibot.Options.fill_options(o)
    defaults = o.load_defaults()
    command_line = o.load_getopt(cmd_line)
    tmp = o.overlay([defaults, command_line])
    config_file = os.path.join(tmp.files.base_dir, tmp.files.conf_file)
    file_ops = o.load_ConfigParser(config_file)
    final = o.overlay([defaults, file_ops, command_line])
    kibot.Options.munge_options(final)
    
    modules = command_line._args
    sys.path = final.files.py_path + sys.path
    return modules, final.modules.load_path


def load_modules(namelist, load_path):
    # namelist is a list of names, they can be module names (slashdot) or
    # file names (../modules/slashdot.py)
    modlist = [] # list of module objects
    loaded = []
    if not namelist:
        for Dir in load_path:
            for f in os.listdir(Dir):
                m = re.match(r'^(.*)\.py[co]?$', f)
                if m and m.group(1) not in namelist:
                    namelist.append(m.group(1))
    
    for modname in namelist:
        log('%-30s --> ' % modname, 0)
        directory, modname = os.path.split(modname)
        if re.search(r'\.py[co]?$', modname): # given a filename
            modname = re.sub(r'\.py[co]?$', '', modname)
            if modname in loaded:
                log('%s already loaded, skipping' % modname)
                continue
            log('trying: %s in %s' % (modname, directory))
            stuff = Loader.find_module_in_dir(modname, directory)
        else:
            if modname in loaded:
                log('%s already loaded, skipping' % modname)
                continue
            log('searching for %s' % modname)
            stuff = Loader.find_module(modname, load_path)
        if stuff:
            module = Loader.load_module(modname, stuff)
            if module:
                modlist.append(module)
                loaded.append(modname)
        if not (stuff and module): log("ERROR: couldn't load: %s" % modname)
    return modlist
            
def get_docs(module):
    module_doc = _dummy()
    name = module_doc.name = module.__name__
    pymod_doc = module_doc.info = fixdoc(module) or []
    cls = getattr(module, name)
    class_doc = module_doc.summary = fixdoc(cls) or ['']

    # functions
    functions = []
    module_doc.functions = functions
    real_functions, groups, allgroup = _get_command_groups(cls)
    # for now, ignore group structures.  Groups are a PITA and mostly
    # helpful in the irc-based help
    for fn in allgroup:
        f = get_func_doc(cls, fn, real_functions[fn])
        functions.append(f)

    # settings
    rawsettings = getattr(cls, '_settings', [])
    settings = [ translate_setting(s) for s in rawsettings ]
    module_doc.settings = settings
    return module_doc

def _get_command_groups(obj):
    # stolen almost verbatim from base.py
    # the only change is the indentation and the args: (self, obj) -> (obj)
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

def get_func_doc(cls, fname, attr):
    f = _dummy()

    if fname == '__call__':
        f.name = '(call)'
        c = getattr(cls, '_cperm', None)
    else:
        f.name = fname
        c = getattr(cls, '_%s_cperm' % fname, None)

    if c == 1: f.cperm = '(none)'
    elif c is None or c == 0: f.cperm = '(forbidden)'
    elif isinstance(c, CPerm): f.cperm = c.format()
    else: f.cperm = repr(c)
    f.doc = fixdoc(attr) or []
    while len(f.doc) < 2: f.doc.append('')
    return f
    

html_intro = """
    <p>
      This document describes kibot modules and their contents.
      Modules can contain both <i>commands</i> and <i>settings</i>.
      Commands can be executed either privately or publicly.  To
      execute a command publicly, simply send <tt>&lt;botnick&gt;:
      &lt;command&gt; &lt;args&gt;</tt>, where
      <tt>&lt;botnick&gt;</tt> is the bot's nick,
      <tt>&lt;command&gt;</tt> is the command name, and
      <tt>&lt;args&gt;</tt> are any command arguments.  To execute a
      command privately, you need only send <tt>&lt;command&gt;
      &lt;args&gt;</tt>.
    </p>

    <p>
      All commands can be called by their <q>full path</q>, i.e.
      <tt>modname.cmdname</tt>.  If only <tt>cmdname</tt> is typed,
      it will be searched for in all loaded modules according to the
      <tt>path</tt> (see the <tt>base.path</tt> command).
    </p>

    <p>
      Some modules can be treated like commands themselves.  For example,
      you can do a google search either with the command
      <q><tt>google.search your search terms</tt></q> or simply with
      <q><tt>google your search terms</tt></q>.  Such command-like behavior
      is listed as a command named <q><tt>(call)</tt></q> in the help below.
    </p>

    <p>
      Some commands require specific <q>permissions</q> in order to be
      executed.  These command permissions (or <q>cperms</q>) are usually
      a simple name, but can be more powerful.
    </p>

    <p>
      Module settings are used to modify the behavior of the module.
      They can be queried and modified with the commands
      <tt>base.get</tt> and <tt>base.set</tt>.
    </p>
"""

def dump_all_html(md_list):
    print '<html>'
    print '  <head>'
    print '    <title>Kibot Commands</title>'
    print '    <LINK REL="StyleSheet" HREF="modulehelp.css" TYPE="text/css" MEDIA="screen">'
    print '  </head>'
    print '  <body>'
    print '    <h1>Kibot Commands</h1>'
    print html_intro
    

    print '    <h2>Modules</h2>'
    print '    <table class="modlist">'
    print '      <tr class="modlist">'
    print '        <th class="modlist">Module</th>'
    print '        <th class="modlist">Description</th>'
    print '      </tr>'
    for md in md_list:
        print '      <tr class="modlist">'
        nlink = '<a href="#mod.%s">%s</a>' % (md.name, md.name)
        print '        <td class="mlname">%s</td>' % nlink
        print '        <td class="mldesc">%s</td></tr>' % htmlenc(md.summary[0])
        print '      </tr>'
    print '    </table>'


    print '    <h2>Module Summaries</h2>'
    for md in md_list:
        print '    <a name="mod.%s" />' % md.name
        print '    <h3>%s -- %s</h3>' % (md.name, md.summary[0])
        print '    <table class="summary">'
        print '      <tr class="summary">'
        print '        <th class="summary">Command</th>'
        print '        <th class="summary">Description</th>'
        print '      </tr>'
        for f in md.functions:
            print '      <tr class="summary">'
            nlink = '<a href="#%s.%s">%s</a>' % (md.name, f.name, f.name)
            print '        <td class="sfname">%s</td>' % nlink
            print '        <td class="sfdesc">%s</td></tr>' % htmlenc(f.doc[0])
            print '      </tr>'
        for s in md.settings:
            print '      <tr class="summary">'
            nlink = '<a href="#%s.%s">%s</a>' % (md.name, s.name, s.name)
            print '        <td class="dscplabel">%s</td>' % nlink
            doc = s.doc or '(no description)'
            print '        <td class="dscpvalue">%s</td></tr>' % htmlenc(doc)
            print '      </tr>'
        print '    </table>'

    print '    <h2>Module Details</h2>'
    for md in md_list:
        print '    <h3>%s -- %s</h3>' % (md.name, md.summary[0])
        if md.summary[1:]:
            print '  <div class="preborder">'
            print '    <pre>%s</pre>' % '\n'.join(md.summary[1:])
            print '  </div>'
        if md.info:
            print '  <div class="preborder">'
            print '    <pre>%s</pre>' % '\n'.join(md.info)
            print '  </div>'

        if md.functions:
            print '    <h4>Commands</h4>'
        for f in md.functions:
            print '    <a name="%s.%s" />' % (md.name, f.name)
            print '    <table class="details">'
            print '      <tr class="details">'
            print '        <td class="dfname">%s</td>' % f.name
            print '        <td class="dfdesc">%s</td></tr>' % htmlenc(f.doc[0])
            print '      </tr>'
            print '      <tr class="details">'
            print '        <td class="dfcplabel">%s</td>' % 'cperm'
            print '        <td class="dfcpvalue">%s</td>' % htmlenc(f.cperm)
            print '      </tr>'

            print '      <tr class="details">'
            print '        <td class="dfusagelabel">%s</td>' % 'usage'
            print '        <td class="dfusagevalue">%s</td>' % htmlenc(f.doc[1])
            print '      </tr>'

            for line in f.doc[2:]:
                print '      <tr class="details">'
                print '        <td colspan=2 class="dfdoc">%s</td>' % htmlenc(line)
                print '      </tr>'
            print '    </table>'

        if md.settings:
            print '    <h4>Settings</h4>'

        for s in md.settings:
            print '    <a name="%s.%s" />' % (md.name, s.name)
            print '    <table class="details">'
            print '      <tr class="details">'
            print '        <td class="dsname">%s</td>' % s.name
            doc = s.doc or '(no description)'
            print '        <td class="dsdesc">%s</td></tr>' % htmlenc(doc)
            print '      </tr>'
            print '      <tr class="details">'
            print '        <td class="dsdeflabel">%s</td>' % 'default'
            print '        <td class="dsdefvalue">%s</td>' % htmlenc(s.default)
            print '      </tr>'
            print '      <tr class="details">'
            print '        <td class="dscplabel">%s</td>' % 'get cperm'
            print '        <td class="dscpvalue">%s</td>' % htmlenc(s.get_cperm.format())
            print '      </tr>'
            print '      <tr class="details">'
            print '        <td class="dscplabel">%s</td>' % 'set cperm'
            print '        <td class="dscpvalue">%s</td>' % htmlenc(s.set_cperm.format())
            print '      </tr>'
            print '    </table>'

    print '  </body>'
    print '</html>'


html_replace_list = [(r'<', '&lt;'),
                     (r'>', '&gt;')]
html_replace_list = [(re.compile(a), b) for (a, b) in html_replace_list]
def htmlenc(text):
    for html_thing, replacement in html_replace_list:
        text = html_thing.sub(replacement, str(text))
    return text

def fixdoc(obj):
    doc = getattr(obj, '__doc__', '')
    if not doc: return []
    lines = [ line.strip() for line in doc.split('\n') ]
    while lines[-1] == '': lines = lines[:-1]
    return lines

if __name__ == '__main__':
    namelist, load_path = get_options(sys.argv[1:])
    mlist = load_modules(namelist, load_path)
    md_list = []
    for m in mlist:
        md_list.append(get_docs(m))
    dump_all_html(md_list)
