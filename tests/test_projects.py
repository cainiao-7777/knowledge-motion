import tempfile
import unittest
from pathlib import Path
from src.projects import create_project, load_project, save_project, ProjectError

class ProjectTests(unittest.TestCase):
    def test_save_and_reload_project(self):
        with tempfile.TemporaryDirectory() as root:
            project=create_project(root, '囚徒困境')
            project['notes']=['修改标题']
            save_project(root, project)
            self.assertEqual(load_project(root, project['id'])['notes'], ['修改标题'])

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ProjectError): load_project(root, '../secret')

if __name__=='__main__': unittest.main()
