import time
from .events import EventReader


class IdleVisibility:
    """Track inactivity only while an activity-triggered warning is visible."""
    def __init__(self, timeout=10):
        self.timeout = timeout
        self.clear()

    def clear(self):
        self.last_tick = None
        self.since = None

    def show(self, now, tick):
        self.last_tick = tick
        self.since = now

    def should_hide(self, now, tick):
        if self.since is None:
            return False
        if tick != self.last_tick:
            self.last_tick = tick
            self.since = now
        return now - self.since >= self.timeout


class ActivityTracker:
    """Deterministic activity decision logic, separately testable from Windows."""
    def __init__(self, baseline):
        self.last_input = baseline
        self.last_activity = float("-inf")
        self.last_summary = float("-inf")
        self.last_window = None

    def update(self, now, tick, foreground):
        events = []
        changed = tick != self.last_input
        self.last_input = tick
        if changed:
            self.last_activity = now
            if now - self.last_summary >= 10:
                events.append(("检测到输入活动", {"说明": "鼠标或键盘活动；不采集按键内容"}))
                self.last_summary = now
        if now - self.last_activity <= 15 and foreground:
            key = (foreground["pid"], foreground["window"])
            if key != self.last_window:
                events.append(("前台窗口变化", foreground))
                self.last_window = key
        # Every new activity is eligible; the player suppresses overlap only
        # while sound is actually playing, rather than using a fixed cooldown.
        return events, changed


def run(mode, grace, stop, output, api, ready=None):
    def emit(kind, details, stamp=None):
        output.put(("event", kind, details, stamp))

    reader = EventReader()
    health = None
    next_audit = 0.0
    start = time.monotonic()
    tracker = None
    desktop_health = None
    pending_unlock_warning = False
    active_announced = False
    output.put(("status", "准备中：离开倒计时 %s 秒" % grace))
    while not stop.is_set():
        now = time.monotonic()
        if mode in ("锁屏审计", "双模式") and now >= next_audit:
            try:
                items, status = reader.poll()
                for item in items:
                    emit(*item)
                    if item[1].get("event_id") == 4801 and item[1].get("SessionId") == str(api.session_id()):
                        pending_unlock_warning = True
                state = status
            except Exception as error:
                state = str(error)
            if state != health:
                health = state
                emit("审计状态", {"状态": state})
                output.put(("audit", state))
            next_audit = time.monotonic() + 5
        if (ready.is_set() if ready is not None else now - start >= grace):
            if not active_announced:
                output.put(("status", "监控中 · " + mode))
                active_announced = True
            if pending_unlock_warning and api.desktop_available():
                output.put(("warning",))
                pending_unlock_warning = False
            if mode in ("桌面监控", "双模式"):
                try:
                    if not api.desktop_available():
                        state = "桌面不可访问（锁屏、UAC 或其他会话）；等待恢复"
                    else:
                        tick = api.last_input()
                        if tracker is None:
                            tracker = ActivityTracker(tick)
                        events, warn = tracker.update(now, tick, api.foreground())
                        for kind, details in events:
                            emit(kind, details)
                        if warn:
                            output.put(("warning",))
                        state = "桌面监控正常"
                    if state != desktop_health:
                        desktop_health = state
                        output.put(("desktop", state))
                        emit("桌面状态", {"状态": state})
                except Exception as error:
                    state = "桌面监控异常：" + str(error)
                    if state != desktop_health:
                        desktop_health = state
                        emit("监控错误", {"错误": state})
                        output.put(("desktop", state))
            elif tracker is None:
                tracker = True
        stop.wait(0.5)
