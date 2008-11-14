import gibberbase

GibberNoPattern = 0
GibberBadPatternLength = 1
GibberNoInitialVowel = 2
GibberNoConsonant = 3
GibberBadForm = 4
GibberNoDefaultConsonant = 5
GibberNotConsonant = 6
GibberErrorConstants = (GibberNoPattern, GibberBadPatternLength, \
                        GibberNoInitialVowel, GibberNoConsonant, \
                        GibberBadForm, GibberNoDefaultConsonant, \
                        GibberNotConsonant)

class GibberError(Exception):
    def __init__(self,value):
        self.value = value

    def __str__(self):
        if not self.value in GibberErrorConstants:
            return "Undefined Gibber error"
        elif self.value == GibberNoPattern:
            return "Missing Gibber pattern value"
        elif self.value == GibberBadPatternLength:
            return "Gibber pattern needs at least an initial vowel"
        elif self.value == GibberNoInitialValue:
            return "Gibber Pattern must begin with an initial vowel"
        elif self.value == GibberNoConsonant:
            return "Missing Gibber consonant value"
        elif self.value == GibberBadForm:
            return "Gibber pattern and consonant may contain only \
            gibbercharacters"
        elif self.value == GibberNoDefaultConsonant:
            return "Unable to get default Gibber consonant"
        elif self.value == GibberNotConsonant:
            return "Value is not an acceptable consonant"
        
class GibberSpeaker:
    """
    The GibberSpeaker class.  Called with no arguments, the constructor will
    return an instance with no gibber pattern.  Otherwise, the constructor
    expects a single gibber pattern, which must begin with a vowel
    (as set in gibberbase.vowels and gibberbase.exceptions).  It really
    should have at least one consonant as well because of the way it tries
    to make the most "euphonious" gibber words.  Once you have an
    instance with a pattern (set by the constructor or by Pattern),
    simply treat the instance like a function and pass it a string to
    generate gibberspeak.  It is an error to attempt a gibber transformation
    when no pattern is set.
    """
    def __init__(self, gibber=None):
        self._gibber = None
        self._gibberstartconsonant = None
        self._gibberfinalconsonant = None
        self.SetGibber(gibber)
        self.SetGibberConsonant()
        
    def SetGibber(self, gibber=None):
        """
        You probably don't want to call this directly.  It is used by
        the constructor and when the gibber pattern is updated.
        """
        if gibber == None:
            return
        if len(gibber) == 0:
            raise GibberError(GibberBadPatternLength)
        copy = gibber + ' '
        if not gibberbase.IsVowel(copy[0],copy[1]):
            raise GibberError(GibberNoInitialVowel)
        for ch in gibber:
            if not ch in gibberbase.gibbercharacters:
                raise GibberError(GibberBadForm)
        self._gibber = gibber

    def SetGibberConsonant(self, gibberconsonant=None):
        """
        You probably don't want to call this directly.  It is used by
        the constructor and when the gibber pattern is updated.
        """
        if gibberconsonant == None:
            if self._gibber == None:
                return
            if gibberbase.IsConsonant(self._gibber[-1],' '):
                self._startgibberconsonant = self._gibber[-1]
                self._finalgibberconsonant = ''
            else:
                copy = self._gibber + ' '
                gibberlen = len(self._gibber)
                i = 0
                while i < gibberlen and gibberbase.IsVowel(copy[i],copy[i+1]):
                    i += 1
                if i == gibberlen:
                    self._startgibberconsonant = None
                    self._finalgibberconsonant = None
                    raise GibberError(GibberNoDefaultConsonant)
                else:
                    self._startgibberconsonant = copy[i]
                    self._finalgibberconsonant = copy[i]
        else:
            if not len(gibberconsonant) == 1 or \
                   not gibberbase.IsConsonant(gibberconsonant, ' '):
                raise GibberError(GibberNotConsonant)
            else:
                self._startgibberconsonant = gibberconsonant
                if gibberbase.IsConsonant(self._gibber[-1]):
                    self._finalgibberconsonant = ''
                else:
                    self._finalgibberconsonant = gibberconsonant
                
    def Pattern(self, gibber=None):
        """
        Pattern(gibber = None): if called with no arguments, this will
        return the current pattern, otherwise it will attempt to set
        the pattern to the specified value.  Badly formed patterns will
        generate exceptions.
        """
        if not gibber == None:
            self.SetGibber(gibber)
            try:
                self.SetGibberConsonant()
            except:
                pass
        return self._gibber

    def Consonant(self):
        """
        Consonant(): return the current gibber consonant.
        """
        return self._startgibberconsonant

    def __call__(self, str):
        """
        Emulate a callable object.  object(string) will transform string
        into gibber, unless there is no pattern set (in which case it
        will raise an exception).
        """
        if self._gibber == None:
            raise GibberError(GibberNoPattern)
        elif self._startgibberconsonant == None:
            raise GibberError(GibberNoConsonant)
        else:
            return gibberbase.GibberString(str,self._gibber, \
                                            self._startgibberconsonant, \
                                            self._finalgibberconsonant)

    
            
