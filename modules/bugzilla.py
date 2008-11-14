#!/usr/bin/python2 -tt
import urllib as _urllib
import string as _string
from libxml2 import parseDoc as _parseDoc

import kibot.BaseModule

class BugError(Exception):
    def __init__(self, args = None):
        Exception.__init__(self)
        self.args = args

class bugzilla(kibot.BaseModule.BaseModule):
    """Show a link to a bug report with a brief description"""

    _stash_format = 'repr'
    _stash_attrs = ['zilla_map']
    def __init__(self, bot):
        self.bot = bot
        self.zilla_map = {}
        self._unstash()
        if not self.zilla_map: self._add_default_defs()
        self.bot.log(1, 'Initialized bugzilla module')

    def _add_default_defs(self):
        self.zilla_map = {
            'rh': ['http://bugzilla.redhat.com/bugzilla', 'Red Hat'],
            'gnome': ['http://bugzilla.gnome.org', 'Gnome'],
            'xim': ['http://bugzilla.ximian.com', 'Ximian'],
            'moz': ['http://bugzilla.mozilla.org', 'Mozilla']
            }
        self._stash()
    
    _addzilla_cperm = 'manager'
    def addzilla(self, cmd):
        """Add a bugzilla to the list of defined bugzillae.
        Format: addzilla shorthand url description
        E.g.: addzilla rh http://bugzilla.redhat.com/bugzilla Red Hat Zilla"""
        try:
            words = cmd.args.split(' ')
            shorthand = words.pop(0)
            url = words.pop(0)
            description = ' '.join(words)
        except:
            cmd.nreply('Invalid format, please see help addzilla')
            return
        if not description:
            cmd.nreply('Please provide a description for this bugzilla')
            return
        self.zilla_map[shorthand] = [url, description]
        self._stash()
        cmd.reply('Added bugzilla entry for "%s" with shorthand "%s"' % (
            description, shorthand))
        return

    _delzilla_cperm = 'manager'
    def delzilla(self, cmd):
        """Delete a bugzilla from the list of define bugzillae.
        Format: delzilla shorthand
        E.g.: delzilla rh"""
        shorthand = cmd.args
        if shorthand not in self.zilla_map:
            cmd.nreply('Bugzilla "%s" not defined. Try zillalist.' % shorthand)
            return
        del self.zilla_map[shorthand]
        self._stash()
        cmd.reply('Deleted bugzilla "%s"' % shorthand)
        return

    _listzilla_cperm = 1
    def listzilla(self, cmd):
        """List defined bugzillae.
        Format: listzilla [shorthand]
        E.g.: listzilla rh; or just listzilla"""
        shorthand = cmd.args
        if shorthand:
            if shorthand not in self.zilla_map:
                cmd.nreply('No such bugzilla defined: "%s".' % shorthand)
                return
            url, description = self.zilla_map[shorthand]
            cmd.reply('%s: %s, %s' % (shorthand, description, url))
            return
        else:
            shorthands = self.zilla_map.keys()
            if not shorthands:
                cmd.reply('No bugzillae defined. Add some with "addzilla"!')
                return
            cmd.reply('Defined bugzillae: %s' % ' '.join(shorthands))
            return    

    _bug_cperm = 1
    def bug(self, cmd):
        """Look up a bug number in a bugzilla.
        Format: bug shorthand number
        E.g.: bug rh 10301"""
        try: shorthand, num = cmd.args.split(' ')
        except:
            cmd.nreply('Invalid format. Try help bug')
            return
        if shorthand not in self.zilla_map:
            cmd.nreply('Bugzilla "%s" is not defined.' % shorthand)
            return
        if not self._is_bug_number(num):
            cmd.nreply('"%s" does not seem to be a number' % num)
            return
        self.bot.log(5, 'Lookup for %s, bug #%s' % (shorthand, num))
        url, desc = self.zilla_map[shorthand]
        queryurl = '%s/xml.cgi?id=%s' % (url, num)
        self.bot.log(5, 'queryurl=%s' % queryurl)
        try:
            summary = self._get_short_bug_summary(queryurl, desc, num)
        except BugError, e:
            cmd.reply(e)
            return
        except IOError, e:
            msg = '%s. Try yourself: %s' % (e, queryurl)
            cmd.nreply(msg)
            return

        report = {}
        self.bot.log(3, 'Making a report')
        report['zilla'] = desc
        report['id'] = num
        report['url'] = '%s/show_bug.cgi?id=%s' % (url, num)
        report['title'] = summary['title']
        report['summary'] = self._mk_component_severity_status(summary)
        cmd.reply('%(zilla)s bug #%(id)s: %(title)s' % report)
        cmd.reply('  %(summary)s' % report)
        cmd.reply('  %(url)s' % report)
        self.bot.log(3, 'All done with bugzilla')
        return

    def _mk_component_severity_status(self, summary):
        self.bot.log(5, '>_mk_stuff_in_braces')
        ary = []
        if summary.has_key('component'):
            ary.append('Component: %s' % summary['component'])
        if summary.has_key('severity'):
            ary.append('Severity: %s' % summary['severity'])
        if summary.has_key('status'):
            if summary.has_key('resolution'):
                ary.append('Status: %s/%s' %
                           (summary['status'], summary['resolution']))
            else:
                ary.append('Status: %s' % summary['status'])
        out = _string.join(ary, ', ')
        self.bot.log(5, '<_mk_stuff_in_braces')
        return out

    def _is_bug_number(self, bug):
        try: int(bug)
        except: return 0
        else: return 1
        
    def _get_short_bug_summary(self, url, desc, num):
        self.bot.log(5, '>_get_short_bug_summary')
        bugxml = self._getbugxml(url, desc)
        self.bot.log(3, 'Trying to parse the xml')
        try: zdom = _parseDoc(bugxml)
        except Exception, e:
            self.bot.log(3, 'Error parsing XML')
            self.bot.log(5, '<_get_short_bug_summary')
            msg = 'Could not parse XML returned by %s bugzilla: %s'
            raise BugError(msg % (desc, e))
        bnode = zdom.getRootElement().children
        summary = {}
        while bnode:
            props = bnode.properties
            while props:
                if props.name == 'error':
                    errtxt = props.content
                    zdom.freeDoc()
                    msg = 'Error getting %s bug #%s: %s' % (desc, num, errtxt)
                    self.bot.log(3, msg)
                    self.bot.log(5, '<_get_short_bug_summary')
                    raise BugError(msg)
            self.bot.log(3, 'Trying to get the data from the XML file')
            kid = bnode.children
            while kid:
                if kid.name == 'short_desc':
                    summary['title'] = self._getnodetxt(kid)
                elif kid.name == 'bug_status':
                    summary['status'] = self._getnodetxt(kid)
                elif kid.name == 'resolution':
                    summary['resolution'] = self._getnodetxt(kid)
                elif kid.name == 'component':
                    summary['component'] = self._getnodetxt(kid)
                elif kid.name == 'bug_severity':
                    summary['severity'] = self._getnodetxt(kid)
                elif kid.name == 'long_desc':
                    # If we're here, we've gone too far and we can stop
                    # parsing
                    break
                kid = kid.next
            if summary: break
            bnode = bnode.next
        zdom.freeDoc()
        self.bot.log(5, '<_get_short_bug_summary')
        self.bot.log(5, 'summary: %s' % summary)
        return summary

    def _getbugxml(self, url, desc):
        self.bot.log(5, '>_getbugxml')
        try: fh = _urllib.urlopen(url)
        except: raise IOError('Connection to %s bugzilla failed' % desc)
        self.bot.log(5, 'Doing a chunked read')
        bugxml = ''
        while 1:
            chunk = fh.read(8192)
            if chunk == '':
                self.bot.log(5, 'Reached EOF')
                break
            self.bot.log(5, 'Read %s bytes' % len(chunk))
            bugxml = bugxml + chunk
        fh.close()
        if not len(bugxml):
            msg = 'Error getting bug content from %s' % desc
            self.bot.log(3, msg)
            self.bot.log(5, '<_getbugxml')
            raise IOError(msg)
        self.bot.log(5, '<_getbugxml')
        return bugxml

    def _getnodetxt(self, node):
        self.bot.log(5, '>_getnodetxt')
        val = node.content
        self.bot.log(1, 'original val=%s' % val)
        props = node.properties
        while props:
            if props.name == 'encoding':
                if props.content == 'base64':
                    import base64
                    try:
                        val = base64.decodestring(val)
                    except:
                        val = 'Cannot convert bug data from base64!'
            props = props.next
        self.bot.log(5, 'final val=%s' % val)
        self.bot.log(5, '<_getnodetxt')
        return val
