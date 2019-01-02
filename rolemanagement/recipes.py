from itertools import starmap, chain


# May not use this later, but I was considering this to work custom config more easily.
def flatten_dict(dictionary: dict, levels=None):
    """Flatten a nested dictionary structure"""

    def unpack(parent_key, parent_value):
        """Unpack one level of nesting in a dictionary"""
        try:
            items = parent_value.items()
        except AttributeError:
            yield (parent_key, parent_value)
        else:
            for key, value in items:
                yield (parent_key + (key,), value)

    dictionary = {(key,): value for key, value in dictionary.items()}
    if levels:
        for _i in range(levels):
            dictionary = dict(chain.from_iterable(starmap(unpack, dictionary.items())))
            if not any(isinstance(value, dict) for value in dictionary.values()):
                break
    else:
        while True:
            dictionary = dict(chain.from_iterable(starmap(unpack, dictionary.items())))
            if not any(isinstance(value, dict) for value in dictionary.values()):
                break
    return dictionary
