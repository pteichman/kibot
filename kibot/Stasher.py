#!/usr/bin/python
import re
import cPickle
import shelve
import os
import os.path
import shutil
import pprint

class StasherError(Exception): pass

class BaseStasher:
    def __init__(self, file, autosync=1, readonly=0,
                 checkkeys=0, checkvalues=0, numbackups=5):
        self.file = file
        self._autosync = autosync
        self._readonly = readonly

        # different formats have different restrictions on legal keys/values
        # check* raises an exception if the key/value doesn't conform to the
        # lowest common denominator.  With check* off, you are responsible
        # keeping your keys/values sane
        self._checkkeys = checkkeys
        self._checkvalues = checkvalues

        self._numbackups = numbackups
        
        self.dict = {}

        self.open()
        
    def __repr__(self):
        st = '{\n'
        for k in self.keys():
            st = st + '  %s: %s,\n' % (repr(k), pprint.pformat(self[k]))
        st = st + '}\n'
        return st

    def _load(self):
        pass
    
    #################################

    def update(self, dict):
        if self._readonly:
            raise StasherError, "stasher is read-only"
        for key, value in dict.items():
            if self._checkkeys:   self._check_key(key)
            if self._checkvalues: self._check_value(value)
            self.dict[key] = value
        if self._autosync: self.sync()

    def items(self):
        if hasattr(self.dict, 'items'):
            return self.dict.items()
        else:
            keys = self.dict.keys()
            values = [self.dict[key] for key in keys]
            return zip(keys, values)

    def get_dict(self):
        """return a true-dict copy"""
        newdict = {}
        for k in self.keys():
            newdict[k] = self.dict[k]
        return newdict

    def backup(self):
        if not self._numbackups: return
        if not os.path.exists(self.file): return
        first = '%s.1' % self.file
        if os.path.exists(first) and not self._differ(self.file, first): return
        last = '%s.%i' % (self.file, self._numbackups)
        if os.path.exists(last): os.unlink(last)
        for i in range(self._numbackups-1, 0, -1):
            a = '%s.%i' % (self.file, i)
            b = '%s.%i' % (self.file, i+1)
            if os.path.exists(a): os.rename(a, b)
        shutil.copyfile(self.file, first)
                
    def _differ(self, file1, file2):
        ## OK, this could be MUCH smarter
        f1 = open(file1)
        f2 = open(file2)
        ret = 0
        while 1:
            d1 = f1.read(8096)
            d2 = f2.read(8096)
            if not d1 == d2:
                ret = 1
                break
            if not d1:
                break
        f1.close()
        f2.close()
        return ret
    
    def close(self):
        pass
        
    def sync(self):
        pass

    def open(self):
        self.backup()
        ## if we have an error, make the object readonly...
        ## otherwise, it's easy to overrwrite mostly-good data.  This
        ## is especially true with repr, for example
        try:
            self._load()
        except:
            self._readonly = 1
            raise
        
    _key_re = re.compile(r'^[a-zA-Z_][a-zA-Z_0-9]*$')
    def _check_key(self, key):
        if not self._key_re.match(key):
            raise StasherError, "Bad key: %s" % key

    def _check_value(self, value):
        pass

    def keys(self):
        return self.dict.keys()

    def has_key(self, key):
        return self.dict.has_key(key)

    def get(self, key, default=None):
        if self.dict.has_key(key):
            return self[key]
        return default

    def __len__(self):
        return len(self.dict)

    def __getitem__(self, key):
        return self.dict[key]

    def __setitem__(self, key, value):
        if self._readonly:
            raise StasherError, "stasher is read-only"
        if self._checkkeys:   self._check_key(key)
        if self._checkvalues: self._check_value(value)
        self.dict[key] = value
        if self._autosync: self.sync()
        
    def __delitem__(self, key):
        if self._readonly:
            raise StasherError, "stasher is read-only"
        del self.dict[key]
        if self._autosync: self.sync()

    def __del__(self):
        self.close()

class ShelveStasher(BaseStasher):
    def _load(self):
        if self._readonly:
            self.dict = shelve.open(self.file, 'r')
        else:
            self.dict = shelve.open(self.file)
        
    def close(self):
        try: self.dict.close()
        except AttributeError: pass
        
    def sync(self):
        self.dict.sync()

class PickleStasher(BaseStasher):
    def _load(self):
        if os.path.exists(self.file):
            fo = open(self.file, 'rb')
            self.dict = cPickle.load(fo)
            fo.close()
        else:
            self.dict = {}

    def close(self):
        self.sync()

    def sync(self):
        if not self._readonly:
            fo = open(self.file, 'wb')
            cPickle.dump(self.dict, fo, 1)
            fo.close()
        
class ReprStasher(BaseStasher):
    def _load(self):
        self.dict = {}
        if os.path.exists(self.file):
            execfile(self.file, self.dict)
            del self.dict['__builtins__']
            
    def close(self):
        self.sync()

    def sync(self):
        if not self._readonly:
            fo = open(self.file, 'w')
            pprinter = pprint.PrettyPrinter(stream=fo)
            for k, v in self.dict.items():
                fo.write("%s = " % k)
                pprinter.pprint(v)
            fo.close()

_stasher_formats = {'pickle': PickleStasher,
                    'shelve': ShelveStasher,
                    'repr':   ReprStasher}
def get_stasher(file, format=None, **kwargs):
    if format is None: format = guess_format(file)
    driver = _stasher_formats[format]
    return driver(file, **kwargs)

def guess_format(filename):
    # can probably make this smarter
    for k in _stasher_formats.keys():
        if filename.endswith('.'+k): return k
    raise StasherError('Could not guess format for file: %s' % filename)

def test():
    testfile = 'testfile'
    dict = {'foo': 'bar', 'baz': 13}

    for format, klass in _stasher_formats.items():
        print '---------- %s ----------' % format
        fn  = "%s.%s" % (testfile, format)
        st = klass(fn)
        for k, v in dict.items():
            st[k] = v
        st.close()
        
        st.open()
        for k in st.keys():
            print k, st[k]
        st.close()
        #os.unlink(fn)

if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['test']:
        test()
    elif sys.argv[1] == 'dump':
        filename = sys.argv[2]
        st = get_stasher(filename, format=None, readonly=1)
        pprint.pprint(st)
