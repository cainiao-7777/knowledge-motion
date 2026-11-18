"""Render a storyboard into a local MP4 with generated graphical frames."""
import math
import os
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from src.storyboard import validate_storyboard
from src.style import choose_palette, contrast
from src.audio import create_effects_track

WIDTH, HEIGHT, FPS = 1280, 720, 24

@lru_cache(maxsize=16)
def font(size):
    for candidate in ('C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/simhei.ttf'):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    raise RuntimeError('未找到中文字体，请安装微软雅黑或黑体')

def wrapped(draw, text, face, max_width):
    lines=[]
    for paragraph in text.splitlines():
        line=''
        for character in paragraph:
            if line and draw.textlength(line+character, font=face) > max_width:
                lines.append(line)
                line=character
            else:
                line+=character
        if line: lines.append(line)
    return lines

def _tint(color, amount=0.16):
    return tuple(round(channel*(1-amount)+255*amount) for channel in color)

def draw_background_motif(draw, motif, accent, light):
    # 按模型选出的主题意象绘制低对比度背景纹理，不让纹理压过正文。
    line=_tint(accent,0.70 if light else 0.24)
    if motif=='grid':
        for x in range(48,WIDTH,64): draw.line((x,90,x,635),fill=line,width=1)
        for y in range(105,635,64): draw.line((48,y,1232,y),fill=line,width=1)
    elif motif=='orbit':
        for radius in (110,170,230):
            draw.ellipse((1010-radius,355-radius,1010+radius,355+radius),outline=line,width=1)
        draw.ellipse((1002,347,1018,363),fill=accent)
    elif motif=='wave':
        for layer in range(5):
            points=[]
            for x in range(0,WIDTH+1,24):
                y=510+layer*24+int(15*math.sin(x/115+layer*0.72))
                points.append((x,y))
            draw.line(points,fill=line,width=2)
    elif motif=='editorial':
        draw.rectangle((0,0,20,HEIGHT),fill=accent)
        draw.line((92,94,1188,94),fill=line,width=3)
    elif motif=='door':
        for offset in range(0,WIDTH,68):
            draw.line((offset,120,offset-120,400),fill=line,width=1)

def draw_theme_metaphor(draw, motif, description, accent, foreground, progress, beat_pulse, layout):
    # 把自由的主题隐喻映射为当前绘图器支持的程序图形，并随叙事逐步变化。
    if motif=='fracture':
        box=(900,200,1180,500)
        draw.ellipse(box,outline=accent,width=2+round(2*beat_pulse))
        if any(word in (description or '').casefold() for word in ('面具','mask','假面')):
            draw.arc((940,270,1020,325),190,345,fill=foreground,width=3)
            draw.arc((1060,270,1140,325),190,345,fill=foreground,width=3)
            draw.arc((970,340,1110,410),15,165,fill=accent,width=3)
        cracks=[[(1040,200),(1022,250),(1054,290),(1028,330),(1050,370),(1018,420),(1030,460),(1010,500)],
                [(1050,290),(1100,265),(1130,235)],[(1028,330),(970,310),(930,280)],
                [(1050,370),(1110,395),(1150,440)]]
        visible=max(2,min(8,round(2+progress*6)))
        for crack in cracks[:1+(visible>4)+(visible>6)]:
            draw.line(crack[:visible],fill=foreground,width=2)
    elif motif=='butterfly':
        draw.ellipse((1008,285,1038,430),fill=accent)
        draw.ellipse((930,245,1018,340),outline=accent,width=3)
        draw.ellipse((1028,245,1116,340),outline=accent,width=3)
        draw.ellipse((944,345,1018,430),outline=foreground,width=2)
        draw.ellipse((1028,345,1102,430),outline=foreground,width=2)
    elif motif=='branch':
        trunk=(1040,480,1040,235)
        draw.line(trunk,fill=accent,width=4)
        for end in ((950,280),(1125,300),(965,365),(1120,390)):
            start_y=350 if end[1]<350 else 420
            draw.line((1040,start_y,end[0],end[1]),fill=accent,width=3)
            draw.ellipse((end[0]-9,end[1]-9,end[0]+9,end[1]+9),fill=foreground)
    elif motif=='orbit':
        cx,cy=(640,408) if layout=='center' else (1040,350)
        sizes=(58,82,106) if layout=='center' else (82,112,146)
        draw.ellipse((cx-48,cy-48,cx+48,cy+48),fill=(4,5,12))
        for radius in sizes:
            draw.arc((cx-radius,cy-radius*0.52,cx+radius,cy+radius*0.52),195,520,fill=accent,width=2+round(2*beat_pulse))
    elif motif=='door':
        x=950 if layout=='asymmetric' else 875
        draw.rectangle((x,205,x+210,510),outline=accent,width=4)
        draw.polygon([(x+12,215),(x+145,250),(x+145,492),(x+12,500)],fill=(32,34,43),outline=foreground)
        draw.ellipse((x+127,365,x+139,377),fill=accent)
        draw.rectangle((x+150,255,x+199,492),fill=(8,9,15))
    elif motif=='editorial':
        draw.rounded_rectangle((930,220,1160,485),radius=4,outline=accent,width=3)
        for y in (285,325,365,405): draw.line((958,y,1128,y),fill=foreground,width=2)

def draw_scene(title, scene, progress, index, count, palette=None, beat_pulse=0.0):
    # 生成单帧：根据主题艺术指导布局，再画正文、说明和本幕图形。
    palette=choose_palette(palette)
    layout=palette.get('layout','editorial')
    light=contrast(palette['background'],'#181927') > contrast(palette['background'],'#eff0f6')
    foreground=(24,25,39) if light else (239,240,246)
    secondary_hex=palette['secondary']
    secondary=tuple(int(secondary_hex[i:i+2],16) for i in (1,3,5))
    if contrast(palette['background'],secondary_hex)<4.5: secondary=foreground
    accent=tuple(int(palette['accent'][i:i+2],16) for i in (1,3,5))
    divider=(192,184,162) if light else (55,54,73)
    panel=(132,124,110) if light else (95,88,129)
    image=Image.new('RGB',(WIDTH,HEIGHT),palette['background'])
    d=ImageDraw.Draw(image)
    draw_background_motif(d,palette['motif'],accent,light)
    art_progress=((index-1)+progress)/max(1,count-1)
    draw_theme_metaphor(d,palette['motif'],palette.get('visual_metaphor',''),accent,foreground,art_progress,beat_pulse,layout)
    d.line((60,73,1220,73), fill=divider, width=1)
    d.text((64,35),'KNOWLEDGE  /  知识大赏',font=font(18),fill=secondary)
    d.text((1095,35),f'{index:02d} / {count:02d}',font=font(18),fill=secondary)
    title_face=font(28)
    title_text=title[:24]
    title_x=(WIDTH-d.textlength(title_text,font=title_face))/2 if layout=='center' else 72 if layout=='asymmetric' else 64
    title_y=105 if layout=='center' else 145 if layout=='asymmetric' else 140
    d.text((title_x,title_y),title_text,font=title_face,fill=accent)
    text_width=980 if layout=='center' else 650 if layout=='asymmetric' else 750
    y=190 if layout=='center' else 285 if layout=='asymmetric' else 210
    available_height=520-y
    heading=None;lines=[];line_height=0
    # 从大字号开始尝试；如果正文高度放不下，再逐级缩小字号。
    for size in (56,50,44,38,34,30,26,22):
        candidate=font(size)
        candidate_lines=wrapped(d,scene['text'],candidate,text_width)
        candidate_line_height=round(size*1.28)
        if len(candidate_lines)*candidate_line_height<=available_height:
            heading=candidate;lines=candidate_lines;line_height=candidate_line_height
            break
    if heading is None:
        raise ValueError('这幕主文字仍无法排入画面，请拆成更多分镜')
    for line in lines:
        text_x=(WIDTH-d.textlength(line,font=heading))/2 if layout=='center' else 82 if layout=='asymmetric' else 64
        d.text((text_x,y),line,font=heading,fill=foreground)
        y+=line_height
    caption_width=900 if layout=='center' else 720 if layout=='asymmetric' else 740
    caption_text=scene.get('caption','')
    sub=None;caption_lines=[];caption_line_height=0
    for size in (22,20,18,16):
        candidate=font(size)
        candidate_lines=wrapped(d,caption_text,candidate,caption_width)
        candidate_line_height=round(size*1.35)
        if len(candidate_lines)*candidate_line_height<=100:
            sub=candidate;caption_lines=candidate_lines;caption_line_height=candidate_line_height
            break
    if sub is None:
        sub=font(16);caption_lines=wrapped(d,caption_text,sub,caption_width)[:4];caption_line_height=22
    for j,line in enumerate(caption_lines):
        caption_x=(WIDTH-d.textlength(line,font=sub))/2 if layout=='center' else 82 if layout=='asymmetric' else 67
        d.text((caption_x, 540+j*caption_line_height),line,font=sub,fill=secondary)
    if scene.get('type') == 'matrix':
        cells = scene['data']['cells']
        for i, cell in enumerate(cells):
            x, y = 865 + (i % 2) * 160, 210 + (i // 2) * 108
            border=tuple(min(255,int(channel+45*beat_pulse)) for channel in accent)
            d.rounded_rectangle((x,y,x+145,y+95),radius=8,outline=border,width=2+round(2*beat_pulse))
            d.text((x+18,y+26),cell,font=font(28),fill=foreground)
    elif scene.get('type') == 'flow':
        data=scene.get('data') if isinstance(scene.get('data'),dict) else {}
        nodes=data.get('nodes') if isinstance(data.get('nodes'),list) else []
        labels=[x for x in nodes if isinstance(x,str) and x.strip()][:3]
        if not labels: labels=['步骤 1','步骤 2','步骤 3']
        for i,label in enumerate(labels):
            y=210+i*100
            d.rounded_rectangle((870,y,1180,y+68),radius=10,outline=panel,width=2)
            d.text((895,y+16),label[:12],font=font(24),fill=accent if progress >= i*0.2 else secondary)
            if i<len(labels)-1: d.line((1025,y+70,1025,y+98),fill=accent,width=2)
    elif scene.get('type') == 'comparison':
        data=scene.get('data') if isinstance(scene.get('data'),dict) else {}
        labels=[data.get('left','A'),data.get('right','B')]
        for side, x in enumerate((862,1036)):
            border=tuple(min(255,int(channel+45*beat_pulse)) for channel in accent)
            d.rounded_rectangle((x,245,x+145,425),radius=12,outline=border,width=2+round(2*beat_pulse))
            label=labels[side] if isinstance(labels[side],str) and labels[side].strip() else ('A' if side == 0 else 'B')
            label_face=font(25)
            for j,line in enumerate(wrapped(d,label[:14],label_face,120)[:2]):
                width=d.textlength(line,font=label_face)
                d.text((x+(145-width)/2,302+j*34),line,font=label_face,fill=accent)
        d.line((1008,335,1035,335),fill=accent,width=2)
    else:
        if palette['motif']=='none':
            radius=110+round(8*beat_pulse)
            cx,cy=1030,345
            ring=(cx-radius,cy-radius,cx+radius,cy+radius)
            d.ellipse(ring,outline=divider,width=5)
            d.arc(ring,-90,-90+max(1,int(progress*360)),fill=accent,width=6+round(3*beat_pulse))
            d.text((990,318),f'{index:02d}',font=font(58),fill=foreground)
        else:
            d.text((1128,458),f'{index:02d}',font=font(24),fill=accent)
    d.line((64,651,1216,651),fill=divider,width=3)
    d.line((64,651,64+int(1152*((index-1+progress)/count)),651),fill=accent,width=3)
    return image

def apply_rhythm_motion(image, intensity, beat_index):
    """Add a brief, deterministic punch-in and camera nudge on musical accents."""
    if intensity < 0.03:
        return image
    width,height=image.size
    scale=1.0+0.018*intensity
    scaled=image.resize((round(width*scale),round(height*scale)),Image.Resampling.LANCZOS)
    extra_x=scaled.width-width
    extra_y=scaled.height-height
    direction=-1 if beat_index%2 else 1
    nudge_x=round(4*intensity*direction)
    nudge_y=round(3*intensity*(1 if beat_index%3==0 else -1))
    left=max(0,min(extra_x,extra_x//2+nudge_x))
    top=max(0,min(extra_y,extra_y//2+nudge_y))
    return scaled.crop((left,top,left+width,top+height))

def render_video(storyboard, destination, music=None, beats=None):
    # 将故事板逐帧交给 FFmpeg；画面和音频合成成功后才替换成片。
    validate_storyboard(storyboard)
    if not shutil.which('ffmpeg'):
        raise RuntimeError('未找到 FFmpeg，请先安装并配置 PATH')
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    # A temporary output prevents a failed render from destroying a previous video.
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        silent=Path(temp)/'video.mp4'
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{WIDTH}x{HEIGHT}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p',str(silent)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            previous=None
            beats=beats or []
            elapsed=0.0
            for index,scene in enumerate(storyboard['scenes'],1):
                count=round(scene['duration_seconds']*FPS)
                for frame in range(count):
                    global_time=elapsed+frame/FPS
                    # 只取当前附近的拍点，用脉冲强度驱动短暂推近和抖动。
                    active=[(beat_index,beat) for beat_index,beat in enumerate(beats) if abs(global_time-beat)<0.18]
                    beat_index,nearest=min(active,key=lambda item:abs(global_time-item[1])) if active else (-1,None)
                    beat_pulse=math.exp(-((global_time-nearest)/0.075)**2) if nearest is not None else 0.0
                    art_direction=storyboard.get('art_direction',storyboard.get('palette'))
                    image=draw_scene(storyboard['title'],scene,frame/max(1,count-1),index,len(storyboard['scenes']),art_direction,beat_pulse)
                    image=apply_rhythm_motion(image,beat_pulse,beat_index)
                    # 新镜头头半秒与上一幕末帧交叠，形成交叉淡化。
                    if previous is not None and frame < FPS//2:
                        image=Image.blend(previous,image,(frame+1)/(FPS//2))
                    proc.stdin.write(image.tobytes())
                previous=draw_scene(storyboard['title'],scene,1,index,len(storyboard['scenes']),storyboard.get('art_direction',storyboard.get('palette')))
                elapsed+=scene['duration_seconds']
            proc.stdin.close()
            error=proc.stderr.read().decode('utf-8','replace')
            if proc.wait()!=0: raise RuntimeError('视频渲染失败：'+error[-500:])
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        completed=Path(temp)/'complete.mp4'
        if music and Path(music).is_file():
            duration=sum(scene['duration_seconds'] for scene in storyboard['scenes'])
            positions=[]; elapsed=0
            for scene in storyboard['scenes'][:-1]:
                elapsed+=scene['duration_seconds']; positions.append(elapsed)
            effects=Path(temp)/'effects.wav'
            create_effects_track(effects,duration,positions)
            fade_start=max(0.0,duration-1.0)
            fade_duration=min(1.0,duration)
            # 配乐降低电平并在结束前淡出，再叠加单独生成的转场音效。
            audio_filter=f'[1:a]volume=0.48,afade=t=out:st={fade_start}:d={fade_duration},apad[music];[music][2:a]amix=inputs=2:duration=shortest:normalize=0[a]'
            cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(silent),'-i',str(music),'-i',str(effects),'-filter_complex',audio_filter,'-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-shortest',str(completed)]
            result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace')
            if result.returncode: raise RuntimeError('音乐合成失败：'+result.stderr[-500:])
            os.replace(completed,destination)
        else:
            os.replace(silent,destination)
    return str(destination)
