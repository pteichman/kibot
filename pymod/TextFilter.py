import os
import popen2
import GibberSpeak
import re
from stat import *

class TextFilterError(Exception):
    pass

class Filter:
    def __init__(self, name):
        self._filter_name = name
        self._bytes_in = 0
        self._bytes_out = 0
        self._result = []

    def BytesIn(self):
        return self._bytes_in

    def BytesOut(self):
        return self._bytes_out

    def ResetByteCounters(self):
        self._bytes_out = 0
        self._bytes_in = 0
        
    def Translate(self, thing):
        for line in thing:
            self._bytes_in += len(line)
            self._bytes_out += len(line)
        self._result = thing
        return thing

    def __call__(self, thing):
        return self.Translate(thing)
        
    def Name(self, name=None):
        if not name == None:
            self._filter_name = name
        return self._filter_name

    def Result(self):
        return self._result
    

class ShellFilter(Filter):
    def __init__(self, name):
        if not self._is_executable(name):
            raise TextFilterError, "Can't execute %s" % (name)
        self._tr_in = None
        self._tr_out = None
        Filter.__init__(self, name)

    def _is_executable(self, name):
        return os.stat(name)[0] & S_IXOTH
    
    def Translate(self, text):
        (self._tr_in, self._tr_out) = popen2.popen2(self._filter_name)
        for line in text:
            self._tr_out.write(line)
            self._bytes_in += len(line)
        self._tr_out.close()
        self._result = self._tr_in.readlines()
        self._tr_in.close()
        for line in self._result:
            self._bytes_out += len(line)
        return self._result
    
    def Name(self, name=None):
        if not name == None:
            if not self._is_executable(name):
                raise TextFilterError, "Can't execute %s" % (name)
        return Filter.name(self,name)


class GibberFilter(Filter):
    def __init__(self, name="gibberobo"):
        self._gibber_re_group = "gp"
        self._gibber_re = re.compile("gibber(?P<%s>[a-zA-Z]+)" % \
                                     (self._gibber_re_group))
        self._gibber_match = None
        self._set_pattern(self._extract_pattern(name))
        Filter.__init__(self,name)

    def _extract_pattern(self, name):
        self._gibber_match = self._gibber_re.match(name)
        if self._gibber_match == None:
            raise TextFilterError, "name must have form 'gibber[pattern]'"
        return self._gibber_match.group(self._gibber_re_group)
    
    def _set_pattern(self,p):        
        try:
            self._gibber = GibberSpeak.GibberSpeaker(p)
        except GibberSpeak.GibberError:
            raise TextFilterError, "Bad gibber pattern: %s" % (p)
        if self._gibber.Consonant() == None:
            raise TextFilterError, \
              "gibber pattern must begin with a vowel and contain a consonant"
        
    def Translate(self, text):
        self._result = []
        for line in text:
            output = self._gibber(line)
            self._result.append(output)
            self._bytes_out += len(output)
            self._bytes_in += len(line)
        return self._result

    def Name(self, name=None):
        if not name == None:
            self._set_pattern(self._extract_pattern(name))
        return Filter.Name(self,name)
        
