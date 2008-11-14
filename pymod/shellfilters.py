import os
from stat import *

__common_directories = ['/usr/bin', '/usr/games', '/usr/local/bin',
                        '/usr/local/games']

__common_filter_names = ['ken', 'b1ff', 'censor', 'chef', 'cockney', 'eleet',
                         'fudd', 'jethro', 'jibberish', 'jive', 'kraut',
                         'ky00te', 'newspeak', 'nyc', 'rasterman', 'spammer',
                         'studly', 'upside-down', 'brooklyn', 'drawl',
                         'funetak', 'pansy', 'postmodern', 'redneck',
                         'valspeak', 'warez']

def locate_shell_filters():
    result = {}
    for d in __common_directories:
        for n in __common_filter_names:
            try:
                if os.stat("%s/%s" % (d,n))[0] & S_IXOTH and \
                       not result.has_key(n):
                    result[n] = "%s/%s" % (d,n)
            except OSError:
                pass
    return result

    
