#!/usr/bin/python2
import re
import time

class FloodProtector:
    """Here's how this algorithm works:

    It limits the time between "events".  What constitutes and event is
    determined by "messages", which is a regex.  Every message passed
    in to self.check that matches messages is a throttled event.

    The instance keeps a running timer.  Each time an event occurs, the
    following happens:

      1) if the timer is less than the current time, it is set to the
         current time

      2) if the timer is more than N seconds ahead of the current time,
         where (N, D) appear in "delays", then self.check sleeps for
         D seconds.

      3) "step" seconds are added to the timer.

    In the simplest case, we could say
      step = 2
      delays = ((9, 3), )
    Then, every time a message came in, the timer would be advanced by 2,
    and if the timer got 9 or more seconds ahead of the wall clock,
    self.check would sleep for 3 seconds.  This would have the effect of
    limiting events to roughly one every two seconds with a "burst capacity"
    of about 5 events.
    """

    def __init__(self, step=2, delays=((9, 3), (6, 2), (3, 1)),
                 messages=None, debug=0):
        self.messages = messages or re.compile(r'(PRIVMSG|NOTICE)')
        self.step = step
        self.delays = delays
        self.start = time.time()
        self.debug = debug
        self.timer = 0.0

    def check(self, message):
        if not self.messages.match(message): return 0, 'unprotected message'
        now = time.time()
        if self.timer < now: self.timer = now
        d = self.timer - now

        for diff, delay in self.delays:
            if d >= diff:
                time.sleep(delay)
                break
            delay = 0
        self.timer += self.step
        msg = "time: %.1f, timer: %.1f, delay: %.1f" % \
              (now-self.start, self.timer - now, delay)
        if self.debug: print msg
        return delay, msg

if __name__ == '__main__':
    fp = FloodProtector(debug=1)
    start = time.time()
    while 1:
        #s = raw_input()
        fp.check('PRIVMSG ')


