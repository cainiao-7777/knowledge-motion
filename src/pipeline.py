"""Connect research, script generation and rendering into one saved project."""
from pathlib import Path
import os
import shutil
import uuid
from datetime import datetime
from src.projects import create_project, save_project, project_dir, load_project
from src.research import search_sources
from src.generator import generate_storyboard
from src.render import render_video
from src.beats import analyze_music
from src.timeline import align_scenes, normalize_durations
from src.classifier import classify_scenes, apply_scene_labels
from src.language import to_simplified

DEFAULT_MUSIC=Path(os.environ.get('KNOWLEDGE_MUSIC','用户本地配乐文件'))

def create_video_project(root, topic):
    topic=to_simplified(topic)
    project=create_project(root,topic)
    project['operation_started_at']=datetime.now().astimezone().isoformat(timespec='seconds')
    folder=project_dir(root,project['id'])
    try:
        project['status']='researching'; save_project(root,project)
        project['sources']=search_sources(topic)
        lines=['# 资料来源','']
        for s in project['sources']:
            lines.append(f"- {s['title']}：{s['url']}（访问日期：{s.get('accessed','未记录')}）")
        (folder/'sources.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        project['status']='writing'; save_project(root,project)
        project['storyboard']=generate_storyboard(topic,project['sources'])
        project['warnings']=project['storyboard'].get('normalization_warnings',[])
        project['status']='classifying'; save_project(root,project)
        scenes=project['storyboard']['scenes']
        project['layout_choices']=apply_scene_labels(scenes, classify_scenes(scenes))
        project['status']='rendering'; save_project(root,project)
        if not DEFAULT_MUSIC.is_file():
            raise FileNotFoundError('指定背景音乐不存在，请确认音乐文件路径')
        beats = analyze_music(DEFAULT_MUSIC)
        scenes = project['storyboard']['scenes']
        durations=normalize_durations([s['duration_seconds'] for s in scenes])
        boundaries = align_scenes(durations, beats)
        for index, scene in enumerate(scenes):
            scene['duration_seconds'] = boundaries[index+1] - boundaries[index]
        project['beat_count'] = len(beats)
        save_project(root,project)
        render_video(project['storyboard'],folder/'video.mp4',DEFAULT_MUSIC,beats=beats)
        project['status']='complete'
    except Exception as exc:
        project['status']='error'
        project['error']=str(exc) or '生成失败，请检查环境后重试'
    save_project(root,project)
    return project

def revise_video_project(root, project_id, instruction):
    instruction=to_simplified(instruction)
    project=load_project(root, project_id)
    folder=project_dir(root,project_id)
    if project['status'] != 'complete' or not instruction.strip():
        raise ValueError('请先选择已完成的作品并填写修改意见')
    old_storyboard=project['storyboard']
    try:
        project['status']='revising'; project['operation_started_at']=datetime.now().astimezone().isoformat(timespec='seconds'); project.pop('revision_error',None); save_project(root,project)
        revised=generate_storyboard(project['topic'],project['sources'],previous=old_storyboard,revision=instruction)
        project['warnings']=revised.get('normalization_warnings',[])
        layout_choices=apply_scene_labels(revised['scenes'],classify_scenes(revised['scenes']))
        beats=analyze_music(DEFAULT_MUSIC)
        scenes=revised['scenes']
        durations=normalize_durations([s['duration_seconds'] for s in scenes])
        boundaries=align_scenes(durations,beats)
        for index,scene in enumerate(scenes):
            scene['duration_seconds']=boundaries[index+1]-boundaries[index]
        candidate=folder / ('candidate-'+str(uuid.uuid4())+'.mp4')
        render_video(revised,candidate,DEFAULT_MUSIC,beats=beats)
        old_video=folder/'video.mp4'
        version=len(project.get('notes',[]))+1
        shutil.copy2(old_video,folder/f'video-before-edit-{version}.mp4')
        os.replace(candidate,old_video)
        project['storyboard']=revised
        project['layout_choices']=layout_choices
        project.setdefault('notes',[]).append(instruction)
    except Exception as exc:
        project['revision_error']=str(exc) or '修改失败，原视频已保留'
    project['status']='complete'
    save_project(root,project)
    return project
