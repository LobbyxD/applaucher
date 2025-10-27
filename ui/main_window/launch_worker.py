# ui/main_window/launch_worker.py
import asyncio
from PyQt6.QtCore import QObject, pyqtSignal
from core.launcher_logic import run_launch_sequence


class LaunchWorker(QObject):
    """Worker that runs the async launch sequence in its own QThread."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)

    def __init__(self, apps, launch_name: str):
        super().__init__()
        self.apps = apps
        self.launch_name = launch_name

    def run(self):
        """Run the async launch sequence in a separate event loop."""
        def _emit(text: str, **_):
            self.progress.emit(text)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_launch_sequence(self.apps, progress_cb=_emit))
        except Exception as e:
            self.finished.emit(f"❌ Error: {e}")
            return
        finally:
            try:
                loop.close()
            except Exception:
                pass

        self.finished.emit(f"{self.launch_name} Launched.")
