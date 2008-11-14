#!/usr/bin/python2
import os.path
import sys

def mf_split(contents):
    start = 0
    while not contents[start].startswith('# begin core config'): start += 1
    end = start + 1
    while not contents[end].startswith('# end core config'): end += 1
    #while not contents[end].startswith('# end core config'): end += 1
    if start == -1 or end == -1: return(None, None, None)
    head  = contents[:start+1]
    core  = contents[start+1:end]
    foot  = contents[end:]
    return head, core, foot

def process(parts, dirname, names):
    if dirname == '.': return
    for name in names:
        if name == 'Makefile.in':
            fn = os.path.join(dirname, name)
            print "processing %s" % fn

            mf = open(fn, 'r')
            lines = mf.readlines()
            mf.close()

            try: head, core, foot = mf_split(lines)
            except IndexError:
                print "ERROR reading %s - aborting" % fn
                sys.exit(1)

            mf = open(fn, 'w')
            mf.writelines(parts[0] + core + parts[1])
            mf.close()
            
primary_fo = open('Makefile.in', 'r')
lines = primary_fo.readlines()
primary_fo.close()

try: head, core, foot = mf_split(lines)
except IndexError:
    print "ERROR reading primary makefile - aborting"
    sys.exit(1)

#print "HEAD\n" + ''.join(head)
#print "CORE\n" + ''.join(core)
#print "FOOT\n" + ''.join(foot)
#sys.exit()
os.path.walk('.', process, (head, foot))
