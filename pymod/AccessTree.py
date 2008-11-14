import types

class AccessError(Exception):
    pass

class AccessLock:
    """
    AccessLock: a class that supports a single, global lock and a list of
    individual locks simultaneously.  This is useful for switching back
    and forth between fine and coarse locking.  It is up to the user to
    decide the policy -- the class just keeps track of what is set.
    """
    def __init__(self):
        self._individual_locks = []
        self._global_lock = 0

    def __len__(self):
        length = len(self._individual_locks)
        if not self._global_lock == 0:
            length += 1
        return length
    
    def set(self):
        """
        set():
        Set a global lock.
        """
        self._global_lock = 1

    def unset(self):
        """
        unset():
        Unset a global lock.
        """
        self._global_lock = 0

    def is_set(self):
        """
        is_set():
        Test if a global lock is set.
        """
        return self._global_lock
    
    def add(self, item):
        """
        add(item):
        Add an item to a list of individual locked values.
        """
        if not item in self._individual_locks:
            self._individual_locks.append(item)

    def clear(self):
        """
        clear():
        Clear all locks (global or individual).
        """
        self._individual_locks = []
        self._global_lock = 0
        
    def remove(self, item):
        """
        remove(item):
        Remove an item from a list of individual locked values.
        """
        if not item in self._individual_locks:
            raise AccessError, item
        self._individual_locks.remove(item)

    def has(self, item):
        """
        has(item):
        Test if an item belongs to a list of individual locked values.
        """
        return item in self._individual_locks

AT_READ =  1
AT_WRITE = 2

class AccessTree:
    """
    AccessTree: a class that incorporates both tree-like relationships and
    access control.  A node in the tree may contain only other nodes or
    data but not both.  Therefore, a node containing data is automatically
    a terminal node.  Terminal nodes behave like dictionaries (ie,
    terminal_node["3tuple"] = (3,4,5) associates a value with the key
    "3tuple", and terminal_node["3tuple"] retrieves it).  There are two
    styles of node access: attribute style and dictionary style.  The
    first looks like root.node.nextnode.nextnextnode, and so on.  The other
    looks like root["node"]["nextnode"]["nextnextnode"], and so on.  (For
    the attribute style to work on a given node, that node's name must be
    a valid Python attribute name.  Otherwise, you must specify that node
    in dictionary style.  The two styles can be mixed, of course.)  There
    is a single method for listing the contents of a node, terminal or not:
    dir().  The other feature of the AccessTree is that it provides read
    and write locks for all nodes, terminal or not.  These serve to
    protect data and provide a sophisticated access control mechanism
    (in otherwords, an AccessTree with no data is a hierarchical lock).
    """
    
    def __init__(self):
        self._instance_type = "AccessTree"
        self._toplevel = {}
        self._values = None
        self._write_lock = AccessLock()
        self._read_lock = AccessLock()


    def _representation(self,pad):
        resultstr = ''
        lockstr = ''
        if self._read_lock.is_set():
            lockstr = "[R"
            if self._write_lock.is_set():
                lockstr += "W"
            lockstr += "]"
            return "%s%s" % (pad,lockstr)
        if not self._values == None:
            for item in self._values.keys():
                if self._read_lock.has(item):
                    lockstr = "[r"
                    if self._write_lock.has(item):
                        lockstr += "w"
                    lockstr += "]"
                    resultstr += "%s%s = %s\n" % (pad,item,lockstr)
                else:
                    lockstr = ''
                    if self._write_lock.has(item):
                        lockstr = "[w]"
                    resultstr += "%s%s = %s%s\n" % (pad,item,self._values[item],lockstr)
            return resultstr
        for item in self._toplevel.keys():
            if self._read_lock.has(item):
                lockstr = "[r"
                if self._write_lock.has(item):
                    lockstr += "w"
                lockstr += "]"
                resultstr += "%s%s%s\n" % (pad,item,lockstr)
            else:
                lockstr = ''
                if self._write_lock.has(item):
                    lockstr = "[w]"
                if self._toplevel[item]._write_lock.is_set():
                    lockstr += "[W]"
                resultstr += "%s%s%s\n" % (pad,item,lockstr)
                resultstr += self._toplevel[item]._representation(pad+"  ")
        return resultstr
        
    def __str__(self):
        return self._representation('')
    
    def __len__(self):
        if not len(self._read_lock) == 0:
            raise AccessError, "Object is read locked"
        if not self._values == None:
            return len(self._values)
        return len(self._toplevel)

    def __getattr__(self, name):
        if self._read_lock.is_set():
            raise AccessError, "Object is read locked"
        if not self._values == None:
            raise TypeError, "Object is not a top level component"
        if self._toplevel.has_key(name):
            if self._read_lock.has(name):
                raise AccessError, "Object is read locked"
            return self._toplevel[name]
        raise AccessError, name

    def __getitem__(self, key):
        if self._read_lock.is_set():
            raise AccessError, "Object is read locked"
        if not self._toplevel == {}:
            if self._toplevel.has_key(key):
                if self._read_lock.has(key):
                    raise AccessError, "Object is read locked"
                return self._toplevel[key]
            raise AccessError, key
        if self._values == None:
            raise AccessError, key
        if self._values.has_key(key):
            if self._read_lock.has(key):
                raise AccessError, "Object is read locked"
            return self._values[key]
        raise AccessError, key

    def __setitem__(self, key, value):
        if not self._toplevel == {}:
            raise TypeError, "Object is a top level component"
        if self._write_lock.is_set() or self._write_lock.has(key):
            raise AccessError, "Object is write locked"
        if self._values == None:
            self._values = {}
        self._values[key] = value

    def __contains__(self, item):
        return item in self.dir()
    
    def add(self, name):
        """
        add(name):
        Add a subdirectory.  This will raise an exception if the current
        object is a terminal node with dictionary values.
        """
        if self._write_lock.is_set():
            raise AccessError, "Object is write locked"
        if not self._values == None:
            raise TypeError, "Object is not a top level component"
        if not self._toplevel.has_key(name):
            self._toplevel[name] = AccessTree()
            return self._toplevel[name]
        else:
            raise AccessError, "Attribute %s already defined" % (name)
    
    def assign(self, value):
        """
        assign(value):
        If the object is a top level component and value is a
        AccessTree, assign value's subdirectories to the object.
        If the object is a terminal node with dictionary values and
        value is a dictionary, replace the terminal node's dictionary
        with value.  assign will fail if a write lock exists on any
        of the sub items or on the object itself.
        """
        if not len(self._write_lock) == 0:
            raise AccessError, "Object is write locked"
        try:
            if value._instance_type == "AccessTree":
                if not self._values == None:
                    raise TypeError, \
                          "Object is not a top level component"
                self._toplevel = value._toplevel
            else:
                raise TypeError, "Value is not a AccessTree"
        except AttributeError:
            if not self._toplevel == {}:
                raise TypeError, "Object is a top level component"
            if not type(value) == types.DictType:
                raise TypeError, "Value is not a dictionary"
            self._values = value

    def dir(self):
        """
        dir():
        If the currrent object is a directory, list the subdirectories.
        If the current object is a terminal node with dictionary values,
        list the keys.
	"""
        if self._read_lock.is_set():
            raise AccessError, "Object is read locked"
        if not self._values == None:
            return self._values.keys()
        return self._toplevel.keys()
                   

    def nodes(self):
        """
        nodes():
        If the current object is a directory, return a copy of the list
        of subdirectory objects.  If the current object is a terminal node,
        raise an exception.
        """
        if self._read_lock.is_set():
            raise AccessError, "Object is read locked"
        if not self._values == None:
            raise TypeError, "Object is not a top level component"
        return map(None, self._toplevel.values())
    
        
    def unlink(self, name):
        """
        unlink(name):
        If the current object is a directory, try to unlink the subdirectory
        given by name.  If the current object is a terminal node with
        dictionary values, delete the key-value pair whose key is given by
        name.
        """
        if not name in self.dir():
            raise AccessError, name
        if self._write_lock.is_set() or self._write_lock.has(name):
            raise AccessError, "Object is write locked"
        if not self._values == None:
            object = self._values[name]
            del self._values[name]
        else:
            object = self._toplevel[name]
            del self._toplevel[name]
        return object

    def has_lock_mode(self, item, mode):
        """
        has_lock_mode(item, mode):
        Called by has_read_lock and has_write_lock.
        """
        if mode == AT_READ:
            lock = self._read_lock
        elif mode == AT_WRITE:
            lock = self._write_lock
        else:
            raise TypeError, "Lock mode must either be AT_READ or AT_WRITE"
        if item == None:
            return lock.is_set()
        if item in self.dir():
            return lock.has(item)
        raise AccessError, item

    def has_read_lock(self, item=None):
        """
        has_read_lock(item=None):
        Called with no arguments, test for a global read lock.
        Otherwise, test for a read lock on the individual item.
        """
        return self.has_lock_mode(item, AT_READ)

    def has_write_lock(self, item=None):
        """
        has_write_lock(item=None):
        Called with no arguments, test for a global write lock.
        Otherwise, test for a write lock on the individual item.
        """
        return self.has_lock_mode(item, AT_WRITE)

    def has_lock(self, item=None, mode=None):
        """
        has_lock(item=None, mode=None):
        Tests for the existence of a lock.  Arguments are treated
        the same way as for lock and unlock.  See their documentation.
        """
        if not mode in (None, AT_READ, AT_WRITE, AT_READ|AT_WRITE):
            raise TypeError, "Invalid lock mode"
        if mode == None:
            return self.has_read_lock(item) and self.has_write_lock(item)
        answer = 1
        if (mode & AT_READ):
            answer = self.has_read_lock(item)
        if (mode & AT_WRITE):
            answer = self.has_write_lock and answer
        return answer

    def lock_mode(self, item, mode):
        """
        lock_mode(item, mode):
        Called by lock_read and lock_write.
        """
        if mode == AT_READ:
            lock = self._read_lock
        elif mode == AT_WRITE:
            lock = self._write_lock
        else:
            raise TypeError, "Lock mode must be either AT_READ or AT_WRITE"
        if item == None:
            lock.set()
            return
        if item in self.dir():
            if not lock.is_set():
                lock.add(item)
            return
        raise AccessError, item

    def lock_read(self, item=None):
        """
        lock_read(item=None):
        Called with no arguments, set a global read lock.  Otherwise,
        set a read lock for the individual item.
        """
        return self.lock_mode(item,AT_READ)

    def lock_write(self, item=None):
        """
        lock_write(item=None):
        Called with no arguments, set a global write lock.  Otherwise,
        set a write lock for the individual item.
        """
        return self.lock_mode(item,AT_WRITE)
    
    def lock(self, item=None, mode=None):
        """
        lock(item=None, mode=None):
        Called with no arguments, this will set a global read/write lock for
        the object.  Otherwise, it will add an item to a list of locked
        objects.  Acceptable mode values are AT_READ,AT_WRITE,AT_READ|AT_WRITE
        or None (which causes both read and write locks to be set).
        """
        if not mode in (None, AT_READ, AT_WRITE, AT_READ|AT_WRITE):
            raise TypeError, "Invalid lock mode"
        if mode == None:
            self.lock_read(item)
            self.lock_write(item)
            return
        if mode & AT_READ:
            self.lock_read(item)
        if mode & AT_WRITE:
            self.lock_write(item)
        return
        
    def unlock_mode(self, item, mode):
        if mode == AT_READ:
            lock = self._read_lock
        elif mode == AT_WRITE:
            lock = self._write_lock
        else:
            raise TypeError, "Lock mode must be either AT_READ or AT_WRITE"
        if item == None:
            lock.clear()
            return
        if item in self.dir():
            if lock.has(item):
                lock.remove(item)
            return
        raise AccessError, item

    def unlock_read(self, item=None):
        """
        unlock_read(item=None):
        Called with no arguments, unset all read locks.  Otherwise, unset
        a read lock for the individual item.
        """
        return self.unlock_mode(item, AT_READ)

    def unlock_write(self, item=None):
        """
        unlock_write(item=None):
        Called with no arguments, unset all write locks.  Otherwise,
        unset a write lock for the individual item.
        """
        return self.unlock_mode(item, AT_WRITE)
    
    def unlock(self, item=None, mode=None):
        """
        unlock(item=None, mode=None):
        Called with no arguments, this will remove all locks.  Otherwise,
        it will remove an item from a list of locked objecs.  Acceptable
        modes are AT_READ,AT_WRITE,AT_READ|AT_WRITE or None (which causes
        both read and write locks to be unset).
        """
        if not mode in (None, AT_READ, AT_WRITE, AT_READ|AT_WRITE):
            raise TypeError, "Invalid lock mode"      
        if mode == None:
            self.unlock_read(item)
            self.unlock_write(item)
            return
        if mode & AT_READ:
            self.unlock_read(item)
        if mode & AT_WRITE:
            self.unlock_write(item)
        return

