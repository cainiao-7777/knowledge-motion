"""Validate model-suggested colors and keep text legible."""
import re

DEFAULT={'background':'#0a0c17','accent':'#a690ef','secondary':'#66718a','canvas':'dark','motif':'none','style':'editorial'}
def resolve_motif(description):
    """Map a free-form art direction to drawing primitives the renderer can make."""
    # 这是渲染器能力映射，不限制大模型写什么视觉隐喻。
    text=(description or '').casefold()
    if any(word in text for word in ('mask','ice','crack','fracture','面具','薄冰','裂纹','裂缝','冰面')): return 'fracture'
    if any(word in text for word in ('butterfly','wing','蝴蝶','翅膀')): return 'butterfly'
    if any(word in text for word in ('branch','tree','分支','树枝','生长')): return 'branch'
    if any(word in text for word in ('door','threshold','doorway','纸门','门扉','门槛','半开的门')): return 'door'
    if any(word in text for word in ('black hole','event horizon','singularity','orbit','planet','gravity','cosmic','黑洞','视界','奇点','轨道','星体','引力','宇宙')): return 'orbit'
    if any(word in text for word in ('wave','ripple','flowing','water','波纹','水流','流动')): return 'wave'
    if any(word in text for word in ('grid','network','blueprint','data','网格','网络','数据','结构')): return 'grid'
    if any(word in text for word in ('paper','editorial','book','letter','纸','书页','书信','手稿','留白')): return 'editorial'
    return 'none'

def resolve_layout(description, motif):
    # 从自由构图描述中挑当前绘图器可以实现的布局方向。
    text=(description or '').casefold()
    if any(word in text for word in ('centered','center composition','central focal','居中','中心构图','中心对称','几何中心','中央聚焦')): return 'center'
    if any(word in text for word in ('lower-left','lower-right','corner','asymmetric','偏左下','偏右下','角落','不对称','大面积空白')): return 'asymmetric'
    if any(word in text for word in ('diagram','schematic','full-frame','full canvas','图解','示意图','全画幅','满版')) or motif in ('grid','orbit','wave'):
        return 'diagram'
    return 'editorial'

def luminance(color):
    rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    values=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in rgb]
    return 0.2126*values[0]+0.7152*values[1]+0.0722*values[2]

def contrast(a,b):
    x,y=sorted((luminance(a),luminance(b)),reverse=True)
    return (x+0.05)/(y+0.05)

def choose_palette(value):
    # 只接受合法颜色；对比不足时回退或替换辅助色，保障文字可读。
    if not isinstance(value,dict): return DEFAULT.copy()
    def extract_color(raw):
        if not isinstance(raw,str): return ''
        match=re.search(r'#[0-9a-fA-F]{6}',raw)
        return match.group(0) if match else ''
    bg=extract_color(value.get('background','')); accent=extract_color(value.get('accent',''))
    if not bg or not accent:
        return DEFAULT.copy()
    secondary=extract_color(value.get('secondary',accent)) or accent
    if contrast(bg,accent)<3: return DEFAULT.copy()
    if contrast(bg,secondary)<3: secondary=accent
    canvas=value.get('canvas','dark')
    if canvas not in ('dark','paper'): canvas='paper' if luminance(bg)>0.45 else 'dark'
    motif=resolve_motif(' '.join(str(value.get(k,'')) for k in ('motif','visual_metaphor','style')))
    style=value.get('style','theme-led')
    if not isinstance(style,str): style='theme-led'
    visual_metaphor=value.get('visual_metaphor','')
    if not isinstance(visual_metaphor,str): visual_metaphor=''
    composition=value.get('composition','')
    if not isinstance(composition,str): composition=''
    motif=resolve_motif(' '.join(str(value.get(k,'')) for k in ('motif','visual_metaphor','style')))
    return {'background':bg.lower(),'accent':accent.lower(),'secondary':secondary.lower(),
            'canvas':canvas,'motif':motif,'style':style[:80],
            'visual_metaphor':visual_metaphor[:240],
            'layout':resolve_layout(composition,motif)}
