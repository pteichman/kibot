#!/usr/bin/env python
import sys
import os
import os.path

'''This module is used to fork the current process into a daemon.
    Almost none of this is necessary (or advisable) if your daemon 
    is being started by inetd. In that case, stdin, stdout and stderr are 
    all set up for you to refer to the network connection, and the fork()s 
    and session manipulation should not be done (to avoid confusing inetd). 
    Only the chdir() and umask() steps remain as useful.
    References:
        UNIX Programming FAQ
            1.7 How do I get my program to act like a daemon?
                http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
    
        Advanced Programming in the Unix Environment
            W. Richard Stevens, 1992, Addison-Wesley, ISBN 0-201-56317-7.
    '''

def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    '''This forks the current process into a daemon.
    The stdin, stdout, and stderr arguments are file names that
    will be opened and be used to replace the standard file descriptors
    in sys.stdin, sys.stdout, and sys.stderr.
    These arguments are optional and default to /dev/null.
    Note that stderr is opened unbuffered, so
    if it shares a file with stdout then interleaved output
    may not appear in the order that you expect.
    '''
    # Do first fork.
    try: 
        pid = os.fork() 
        if pid > 0:
            sys.exit(0) # Exit first parent.
    except OSError, e: 
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror)    )
        sys.exit(1)
        
    # Decouple from parent environment.
    os.chdir("/") 
    os.umask(0) 
    os.setsid() 
    
    # Do second fork.
    try: 
        pid = os.fork() 
        if pid > 0:
            sys.exit(0) # Exit second parent.
    except OSError, e: 
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror)    )
        sys.exit(1)
        
    # Now I am a daemon!
    
    # Redirect standard file descriptors.
    si = file(stdin, 'r')
    so = file(stdout, 'a+')
    se = file(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

def lock_fd(filename, mode=0777):
    """get a file descriptor (NOT a file object) for a lockfile
    The check/create operation is performed atomically to avoid race
    conditions.
    """
    try:
        fd = os.open(filename, os.O_EXCL|os.O_CREAT|os.O_WRONLY, mode)
    except OSError, msg:
        if msg.strerror == "File exists":
            return None
        else:
            raise msg
    else:
        return fd

def lock_file(filename, contents=None, mode=0777):
    fd = lock_fd(filename, mode)
    if fd is None:
        return 0
    else:
        if contents is None: contents = str(os.getpid())
        os.write(fd, contents)
        os.close(fd)
        return 1

def unlock_file(filename):
    os.unlink(filename)

def cleanup_old_lockfile(filename):
    """clean up an existing lockfile, which contains a pid.  If the file
    does not exist, or the process has terminated (and lockfile removed),
    cleanup_lock will return 1.  If the process exists, or is not KNOWN to be
    done, return 0.

    This is safe to call BEFORE you even try to create the lockfile,
    but you should still use safe lockfile creation.  For example:

      if not cleanup_old_lockfile(filename): sys.exit('lockfile exists')
      if not lock_file(filename): sys.exit('lockfile exists')

    If the latter fails, it's because the lockfile was created BETWEEN the
    two calls.
    """
    if not os.path.exists(filename): return 1
    fo = file(filename)
    try: pid = int(fo.read())
    except ValueError, e:
        # bad pid
        return 0
    if sys.platform == 'linux2' and not os.path.exists('/proc/%i' % pid):
        os.unlink(filename)
        return 1
    return 0

def test_lockfiles():
    filename = '/tmp/lockfile-test'
    print 'using lockfile:', filename
    
    if os.path.exists(filename):
        print "lockfile exists on startup [OK]"
    else:
        print "lockfile not present on startup [OK]"
    
    if cleanup_old_lockfile(filename):
        print 'cleanup succeeded [GOOD]'
    else:
        print 'cleanup failed [BAD]'

    if lock_file(filename):
        print 'created new lockfile [GOOD]'
    else:
        'could not create lockfile [BAD]'

    if lock_file(filename):
        print 'created SECOND lockfile [BAD]'
    else:
        'could not create second lockfile [GOOD]'

    if cleanup_old_lockfile(filename):
        print 'cleanup succeeded [BAD]'
    else:
        print 'cleanup failed [GOOD]'

    print 'removing lock'
    unlock_file(filename)
    if os.path.exists(filename): print "lockfile still present [BAD]"

    print 'creating lockfile for next time... ',
    if lock_file(filename): print 'succeeded [GOOD]'
    else: print 'failed [BAD]'

    

def test_daemonize():
    '''This is an example main function run by the daemon.
    This prints a count and timestamp once per second.
    '''
    daemonize('/dev/null','/tmp/daemon.log','/tmp/daemon.log')
    import time
    sys.stdout.write('Daemon started with pid %d\n' % os.getpid() )
    sys.stdout.write('Daemon stdout output\n')
    sys.stderr.write('Daemon stderr output\n')
    c = 0
    while 1:
        sys.stdout.write('%d: %s\n' % (c, time.ctime(time.time())) )
        sys.stdout.flush()
        c = c + 1
        time.sleep(1)
    
if __name__ == "__main__":
    test_lockfiles()
    test_daemonize()
