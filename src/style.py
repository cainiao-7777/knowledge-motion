"""Validate model-suggested colors and keep text legible."""
import re

DEFAULT={'background':'#0a0c17','accent':'#a690ef'}

def luminance(color):
    rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    values=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in rgb]
    return 0.2126*values[0]+0.7152*values[1]+0.0722*values[2]

def contrast(a,b):
    x,y=sorted((luminance(a),luminance(b)),reverse=True)
    return (x+0.05)/(y+0.05)

def choose_palette(value):
    if not isinstance(value,dict): return DEFAULT.copy()
    bg=value.get('background',''); accent=value.get('accent','')
    if not isinstance(bg,str) or not isinstance(accent,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',bg) or not re.fullmatch(r'#[0-9a-fA-F]{6}',accent):
        return DEFAULT.copy()
    if contrast(bg,accent)<3: return DEFAULT.copy()
    return {'background':bg.lower(),'accent':accent.lower()}
