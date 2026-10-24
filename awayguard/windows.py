"""Small, explicitly typed Win32 API boundary; no keyboard hooks."""
import ctypes
import os
from ctypes import wintypes as w
from pathlib import PureWindowsPath

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", w.UINT), ("dwTime", w.DWORD)]


user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
user32.GetLastInputInfo.restype = w.BOOL
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = w.HWND
user32.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
user32.GetWindowThreadProcessId.restype = w.DWORD
user32.LockWorkStation.argtypes = []
user32.LockWorkStation.restype = w.BOOL
user32.OpenInputDesktop.argtypes = [w.DWORD, w.BOOL, w.DWORD]
user32.OpenInputDesktop.restype = w.HANDLE
user32.CloseDesktop.argtypes = [w.HANDLE]
user32.CloseDesktop.restype = w.BOOL
user32.GetUserObjectInformationW.argtypes = [w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD, ctypes.POINTER(w.DWORD)]
user32.GetUserObjectInformationW.restype = w.BOOL
kernel32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
kernel32.OpenProcess.restype = w.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = w.BOOL
kernel32.CloseHandle.argtypes = [w.HANDLE]
kernel32.CloseHandle.restype = w.BOOL
kernel32.CreateMutexW.argtypes = [w.LPVOID, w.BOOL, w.LPCWSTR]
kernel32.CreateMutexW.restype = w.HANDLE
kernel32.ProcessIdToSessionId.argtypes = [w.DWORD, ctypes.POINTER(w.DWORD)]
kernel32.ProcessIdToSessionId.restype = w.BOOL


def session_id():
    value = w.DWORD()
    if not kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    return value.value


def single_instance():
    handle = kernel32.CreateMutexW(None, False, "Local\\AwayGuard.UI.v1")
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        kernel32.CloseHandle(handle)
        raise RuntimeError("当前 Windows 会话已运行 AwayGuard。")
    return handle


def last_input():
    value = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
    if not user32.GetLastInputInfo(ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    return value.dwTime


def desktop_available():
    # UAC secure desktop and a locked workstation are intentionally both skipped.
    handle = user32.OpenInputDesktop(0, False, 1)
    if not handle:
        return False
    try:
        name = ctypes.create_unicode_buffer(256)
        needed = w.DWORD()
        return bool(user32.GetUserObjectInformationW(handle, 2, name, ctypes.sizeof(name), ctypes.byref(needed))) and name.value.lower() == "default"
    finally:
        user32.CloseDesktop(handle)


def foreground():
    hwnd = user32.GetForegroundWindow()
    pid = w.DWORD()
    if not hwnd:
        return None
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value or pid.value == os.getpid():
        return None
    handle = kernel32.OpenProcess(0x1000, False, pid.value)
    name = "无法读取进程名"
    if handle:
        try:
            length = w.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(length.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)):
                name = PureWindowsPath(buffer.value).name
        finally:
            kernel32.CloseHandle(handle)
    return {"process": name, "pid": pid.value, "window": int(hwnd)}


def lock():
    if not user32.LockWorkStation():
        raise ctypes.WinError(ctypes.get_last_error())
