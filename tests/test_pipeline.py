import tempfile
import unittest
from unittest.mock import patch
from src.pipeline import create_video_project
from src.projects import load_project

class PipelineTests(unittest.TestCase):
    def test_failure_is_saved_and_not_claimed_complete(self):
        with tempfile.TemporaryDirectory() as root:
            with patch('src.pipeline.search_sources',side_effect=RuntimeError('网络不可用')):
                project=create_video_project(root, '囚徒困境')
            self.assertEqual(project['status'],'error')
            self.assertIn('网络不可用',load_project(root,project['id'])['error'])

    def test_success_retains_sources_and_storyboard(self):
        with tempfile.TemporaryDirectory() as root:
            storyboard={'title':'主题','scenes':[{'text':'知识','visual_description':'解释','duration_seconds':3,'type':'concept','data':{}}]}
            sources=[{'title':'资料','url':'https://example.com','snippet':'来源'}]
            with patch('src.pipeline.search_sources',return_value=sources), patch('src.pipeline.generate_storyboard',return_value=storyboard), patch('src.pipeline.render_video',return_value='video.mp4'), patch('src.pipeline.analyze_music',return_value=[]), patch('src.pipeline.classify_scenes',return_value=['concept']):
                project=create_video_project(root,'主题')
            self.assertEqual(project['status'],'complete')
            self.assertEqual(project['sources'],sources)
            self.assertEqual(project['storyboard'],storyboard)
from unittest.mock import patch
from src.pipeline import revise_video_project
from src.projects import create_project, save_project, project_dir

class RevisionTests(unittest.TestCase):
    def test_failed_revision_preserves_previous_video(self):
        with tempfile.TemporaryDirectory() as root:
            project=create_project(root,'主题')
            project['status']='complete'
            project['sources']=[{'title':'资料','url':'https://example.com'}]
            project['storyboard']={'title':'旧','scenes':[]}
            save_project(root,project)
            video=project_dir(root,project['id'])/'video.mp4'
            video.write_bytes(b'old video')
            with patch('src.pipeline.generate_storyboard',side_effect=RuntimeError('模型不可用')):
                result=revise_video_project(root,project['id'],'缩短第二幕')
            self.assertEqual(video.read_bytes(),b'old video')
            self.assertEqual(result['status'],'complete')
            self.assertIn('模型不可用',result['revision_error'])
    def test_successful_revision_archives_original(self):
        with tempfile.TemporaryDirectory() as root:
            project=create_project(root,'主题'); project['status']='complete'
            project['sources']=[{'title':'资料','url':'https://example.com'}]
            project['storyboard']={'title':'旧','scenes':[{'text':'旧','visual_description':'说明','duration_seconds':4}]}
            save_project(root,project); folder=project_dir(root,project['id']); (folder/'video.mp4').write_bytes(b'old')
            revised={'title':'新','scenes':[{'text':'新','visual_description':'说明','duration_seconds':4}]}
            def fake_render(board,dest,music): dest.write_bytes(b'new')
            with patch('src.pipeline.generate_storyboard',return_value=revised), patch('src.pipeline.classify_scenes',return_value=['concept']), patch('src.pipeline.analyze_music',return_value=[]), patch('src.pipeline.render_video',side_effect=fake_render):
                result=revise_video_project(root,project['id'],'修改标题')
            self.assertEqual((folder/'video.mp4').read_bytes(),b'new')
            self.assertEqual((folder/'video-before-edit-1.mp4').read_bytes(),b'old')
            self.assertEqual(result['notes'],['修改标题'])
