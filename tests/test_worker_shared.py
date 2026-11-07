import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.yougen_queue import Queue
from tools.yougen_worker import episode_name_matches


class SharedWorkerTests(unittest.TestCase):
    def test_episode_labels(self):
        for name in ("\u0421\u0435\u0440\u0438\u044f 2", "Episode 2", "S01E02"):
            self.assertTrue(episode_name_matches(name, 2))
        self.assertFalse(episode_name_matches("Episode 3", 2))
        self.assertFalse(episode_name_matches("The Show (2022)", 2))

    def test_crash_preserves_receipt_and_unblocks_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.sqlite"
            queue = Queue(path)
            from tools.yougen_bridge import VOICES
            payload = dict(query="Show", result_title="Show", title="Show",
                           voice=next(iter(VOICES)), quality="720p", season=1, episode=2)
            first = queue.enqueue(payload, identity="first")
            second = queue.enqueue(payload, identity="second")
            script = """
import os
import sys
from tools.yougen_queue import Queue
queue = Queue(sys.argv[1])
with queue.worker_lock():
    job = queue.claim()
    queue.update(job["id"], "waiting_receipt", details={"target_message_id": 42})
    print("locked", flush=True)
    sys.stdin.readline()
    os._exit(71)
"""
            with subprocess.Popen([sys.executable, "-c", script, str(path)],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                                  env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}) as child:
                try:
                    self.assertEqual(child.stdout.readline().strip(), "locked")
                    with self.assertRaises(RuntimeError), queue.worker_lock():
                        self.fail("concurrent lock acquired")
                    self.assertEqual(queue.get(first)["status"], "working")
                finally:
                    child.stdin.write("\n")
                    child.stdin.flush()
                    self.assertEqual(child.wait(timeout=10), 71)
            with queue.worker_lock():
                saved = queue.get(first)
                self.assertEqual(saved["status"], "needs_review")
                self.assertEqual(saved["phase"], "waiting_receipt")
                self.assertEqual(saved["details"], {"target_message_id": 42})
                self.assertEqual(queue.enqueue(payload, identity="first"), first)
                self.assertEqual(queue.claim()["id"], second)
