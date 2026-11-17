"""Validate model-suggested colors and keep text legible."""
import re

DEFAULT={'background':'#0a0c17','accent':'#a690ef','secondary':'#66718a','canvas':'dark','motif':'none','style':'editorial'}
def resolve_motif(description):
    """Map a free-form art direction to drawing primitives the renderer can make."""
    text=(description or '').casefold()
    if any(word in text for word in ('orbit','planet','gravity','cosmic','轨道','星体','引力','宇宙')): return 'orbit'
    if any(word in text for word in ('wave','ripple','flowing','water','波纹','水流','流动')): return 'wave'
    if any(word in text for word in ('grid','network','blueprint','data','网格','网络','数据','结构')): return 'grid'
    if any(word in text for word in ('paper','editorial','book','letter','纸','书页','书信','手稿','留白')): return 'editorial'
    return 'none'

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
    secondary=value.get('secondary',accent)
    if not isinstance(secondary,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',secondary):
        secondary=accent
    if contrast(bg,accent)<3 or contrast(bg,secondary)<2.5: return DEFAULT.copy()
    canvas=value.get('canvas','dark')
    if canvas not in ('dark','paper'): canvas='paper' if luminance(bg)>0.45 else 'dark'
    motif=resolve_motif(' '.join(str(value.get(k,'')) for k in ('motif','visual_metaphor','style')))
    style=value.get('style','theme-led')
    if not isinstance(style,str): style='theme-led'
    return {'background':bg.lower(),'accent':accent.lower(),'secondary':secondary.lower(),
            'canvas':canvas,'motif':motif,'style':style[:40]}
