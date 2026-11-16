"""Render a storyboard into a local MP4 with generated graphical frames."""
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from src.storyboard import validate_storyboard
from src.style import choose_palette, contrast
from src.audio import create_effects_track

WIDTH, HEIGHT, FPS = 1280, 720, 12

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

def draw_scene(title, scene, progress, index, count, palette=None):
    palette=choose_palette(palette)
    light=contrast(palette['background'],'#181927') > contrast(palette['background'],'#eff0f6')
    foreground=(24,25,39) if light else (239,240,246)
    secondary=foreground
    accent=palette['accent']
    image=Image.new('RGB',(WIDTH,HEIGHT),palette['background'])
    d=ImageDraw.Draw(image)
    d.line((60,73,1220,73), fill=(55,54,73), width=1)
    d.text((64,35),'KNOWLEDGE  /  知识大赏',font=font(18),fill=secondary)
    d.text((1095,35),f'{index:02d} / {count:02d}',font=font(18),fill=secondary)
    d.text((64,140),title[:24],font=font(28),fill=accent)
    heading=font(55)
    lines=wrapped(d,scene['text'],heading,750)
    if len(lines)>4:
        heading=font(42)
        lines=wrapped(d,scene['text'],heading,750)
    if len(lines)>5:
        raise ValueError('分镜文字过长，请缩短后重新生成')
    y=210
    for line in lines:
        d.text((64,y),line,font=heading,fill=foreground)
        y+=72 if heading.size==55 else 58
    sub=font(23)
    for j,line in enumerate(wrapped(d,scene.get('caption',''),sub,740)[:3]):
        d.text((67, 540+j*33),line,font=sub,fill=secondary)
    if scene.get('type') == 'matrix':
        cells = scene['data']['cells']
        for i, cell in enumerate(cells):
            x, y = 865 + (i % 2) * 160, 210 + (i // 2) * 108
            d.rounded_rectangle((x,y,x+145,y+95),radius=8,outline=(95,88,129),width=2)
            d.text((x+18,y+26),cell,font=font(28),fill=foreground)
    elif scene.get('type') == 'comparison':
        for side, x in enumerate((862,1036)):
            d.rounded_rectangle((x,245,x+145,425),radius=12,outline=(95,88,129),width=2)
            d.text((x+50,302),'A' if side == 0 else 'B',font=font(48),fill=accent)
        d.line((1008,335,1035,335),fill=accent,width=2)
    else:
        # Progress arc is drawn from time, so frames are deterministic.
        d.ellipse((920,235,1140,455),outline=(49,48,70),width=5)
        d.arc((920,235,1140,455),-90,-90+max(1,int(progress*360)),fill=accent,width=6)
        d.text((990,318),f'{index:02d}',font=font(58),fill=foreground)
    d.line((64,651,1216,651),fill=(49,48,70),width=3)
    d.line((64,651,64+int(1152*((index-1+progress)/count)),651),fill=accent,width=3)
    return image

def render_video(storyboard, destination, music=None):
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
            for index,scene in enumerate(storyboard['scenes'],1):
                count=round(scene['duration_seconds']*FPS)
                for frame in range(count):
                    image=draw_scene(storyboard['title'],scene,frame/max(1,count-1),index,len(storyboard['scenes']),storyboard.get('palette'))
                    if previous is not None and frame < FPS//2:
                        image=Image.blend(previous,image,(frame+1)/(FPS//2))
                    proc.stdin.write(image.tobytes())
                previous=draw_scene(storyboard['title'],scene,1,index,len(storyboard['scenes']),storyboard.get('palette'))
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
            cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(silent),'-i',str(music),'-i',str(effects),'-filter_complex','[1:a]volume=0.65,apad[music];[music][2:a]amix=inputs=2:duration=shortest:normalize=0[a]','-map','0:v:0','-map','[a]','-c:v','copy','-c:a','aac','-shortest',str(completed)]
            result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace')
            if result.returncode: raise RuntimeError('音乐合成失败：'+result.stderr[-500:])
            os.replace(completed,destination)
        else:
            os.replace(silent,destination)
    return str(destination)
