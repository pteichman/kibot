#!/usr/bin/python2

import sys
import pickle
from pprint import pprint
import kibot.Stasher
import kibot.ircDB as ircDB

st = kibot.Stasher.get_stasher(sys.argv[1], readonly=1, numbackups=0)
print '{'
for k, v in st.items():
    print '  %s: %s,' % (repr(k), repr(v))
print '}'

