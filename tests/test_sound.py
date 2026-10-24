import tempfile
import unittest
import wave
import threading
from pathlib import Path
from unittest.mock import Mock, patch

from awayguard.sound import SoundPlayer, validate_wav, DEFAULT_SOUND


class SoundTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.wav = self.root / "custom.wav"
        with wave.open(str(self.wav), "wb") as audio:
            audio.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\0\0" * 80)
        self.player = SoundPlayer(self.root / "settings.json")

    def test_valid_wav_and_persisted_preferences(self):
        path = validate_wav(self.wav)
        self.player.configure(False, path)
        loaded = SoundPlayer(self.player.settings_path)
        self.assertFalse(loaded.enabled)
        self.assertEqual(loaded.path, path)

    def test_default_and_reset_use_bundled_00(self):
        validate_wav(DEFAULT_SOUND)
        sound = Mock(SND_FILENAME=1, SND_NODEFAULT=4, SND_ALIAS=8)
        with patch.dict("sys.modules", {"winsound": sound}):
            self.player.play()
            self.player._worker.join(2)
            self.assertEqual(sound.PlaySound.call_args.args, (str(DEFAULT_SOUND), 5))
            self.player.configure(True, str(self.wav))
            self.player.configure(True, "")
            self.player.play()
            self.player._worker.join(2)
            self.assertEqual(sound.PlaySound.call_args.args, (str(DEFAULT_SOUND), 5))

    def test_invalid_file_and_corrupt_settings(self):
        with self.assertRaises(ValueError):
            validate_wav(self.root / "song.mp3")
        self.wav.write_bytes(b"invalid")
        with self.assertRaises(ValueError):
            validate_wav(self.wav)
        self.player.settings_path.write_text("[]", encoding="utf-8")
        loaded = SoundPlayer(self.player.settings_path)
        self.assertTrue(loaded.enabled)
        self.assertTrue(loaded.load_error)

    def test_missing_file_falls_back(self):
        self.player.configure(True, str(self.wav))
        self.wav.unlink()
        sound = Mock(SND_FILENAME=1, SND_ASYNC=2, SND_NODEFAULT=4, SND_ALIAS=8)
        with patch.dict("sys.modules", {"winsound": sound}):
            self.assertTrue(self.player.play())
            self.player._worker.join(2)
            self.assertFalse(self.player.errors.empty())
        self.assertEqual(sound.PlaySound.call_args.args[0], "SystemExclamation")

    def test_disabled_sound_and_explicit_preview(self):
        self.player.configure(False, str(self.wav))
        sound = Mock(SND_FILENAME=1, SND_ASYNC=2, SND_NODEFAULT=4, SND_ALIAS=8)
        with patch.dict("sys.modules", {"winsound": sound}):
            self.player.play()
            sound.PlaySound.assert_not_called()
            self.assertTrue(self.player.play(preview=True))
            self.player._worker.join(2)
        self.assertEqual(sound.PlaySound.call_args.args, (str(self.wav), 5))

    def test_device_failure_is_reported_without_raising(self):
        self.player.configure(True, str(self.wav))
        sound = Mock(SND_FILENAME=1, SND_ASYNC=2, SND_NODEFAULT=4, SND_ALIAS=8)
        sound.PlaySound.side_effect = RuntimeError("audio unavailable")
        with patch.dict("sys.modules", {"winsound": sound}):
            self.assertTrue(self.player.play())
            self.player._worker.join(2)
            self.assertFalse(self.player.errors.empty())
        self.assertEqual(sound.PlaySound.call_count, 2)

    def test_activity_during_playback_is_not_queued_and_new_activity_replays(self):
        self.player.configure(True, str(self.wav))
        entered, finish = threading.Event(), threading.Event()
        sound = Mock(SND_FILENAME=1, SND_NODEFAULT=4, SND_ALIAS=8)
        def playback(*args):
            entered.set()
            finish.wait(2)
        sound.PlaySound.side_effect = playback
        with patch.dict("sys.modules", {"winsound": sound}):
            self.assertTrue(self.player.play())
            self.assertTrue(entered.wait(1))
            for _ in range(10):
                self.assertFalse(self.player.play())
            self.assertEqual(sound.PlaySound.call_count, 1)
            finish.set()
            self.player._worker.join(2)
            self.assertFalse(self.player.playing)
            self.assertEqual(sound.PlaySound.call_count, 1)
            self.assertTrue(self.player.play())
            self.player._worker.join(2)
            self.assertEqual(sound.PlaySound.call_count, 2)

    def test_stop_ends_playback_and_allows_next_activity(self):
        entered, finish = threading.Event(), threading.Event()
        sound = Mock(SND_FILENAME=1, SND_NODEFAULT=4, SND_ALIAS=8)
        def playback(name, flags):
            if name is None:
                finish.set()
            else:
                entered.set()
                finish.wait(2)
        sound.PlaySound.side_effect = playback
        with patch.dict("sys.modules", {"winsound": sound}):
            self.player.play()
            self.assertTrue(entered.wait(1))
            self.player.stop()
            self.assertFalse(self.player.playing)
            self.assertTrue(self.player.play())
            self.player._worker.join(2)

    def test_save_failure_preserves_active_configuration(self):
        with patch.object(Path, "replace", side_effect=OSError("read only")):
            with self.assertRaises(OSError):
                self.player.configure(False, str(self.wav))
        self.assertTrue(self.player.enabled)
        self.assertEqual(self.player.path, "")
