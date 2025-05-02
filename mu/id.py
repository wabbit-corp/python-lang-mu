import collections.abc

class Id:
    __slots__ = ('_value',)

    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        """Read-only access to the wrapped object."""
        return self._value

    def __hash__(self):
        # Typically id(obj) is used for identity-based hashing
        return hash(id(self._value))

    def __eq__(self, other):
        if not isinstance(other, Id):
            return NotImplemented
        return self._value is other._value
    
    def __repr__(self):
        return f"{self.__class__.__name__}(value={self._value!r})"
    

class IdDict(collections.abc.MutableMapping):
    """
    A dictionary-like container that uses `id(key_object)` as the lookup key,
    storing the original key object to prevent it from being garbage-collected.
    """

    __slots__ = ("_storage",)

    def __init__(self):
        self._storage = {}

    def __getitem__(self, key):
        # We stored (original_key, value) in _storage
        return self._storage[id(key)][1]

    def __setitem__(self, key, value):
        # Store the original key object in the tuple
        self._storage[id(key)] = (key, value)

    def __delitem__(self, key):
        del self._storage[id(key)]

    def __iter__(self):
        """
        Iteration yields the *actual key objects*, not their ids.
        """
        for (stored_key, _) in self._storage.values():
            yield stored_key

    def __len__(self):
        return len(self._storage)

    def __contains__(self, key):
        return id(key) in self._storage

    def keys(self):
        for (stored_key, _) in self._storage.values():
            yield stored_key

    def values(self):
        for (_, value) in self._storage.values():
            yield value

    def items(self):
        for (stored_key, value) in self._storage.values():
            yield (stored_key, value)

    def get(self, key, default=None):
        return self._storage.get(id(key), (None, default))[1]

    def __repr__(self):
        items_str = ', '.join(
            f'{repr(k)}: {repr(v)}' for (k, v) in self._storage.values()
        )
        return f'{self.__class__.__name__}({{{items_str}}})'


# Provide an alias
identitydict = IdDict