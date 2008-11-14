#!/usr/bin/python

## python stash_convert.py <input> <output>
##    ex:   python stash_convert.py foo.pickle foo.repr

import sys
import kibot.Stasher

input = sys.argv[1]
output = sys.argv[2]

input_stasher = kibot.Stasher.get_stasher(input, readonly=1)
output_stasher = kibot.Stasher.get_stasher(output, autosync=0)
output_stasher.update(input_stasher)
output_stasher.close()
