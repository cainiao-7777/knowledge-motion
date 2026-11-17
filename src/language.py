"""Deterministic Traditional-to-Simplified Chinese conversion."""
from opencc import OpenCC

_CONVERTER=OpenCC('t2s')

def to_simplified(value):
    if not isinstance(value,str): return value
    return _CONVERTER.convert(value)

def simplify_tree(value):
    if isinstance(value,str): return to_simplified(value)
    if isinstance(value,list): return [simplify_tree(item) for item in value]
    if isinstance(value,dict):
        return {key:(item if key in ('url','source_url') else simplify_tree(item)) for key,item in value.items()}
    return value
