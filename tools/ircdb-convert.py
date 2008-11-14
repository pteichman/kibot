#!/usr/bin/python2

import sys
import pickle
import os
import os.path
import kibot.Stasher
import kibot.ircDB as ircDB

old, new = sys.argv[1:3]
fo = open(old)
a = pickle.load(fo)
known = a['known']
fo.close()

if os.path.exists(new):
    print 'backing up: %s -> %s.bak' % (new, new)
    os.rename(new, new+'.bak')
st = kibot.Stasher.get_stasher(new)
st.update(known)
st.close()
