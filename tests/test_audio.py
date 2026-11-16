import tempfile
import unittest
import wave
from pathlib import Path
from src.audio import create_effects_track

class AudioTests(unittest.TestCase):
    def test_effects_track_duration_and_contains_sound(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'effects.wav'
            create_effects_track(path, 3.0, [1.0,2.0])
            with wave.open(str(path),'rb') as stream:
                self.assertEqual(stream.getframerate(),22050)
                self.assertEqual(stream.getnframes(),66150)
                self.assertNotEqual(set(stream.readframes(66150)),{0})
