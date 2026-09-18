import unittest
from pathlib import Path

from utils.config import REQUIRED_CHECKPOINTS, checkpoint_path


class ConfigTests(unittest.TestCase):
    def test_required_checkpoint_manifest_is_complete(self):
        self.assertEqual(len(REQUIRED_CHECKPOINTS), 9)
        self.assertEqual(len(set(REQUIRED_CHECKPOINTS)), 9)

    def test_checkpoint_paths_are_absolute(self):
        for checkpoint in REQUIRED_CHECKPOINTS:
            self.assertTrue(Path(checkpoint_path(checkpoint)).is_absolute())


if __name__ == "__main__":
    unittest.main()
