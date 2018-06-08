import unicodedata
import itertools


def zalgo_callback(self, ret):
    ctx, val, path = ret
    if not val:
        return
    with path.open(mode='a') as f:
        f.write(f"{val.mention}")


def is_zalgo_map(arg_tup):
    """
    This is setup for map_async
    """
    ctx, member, t, path = arg_tup
    ZALGO = ['Mn', 'Me']
    if len(member.display_name) == 0:
        return False
    threshold = len(member.display_name) * float(t)
    count = 0
    for c in member.display_name:
        if (unicodedata.category(c) in ZALGO):
            count += 1
            if count > threshold:
                return (ctx, member, path)
    return (ctx, None, path)


def groups_of_n(n, iterable):
    """
    mostly memory safe handler for grouping by n
    """
    args = [iter(iterable)] * n
    for group in itertools.zip_longest(*args):
        yield [element for element in group if element is not None]
