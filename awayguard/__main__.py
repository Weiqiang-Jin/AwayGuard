import os
import queue
import sys
import threading
import time
import math
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, ImageOps

from .storage import Store, local_time
from .monitor import run, IdleVisibility
from .sound import SoundPlayer, validate_wav


class App:
    def __init__(self, root, api):
        self.root, self.api = root, api
        self.path = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AwayGuard" / "events.sqlite3"
        self.store = Store(self.path)
        self.player = SoundPlayer(self.path.with_name("sound-settings.json"))
        self.worker = None
        self.stop_event = threading.Event()
        self.messages = queue.Queue()
        self.warning_window = None
        self.records_window = None
        self.table = None
        self.closing = False
        self.countdown_id = None
        self.ready = threading.Event()
        self.idle_visibility = IdleVisibility(timeout=10)
        root.title("AwayGuard")
        root.geometry("1160x820")
        root.minsize(940, 740)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f4f6")
        style.configure("TLabel", background="#f3f4f6", foreground="#20252d", font=("Microsoft YaHei UI", 10))
        style.configure("TButton", padding=(12, 8), font=("Microsoft YaHei UI", 10))
        style.configure("Accent.TButton", background="#bd303b", foreground="white")
        style.map("Accent.TButton", background=[("active", "#a92330"), ("disabled", "#e0b9bd")])
        root.protocol("WM_DELETE_WINDOW", self.close)
        main = ttk.Frame(root, padding=20)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="AwayGuard", font=("Microsoft YaHei UI", 21, "bold")).pack(anchor="w")
        ttk.Label(main, text="离开前开启守护，回来后查看记录。你的活动记录只保存在这台电脑上。").pack(anchor="w", pady=(4, 16))
        options = ttk.Frame(main)
        options.pack(fill="x")
        self.mode = tk.StringVar(value="双模式")
        self.select = ttk.Combobox(options, textvariable=self.mode, values=["桌面监控", "锁屏审计", "双模式"], state="readonly", width=16)
        self.select.pack(side="left")
        ttk.Label(options, text="  离开倒计时（秒） ").pack(side="left")
        self.grace = tk.StringVar(value="10")
        self.delay = ttk.Spinbox(options, from_=3, to=120, textvariable=self.grace, width=6)
        self.delay.pack(side="left")
        self.sound = tk.BooleanVar(value=self.player.enabled)
        ttk.Checkbutton(options, text="声音警告", variable=self.sound, command=self.toggle_sound).pack(side="left", padx=18)
        audio_options = ttk.Frame(main)
        audio_options.pack(fill="x", pady=(12, 0))
        ttk.Button(audio_options, text="选择自定义 WAV", command=self.choose_sound).pack(side="left")
        ttk.Button(audio_options, text="试听", command=self.preview_sound).pack(side="left", padx=8)
        ttk.Button(audio_options, text="停止播放", command=self.player.stop).pack(side="left")
        ttk.Button(audio_options, text="恢复默认警告音", command=self.reset_sound).pack(side="left", padx=8)
        self.sound_label = tk.StringVar(value=self.player.load_error or self.sound_description())
        ttk.Label(main, textvariable=self.sound_label, wraplength=980).pack(anchor="w", pady=(4, 0))
        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=16)
        self.start_button = ttk.Button(actions, text="我离开了 · 开始监控", command=self.start, style="Accent.TButton")
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(actions, text="我回来了 · 停止监控", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=10)
        ttk.Button(actions, text="立即锁屏（Win + L）", command=self.lock).pack(side="left")
        ttk.Button(actions, text="查看操作记录", command=self.show_records).pack(side="right")
        self.status = tk.StringVar(value="未监控")
        self.audit = tk.StringVar(value="登录与解锁记录：开始监控后检查是否可用")
        self.desktop = tk.StringVar(value="鼠标与键盘检测：未开始")
        for variable in (self.status, self.audit, self.desktop):
            ttk.Label(main, textvariable=variable, wraplength=980).pack(anchor="w", pady=2)
        ttk.Label(main, text="你回来操作时也会触发警告，点击“我回来了”即可停止。锁屏期间无法显示弹窗。", wraplength=980).pack(anchor="w", pady=(8, 12))
        hero = tk.Frame(main, bg="#17191d")
        hero.pack(fill="both", expand=True)
        caption = tk.Frame(hero, bg="#17191d", width=260)
        caption.pack(side="right", fill="y")
        caption.pack_propagate(False)
        tk.Label(caption, text="PRIVATE COMPUTER", fg="#e37b83", bg="#17191d", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=24, pady=(18, 10))
        tk.Label(caption, text="私人电脑\n请勿擅自操作", justify="left", fg="white", bg="#17191d", font=("Microsoft YaHei UI", 18, "bold")).pack(anchor="w", padx=24)
        self.hero_status = tk.StringVar(value="守护尚未开启")
        tk.Label(caption, textvariable=self.hero_status, wraplength=210, justify="left", fg="#f28d95", bg="#17191d", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w", padx=24, pady=(14, 8))
        tk.Label(caption, text="开启后，操作将触发警告。\n记录可通过上方按钮查看。", wraplength=210, justify="left", fg="#c2c5cc", bg="#17191d", font=("Microsoft YaHei UI", 10)).pack(anchor="w", padx=24)
        self.hero_canvas = tk.Canvas(hero, bg="#101114", highlightthickness=0)
        self.hero_canvas.pack(side="left", fill="both", expand=True)
        self.hero_image = None
        image_path = Path(__file__).with_name("assets") / "warning.jpg"
        if image_path.exists():
            with Image.open(image_path) as source:
                self.hero_image = source.convert("RGB")
        self.hero_canvas.bind("<Configure>", self.render_hero)
        self.status.trace_add("write", self.update_hero_status)
        ttk.Label(main, text="隐私保护：不记录具体按键、密码、聊天内容或截图。", foreground="#6b7280").pack(anchor="w", pady=(12, 0))
        root.after(200, self.drain)

    def update_hero_status(self, *_args):
        value = self.status.get()
        self.hero_status.set("守护尚未开启" if value == "未监控" else value)

    def render_hero(self, event):
        self.hero_canvas.delete("all")
        if self.hero_image is None:
            self.hero_canvas.create_text(event.width // 2, event.height // 2, text="私人电脑 · 请勿擅自操作", fill="white", font=("Microsoft YaHei UI", 20))
            return
        fitted = ImageOps.contain(self.hero_image, (max(1, event.width), max(1, event.height)), Image.Resampling.LANCZOS)
        self.hero_photo = ImageTk.PhotoImage(fitted)
        self.hero_canvas.create_image(event.width // 2, event.height // 2, image=self.hero_photo)

    def show_records(self):
        if self.records_window is not None and self.records_window.winfo_exists():
            self.records_window.deiconify()
            self.records_window.lift()
            return
        window = self.records_window = tk.Toplevel(self.root)
        window.title("AwayGuard · 操作记录")
        window.geometry("1060x560")
        window.minsize(720, 400)
        main = ttk.Frame(window, padding=20)
        main.pack(fill="both", expand=True)
        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x", pady=(0, 12))
        ttk.Label(toolbar, text="操作记录", font=("Microsoft YaHei UI", 18, "bold")).pack(side="left")
        ttk.Button(toolbar, text="导出全部 CSV", command=self.export).pack(side="right")
        ttk.Label(main, text="显示最近 500 条记录；双击一条记录可查看完整详情。关闭此窗口不会停止监控。").pack(anchor="w", pady=(0, 10))
        box = ttk.Frame(main)
        box.pack(fill="both", expand=True)
        self.table = ttk.Treeview(box, columns=("time", "kind", "details"), show="headings")
        for name, label, width in [("time", "本地时间", 200), ("kind", "事件", 140), ("details", "详情（双击展开）", 600)]:
            self.table.heading(name, text=label)
            self.table.column(name, width=width, minwidth=100)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.table.pack(fill="both", expand=True)
        self.table.bind("<Double-1>", self.detail)
        ttk.Label(main, text=f"显示最近 500 条；日志：{self.path}", wraplength=980).pack(anchor="w", pady=(10, 0))
        self.refresh()

    def refresh(self):
        if self.table is None or not self.table.winfo_exists():
            return
        self.table.delete(*self.table.get_children())
        for identifier, stamp, kind, details in self.store.recent():
            self.table.insert("", "end", iid=str(identifier), values=(local_time(stamp), kind, details))

    def sound_description(self):
        return "警告声音：" + (self.player.path or "默认警告音 · 03.wav")

    def save_sound(self, path):
        try:
            self.player.configure(self.sound.get(), path)
        except OSError as error:
            self.sound.set(self.player.enabled)
            messagebox.showerror("声音设置保存失败", str(error))
            return False
        self.player.stop()
        self.sound_label.set(self.sound_description())
        return True

    def toggle_sound(self):
        self.save_sound(self.player.path)

    def choose_sound(self):
        path = filedialog.askopenfilename(title="选择警告音频（PCM WAV）", filetypes=[("WAV 音频", "*.wav")])
        if path:
            try:
                path = validate_wav(path)
            except (OSError, ValueError) as error:
                messagebox.showerror("音频不可用", str(error))
                return
            self.save_sound(path)

    def reset_sound(self):
        self.save_sound("")

    def preview_sound(self):
        self.player.play(preview=True)
        self.sound_label.set(self.sound_description())

    def detail(self, _event):
        selection = self.table.selection()
        if selection:
            values = self.table.item(selection[0], "values")
            messagebox.showinfo(values[1], values[0] + "\n\n" + values[2])

    def start(self):
        if self.worker is not None:
            return
        try:
            grace = int(self.grace.get())
            if not 3 <= grace <= 120:
                raise ValueError()
        except ValueError:
            messagebox.showerror("倒计时无效", "请输入 3 至 120 之间的整数。")
            return
        self.stop_event = threading.Event()
        self.ready = threading.Event()
        self.idle_visibility.clear()
        self.messages = queue.Queue()
        self.store.add("开始监控", {"模式": self.mode.get(), "桌面宽限秒数": grace})
        self.audit.set("锁屏审计：连接中" if self.mode.get() != "桌面监控" else "锁屏审计：本模式未启用")
        self.desktop.set("桌面监控：等待倒计时" if self.mode.get() != "锁屏审计" else "桌面监控：本模式未启用")
        self.worker = threading.Thread(target=run, args=(self.mode.get(), grace, self.stop_event, self.messages, self.api, self.ready), daemon=True)
        self.worker.start()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.select.configure(state="disabled")
        self.delay.configure(state="disabled")
        self.countdown_deadline = time.monotonic() + grace
        self.countdown_tick()
        self.refresh()

    def countdown_tick(self):
        self.countdown_id = None
        if self.stop_event.is_set() or self.closing:
            return
        remaining = max(0, math.ceil(self.countdown_deadline - time.monotonic()))
        if remaining:
            self.status.set(f"{remaining} 秒后自动最小化并开始守护")
            self.countdown_id = self.root.after(100, self.countdown_tick)
            return
        self.minimize_monitoring()
        self.ready.set()
        self.status.set("监控中 · " + self.mode.get())

    def minimize_monitoring(self):
        self.idle_visibility.clear()
        self.player.stop()
        self.dismiss_warning()
        if self.records_window is not None and self.records_window.winfo_exists():
            self.records_window.withdraw()
        self.root.attributes("-topmost", False)
        self.root.iconify()

    def check_idle_visibility(self):
        if self.stop_event.is_set() or not self.ready.is_set() or self.idle_visibility.since is None:
            return
        # Read input directly on the UI timer so slow Security log queries do
        # not cause an active user to be mistaken for an idle one.
        try:
            tick = self.api.last_input()
        except OSError:
            return
        if self.idle_visibility.should_hide(time.monotonic(), tick):
            self.minimize_monitoring()

    def cancel_countdown(self):
        if self.countdown_id is not None:
            self.root.after_cancel(self.countdown_id)
            self.countdown_id = None

    def stop(self):
        self.cancel_countdown()
        self.idle_visibility.clear()
        if self.worker:
            self.stop_event.set()
            self.status.set("正在停止，等待事件查询完成…")
            self.stop_button.configure(state="disabled")
        self.dismiss_warning()
        self.player.stop()

    def drain(self):
        dirty = False
        try:
            while not self.player.errors.empty():
                error = self.player.errors.get_nowait()
                self.sound_label.set(error)
                self.store.add("声音播放异常", {"原因": error})
                dirty = True
            while True:
                item = self.messages.get_nowait()
                if item[0] == "event":
                    self.store.add(item[1], item[2], item[3])
                    dirty = True
                elif item[0] == "status" and not self.stop_event.is_set() and self.ready.is_set():
                    self.status.set(item[1])
                elif item[0] == "audit":
                    state = item[1]
                    if "无法读取 Security" in state:
                        state = "暂不可用，请以管理员身份运行；详细原因可在操作记录中查看"
                    elif "已连接" in state:
                        state = "已连接；还需开启 Windows 登录记录设置"
                    self.audit.set("登录与解锁记录：" + state)
                elif item[0] == "desktop":
                    self.desktop.set("鼠标与键盘检测：" + item[1].replace("桌面监控正常", "正常工作"))
                elif item[0] == "warning" and not self.stop_event.is_set():
                    self.warn()
                    dirty = True
        except queue.Empty:
            pass
        except Exception as error:
            self.stop_event.set()
            messagebox.showerror("日志写入失败，监控已停止", str(error))
            self.closing = True
        if self.worker and not self.worker.is_alive() and self.messages.empty():
            self.cancel_countdown()
            self.idle_visibility.clear()
            self.worker = None
            try:
                self.store.add("停止监控", {})
            except Exception:
                pass
            self.status.set("未监控")
            self.desktop.set("鼠标与键盘检测：已停止")
            self.audit.set("登录与解锁记录：已停止")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.select.configure(state="readonly")
            self.delay.configure(state="normal")
            dirty = True
        if self.closing and self.worker is None:
            self.store.close()
            self.root.destroy()
            return
        if dirty:
            self.refresh()
        self.check_idle_visibility()
        self.root.after(200, self.drain)

    def warn(self):
        if not self.api.desktop_available():
            self.store.add("警告跳过", {"原因": "当前桌面不可访问"})
            return
        self.idle_visibility.show(time.monotonic(), self.api.last_input())
        # Bring back the main warning image after away-mode minimization.
        if self.root.state() in ("iconic", "withdrawn"):
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(1000, lambda: self.root.attributes("-topmost", False))
        new_popup = self.warning_window is None or not self.warning_window.winfo_exists()
        if new_popup:
            popup = self.warning_window = tk.Toplevel(self.root)
            popup.title("AwayGuard · 操作警告")
            popup.geometry("530x220")
            popup.attributes("-topmost", True)
            ttk.Label(popup, text="此电脑正在监控", font=("Microsoft YaHei UI", 22, "bold")).pack(pady=(14, 8))
            ttk.Label(popup, text="已记录当前时间和应用活动。\n未经机主允许，请停止使用。", justify="center").pack()
            ttk.Button(popup, text="知道了（监控继续）", command=self.dismiss_warning).pack(pady=16)
            popup.protocol("WM_DELETE_WINDOW", self.dismiss_warning)
        started = self.player.play()
        if new_popup or started:
            self.store.add("发出操作警告", {"声音播放请求": started})

    def dismiss_warning(self):
        if self.warning_window is not None:
            self.warning_window.destroy()
            self.warning_window = None

    def lock(self):
        try:
            self.api.lock()
        except OSError as error:
            messagebox.showerror("锁屏失败", str(error))

    def export(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="awayguard-events.csv", filetypes=[("CSV", "*.csv")])
        if path:
            try:
                self.store.export(path)
                messagebox.showinfo("已导出", path)
            except OSError as error:
                messagebox.showerror("导出失败", str(error))

    def close(self):
        if self.worker and not messagebox.askyesno("退出 AwayGuard", "退出将停止监控。确定退出吗？"):
            return
        self.closing = True
        self.stop()


def main():
    if sys.platform != "win32":
        raise SystemExit("AwayGuard 仅支持 Windows 10/11。")
    from . import windows
    # Keep Tk dimensions and image rendering sharp on scaled Windows displays.
    windows.user32.SetProcessDPIAware()
    root = tk.Tk()
    try:
        mutex = windows.single_instance()
        App(root, windows)
    except Exception as error:
        messagebox.showerror("AwayGuard 无法启动", str(error))
        root.destroy()
        return 1
    try:
        root.mainloop()
    finally:
        windows.kernel32.CloseHandle(mutex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
