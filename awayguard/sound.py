"""Local sound preferences and non-blocking WAV playback."""
import json
import wave
import queue
import threading
import time
from pathlib import Path

DEFAULT_SOUND = Path(__file__).with_name("assets") / "00.wav"


def validate_wav(path):
    path = Path(path)
    if path.suffix.lower() != ".wav":
        raise ValueError("请选择 PCM WAV 文件；暂不支持 MP3、M4A。")
    try:
        with wave.open(str(path), "rb") as audio:
            if audio.getnframes() == 0 or audio.getcomptype() != "NONE":
                raise ValueError("音频必须是非空的 PCM WAV 文件。")
    except (wave.Error, EOFError) as error:
        raise ValueError("无法读取此 WAV，请将音频导出为 PCM WAV 后重试。") from error
    return str(path.resolve())


class SoundPlayer:
    def __init__(self, settings_path):
        self.settings_path = Path(settings_path)
        self.enabled = True
        self.path = ""
        self.load_error = ""
        self._worker = None
        self._cancel = threading.Event()
        self.errors = queue.Queue()
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("enabled"), bool) or not isinstance(data.get("path"), str):
                raise ValueError("声音设置格式无效")
            self.enabled, self.path = data["enabled"], data["path"]
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as error:
            self.load_error = "无法加载声音设置，已使用默认警告音 00：" + str(error)

    def configure(self, enabled, path):
        # Commit preferences only after the new file was successfully written.
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.settings_path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"enabled": enabled, "path": path}, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.settings_path)
        self.enabled, self.path = enabled, path

    def play(self, preview=False):
        if not preview and not self.enabled:
            return False
        # Called only by the UI thread. A synchronous backend in a worker gives
        # an actual completion signal, including for Windows' default sound.
        if self.playing:
            return False
        self._cancel = threading.Event()
        self._worker = threading.Thread(target=self._play_once, args=(self.path or str(DEFAULT_SOUND), self._cancel), daemon=True)
        self._worker.start()
        return True

    @property
    def playing(self):
        return self._worker is not None and self._worker.is_alive()

    def _play_once(self, path, cancel):
        import winsound
        error_text = ""
        if path:
            try:
                validate_wav(path)
                if cancel.is_set():
                    return
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
                return
            except (OSError, ValueError, RuntimeError) as error:
                error_text = "自定义音频不可用，尝试系统提示音：" + str(error)
        if cancel.is_set():
            return
        try:
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        except RuntimeError as error:
            error_text += " 系统提示音播放失败：" + str(error)
        if error_text and not cancel.is_set():
            self.errors.put(error_text)

    def stop(self):
        import winsound
        self._cancel.set()
        # Reissue stop while joining to cover cancellation immediately before
        # the worker enters PlaySound. Never forget a still-running worker.
        deadline = time.monotonic() + 0.5
        while self.playing:
            try:
                winsound.PlaySound(None, 0)
            except RuntimeError:
                pass
            self._worker.join(0.01)
            if time.monotonic() >= deadline:
                break
