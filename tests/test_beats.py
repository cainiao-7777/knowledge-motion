import unittest
from src.beats import detect_peaks

class BeatTests(unittest.TestCase):
    def test_finds_separated_strength_peaks(self):
        energies=[0,0,5,0,0,0,8,0,0]
        self.assertEqual(detect_peaks(energies,hop_seconds=0.5,min_spacing=1.0),[1.0,3.0])

    def test_silence_has_no_beats(self):
        self.assertEqual(detect_peaks([0]*10,hop_seconds=0.5),[])
