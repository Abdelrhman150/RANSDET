import tempfile
import unittest
from pathlib import Path
import numpy as np
from content_features import extract_all_features, analyze_windows, calculate_compression_ratio, MODEL_FEATURE_NAMES

class FeatureTests(unittest.TestCase):
    def test_unchanged_and_optional_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'a.txt'
            p.write_bytes('نص عربي سليم\n'.encode() * 1000)
            f = extract_all_features(p, p, 'txt')
            self.assertEqual(f['content_change_ratio'], 0)
            self.assertEqual(f['compression_ratio_delta'], 0)
            self.assertEqual(f['window_change_ratio_max'], 0)
            self.assertEqual(f['structure_broken'], 0)
            self.assertNotIn('entropy_before', f)
            self.assertTrue(set(MODEL_FEATURE_NAMES) <= f.keys())
            self.assertIn('chi_square_before', extract_all_features(p, p, 'txt', include_baseline=True))

    def test_localized_fixed_length_change(self):
        old = b'A' * 32768
        replacement = np.random.default_rng(42).integers(0, 256, 4096, dtype=np.uint8).tobytes()
        new = old[:12288] + replacement + old[16384:]
        f = analyze_windows(old, new)
        self.assertGreater(f['window_change_ratio_max'], .98)
        self.assertGreater(f['window_entropy_delta_max'], 7.8)
        self.assertEqual(len(old), len(new))

    def test_empty_growth_and_validation(self):
        self.assertEqual(analyze_windows(b'', b'')['window_count'], 0)
        self.assertEqual(analyze_windows(b'', b'abc')['window_change_ratio_max'], 1)
        self.assertEqual(analyze_windows(b'abc', b'')['window_change_ratio_max'], 1)
        self.assertEqual(analyze_windows(b'abc', b'abc')['window_count'], 1)
        with self.assertRaises(ValueError):
            analyze_windows(b'a', b'a', 4, 5)
        with self.assertRaises(FileNotFoundError):
            extract_all_features('missing-original', 'missing-current', 'txt')

    def test_compression(self):
        noise = np.random.default_rng(0).integers(0, 256, 32768, dtype=np.uint8).tobytes()
        self.assertLess(calculate_compression_ratio(b'A' * 32768), .01)
        self.assertGreater(calculate_compression_ratio(noise), .99)
        self.assertEqual(calculate_compression_ratio(b''), 0)

if __name__ == '__main__':
    unittest.main()
