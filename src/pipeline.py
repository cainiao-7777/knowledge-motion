"""Connect research, script generation and rendering into one saved project."""
from pathlib import Path
from contextlib import nullcontext
import copy
import os
import shutil
import uuid
from datetime import datetime
from src.projects import create_project, save_project, project_dir, load_project
from src.research import search_sources, extract_search_query
from src.generator import generate_storyboard, plan_search_queries
from src.render import render_video
from src.beats import analyze_music
from src.timeline import align_scenes, normalize_durations
from src.classifier import classify_scenes, apply_scene_labels
from src.language import to_simplified
from src.cancellation import OperationCancelled, check_cancelled

# 可用 KNOWLEDGE_MUSIC 覆盖本地配乐路径；默认指向用户指定的歌曲。
DEFAULT_MUSIC=Path(os.environ.get('KNOWLEDGE_MUSIC',''))

def create_video_project(root, topic, cancel_event=None, operation_control=None, on_project_created=None):
    # 这是新作品的总流程：来源 → 大模型分镜 → 小模型布局 → 节奏 → 视频。
    topic=to_simplified(topic)
    project=create_project(root,topic)
    project['operation_started_at']=datetime.now().astimezone().isoformat(timespec='seconds')
    folder=project_dir(root,project['id'])
    if operation_control:
        operation_control.project_id=project['id']
    if on_project_created:
        on_project_created(project)
    try:
        check_cancelled(cancel_event)
        # 先让大模型从一句话中提炼主题和网页检索词。
        project['status']='planning_search'; save_project(root,project)
        try:
            project['search_plan']=plan_search_queries(topic)
            check_cancelled(cancel_event)
        except OperationCancelled:
            raise
        except Exception as exc:
            # 规划超时或格式错误时，用本地规则提词并记录回退原因。
            core,_=extract_search_query(topic)
            project['search_plan']={'main_topic':core,'queries':[core],'method':'fallback','reason':str(exc)}
        # 将规划词交给网页搜索，再保存实际来源。
        project['status']='researching'; save_project(root,project)
        plan=project['search_plan']
        project['sources']=search_sources(topic,plan.get('queries'),plan.get('main_topic'),cancel_event=cancel_event)
        check_cancelled(cancel_event)
        lines=['# 资料来源','']
        for s in project['sources']:
            lines.append(f"- {s['title']}：{s['url']}（访问日期：{s.get('accessed','未记录')}）")
        (folder/'sources.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        # 将实际搜索到的资料及链接单独落盘，再交给大模型组织讲述。
        project['status']='writing'; save_project(root,project)
        check_cancelled(cancel_event)
        project['storyboard']=generate_storyboard(topic,project['sources'])
        check_cancelled(cancel_event)
        project['warnings']=project['storyboard'].get('normalization_warnings',[])
        # 小模型逐幕分类；画面类型最终还会检查相应数据是否完整。
        project['status']='classifying'; save_project(root,project)
        check_cancelled(cancel_event)
        scenes=project['storyboard']['scenes']
        project['layout_choices']=apply_scene_labels(scenes, classify_scenes(scenes,cancel_event=cancel_event))
        check_cancelled(cancel_event)
        project['status']='rendering'; save_project(root,project)
        check_cancelled(cancel_event)
        if not DEFAULT_MUSIC.is_file():
            raise FileNotFoundError('指定背景音乐不存在，请确认音乐文件路径')
        # 用本地音乐估计拍点，再尽量让镜头边界靠近这些拍点。
        beats = analyze_music(DEFAULT_MUSIC,cancel_event=cancel_event)
        check_cancelled(cancel_event)
        scenes = project['storyboard']['scenes']
        durations=normalize_durations([s['duration_seconds'] for s in scenes])
        boundaries = align_scenes(durations, beats)
        for index, scene in enumerate(scenes):
            scene['duration_seconds'] = boundaries[index+1] - boundaries[index]
        project['beat_count'] = len(beats)
        save_project(root,project)
        # 先写临时渲染文件；只有视频与音轨合成成功才落到最终文件。
        render_video(project['storyboard'],folder/'video.mp4',DEFAULT_MUSIC,beats=beats,cancel_event=cancel_event)
        # 最后的取消检查与完成状态写入共享一把锁，避免刚完成又被计时器撤销。
        with operation_control.lock if operation_control else nullcontext():
            check_cancelled(cancel_event)
            project['status']='complete'
            save_project(root,project)
            if operation_control:
                operation_control.committed=True
    except OperationCancelled as exc:
        project['status']='cancelled'
        project['error']=str(exc)
        (folder/'video.mp4').unlink(missing_ok=True)
    except Exception as exc:
        project['status']='error'
        project['error']=str(exc) or '生成失败，请检查环境后重试'
    save_project(root,project)
    return project

def revise_video_project(root, project_id, instruction, cancel_event=None, operation_control=None):
    # 修改时保留旧故事板；新视频成功前不替换当前成片。
    instruction=to_simplified(instruction)
    project=load_project(root, project_id)
    folder=project_dir(root,project_id)
    if project['status'] != 'complete' or not instruction.strip():
        raise ValueError('请先选择已完成的作品并填写修改意见')
    original_project=copy.deepcopy(project)
    old_storyboard=project['storyboard']
    candidate=None
    backup=None
    try:
        check_cancelled(cancel_event)
        project['status']='revising'; project['operation_started_at']=datetime.now().astimezone().isoformat(timespec='seconds'); project.pop('revision_error',None); project.pop('revision_notice',None); save_project(root,project)
        check_cancelled(cancel_event)
        revised=generate_storyboard(project['topic'],project['sources'],previous=old_storyboard,revision=instruction)
        check_cancelled(cancel_event)
        project['warnings']=revised.get('normalization_warnings',[])
        layout_choices=apply_scene_labels(revised['scenes'],classify_scenes(revised['scenes'],cancel_event=cancel_event))
        check_cancelled(cancel_event)
        beats=analyze_music(DEFAULT_MUSIC,cancel_event=cancel_event)
        check_cancelled(cancel_event)
        scenes=revised['scenes']
        durations=normalize_durations([s['duration_seconds'] for s in scenes])
        boundaries=align_scenes(durations,beats)
        for index,scene in enumerate(scenes):
            scene['duration_seconds']=boundaries[index+1]-boundaries[index]
        candidate=folder / ('candidate-'+str(uuid.uuid4())+'.mp4')
        render_video(revised,candidate,DEFAULT_MUSIC,beats=beats,cancel_event=cancel_event)
        old_video=folder/'video.mp4'
        version=len(project.get('notes',[]))+1
        backup=folder/f'video-before-edit-{version}.mp4'
        # 修改提交与“暂停修改”互斥；成功保存后旧版本才算正式替换。
        with operation_control.lock if operation_control else nullcontext():
            check_cancelled(cancel_event)
            shutil.copy2(old_video,backup)
            try:
                check_cancelled(cancel_event)
                os.replace(candidate,old_video)
                project['storyboard']=revised
                project['layout_choices']=layout_choices
                project.setdefault('notes',[]).append(instruction)
                project['status']='complete'
                save_project(root,project)
                if operation_control:
                    operation_control.committed=True
            except Exception:
                if backup.is_file():
                    shutil.copy2(backup,old_video)
                    backup.unlink(missing_ok=True)
                raise
    except OperationCancelled as exc:
        project=original_project
        project['revision_notice']=str(exc)+'；原视频已保留'
        if candidate:
            candidate.unlink(missing_ok=True)
        if backup:
            backup.unlink(missing_ok=True)
    except Exception as exc:
        project=original_project
        project['revision_error']=str(exc) or '修改失败，原视频已保留'
        if candidate:
            candidate.unlink(missing_ok=True)
    project['status']='complete'
    save_project(root,project)
    return project
