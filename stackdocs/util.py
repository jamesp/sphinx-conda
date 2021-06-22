from typing import NamedTuple


def split(x: str, sep: str, maxsplit: int) -> list[str]:
    """Same as x.split but always returns a list
    of length `maxsplit+1`, padded with empty strings."""
    parts = x.split(sep, maxsplit)
    extra = [""] * (maxsplit + 1 - len(parts))
    return [*parts, *extra]


# namedtuple helper for sphinx get_object() return tuple
class object_desc(NamedTuple):
    name: str
    display_name: str
    type: str
    docname: str
    anchor: str
    priority: int
