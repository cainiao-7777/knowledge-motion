"""Deterministic Traditional-to-Simplified Chinese conversion."""
from opencc import OpenCC

_CONVERTER=OpenCC('t2s')

def to_simplified(value):
    # OpenCC 逐字词转换繁体中文；非字符串值原样返回。
    if not isinstance(value,str): return value
    return _CONVERTER.convert(value)

def simplify_tree(value):
    # 递归转换模型对象内的文本，同时保留 URL 以免破坏链接。
    if isinstance(value,str): return to_simplified(value)
    if isinstance(value,list): return [simplify_tree(item) for item in value]
    if isinstance(value,dict):
        return {key:(item if key in ('url','source_url') else simplify_tree(item)) for key,item in value.items()}
    return value
