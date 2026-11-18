"""Validate the project data before it reaches the renderer."""
import math

class StoryboardError(ValueError):
    pass

def validate_storyboard(value):
    # 在渲染前检查模型数据，防止缺标题、空分镜、异常时长或虚构矩阵格。
    # 先验顶层结构，再逐幕检查，出现问题时报告幕序号方便定位。
    if not isinstance(value, dict) or not isinstance(value.get('title'), str) or not value['title'].strip():
        raise StoryboardError('缺少视频标题')
    scenes = value.get('scenes')
    if not isinstance(scenes, list) or not scenes:
        raise StoryboardError('至少需要一个分镜')
    if len(scenes) > 12:
        raise StoryboardError('分镜数量不能超过12')
    # 每幕的文字和画面描述是渲染/分类所需的最小输入。
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            raise StoryboardError(f'第{index}幕格式错误')
        for field in ('text', 'visual_description'):
            if not isinstance(scene.get(field), str) or not scene[field].strip():
                raise StoryboardError(f'第{index}幕缺少 {field}')
        duration = scene.get('duration_seconds')
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 2 <= duration <= 30:
            raise StoryboardError(f'第{index}幕时长需在2到30秒之间')
        if scene.get('type', 'concept') not in ('concept', 'comparison', 'matrix', 'summary', 'flow'):
            raise StoryboardError(f'第{index}幕动画类型无效')
        # 矩阵有四格，缺值时拒绝渲染，避免程序或模型编造收益数字。
        if scene.get('type') == 'matrix':
            data = scene.get('data') or {}
            cells = data.get('cells') if isinstance(data, dict) else None
            if not isinstance(cells, list) or len(cells) != 4 or any(not isinstance(c, str) or not c.strip() for c in cells):
                raise StoryboardError(f'第{index}幕矩阵需要四个真实数据项')
    return value
