import ctypes
import sys
from ctypes import wintypes as wt

# ---------------------------------------------------------------- setup
user32 = ctypes.WinDLL("user32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor DPI aware
except Exception:
    user32.SetProcessDPIAware()

MONITOR_DEFAULTTONEAREST = 2
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
DWMWA_CLOAKED = 14
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010

MIN_VISIBLE_W = 150   # px of width that must be reachable
TITLE_H = 40          # px of title bar that must be inside the work area


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("rcMonitor", wt.RECT),
        ("rcWork", wt.RECT),
        ("dwFlags", wt.DWORD),
    ]


EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

user32.EnumWindows.argtypes = [EnumProc, wt.LPARAM]
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsIconic.argtypes = [wt.HWND]
user32.IsZoomed.argtypes = [wt.HWND]
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.MonitorFromWindow.argtypes = [wt.HWND, wt.DWORD]
user32.MonitorFromWindow.restype = wt.HANDLE
user32.GetMonitorInfoW.argtypes = [wt.HANDLE, ctypes.POINTER(MONITORINFO)]
user32.SetWindowPos.argtypes = [
    wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, wt.UINT,
]
dwmapi.DwmGetWindowAttribute.argtypes = [
    wt.HWND, wt.DWORD, ctypes.c_void_p, wt.DWORD,
]


# ---------------------------------------------------------------- helpers
def window_title(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n == 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def is_cloaked(hwnd):
    cloaked = wt.DWORD(0)
    dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
    )
    return cloaked.value != 0  # hidden UWP / other-virtual-desktop windows


def candidate_windows():
    found = []

    @EnumProc
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.IsIconic(hwnd) or user32.IsZoomed(hwnd):
            return True  # minimized / maximized windows manage themselves
        if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
            return True
        if is_cloaked(hwnd):
            return True
        if not window_title(hwnd):
            return True
        found.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    return found


def work_area_for(hwnd):
    mon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(mon, ctypes.byref(mi))
    return mi.rcWork


def needs_rescue(r, work, fit_mode):
    if fit_mode:
        return (r.left < work.left or r.top < work.top
                or r.right > work.right or r.bottom > work.bottom)
    overlap_w = min(r.right, work.right) - max(r.left, work.left)
    title_ok = work.top <= r.top <= work.bottom - TITLE_H
    return overlap_w < MIN_VISIBLE_W or not title_ok


def target_rect(r, work):
    w = min(r.right - r.left, work.right - work.left)
    h = min(r.bottom - r.top, work.bottom - work.top)
    x = max(work.left, min(r.left, work.right - w))
    y = max(work.top, min(r.top, work.bottom - h))
    return x, y, w, h


# ---------------------------------------------------------------- main
def main():
    args = set(sys.argv[1:])
    fit_mode = "--fit" in args
    dry = "--dry-run" in args
    verbose = "--verbose" in args

    moved = 0
    for hwnd in candidate_windows():
        r = wt.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            continue
        work = work_area_for(hwnd)
        title = window_title(hwnd)

        if not needs_rescue(r, work, fit_mode):
            if verbose:
                print(f"ok      {title[:60]}")
            continue

        x, y, w, h = target_rect(r, work)
        print(f"{'would move' if dry else 'moving'}  {title[:60]}  "
              f"({r.left},{r.top}) -> ({x},{y}) size {w}x{h}")
        if not dry:
            ok = user32.SetWindowPos(
                hwnd, None, x, y, w, h, SWP_NOZORDER | SWP_NOACTIVATE
            )
            if not ok:
                print("   failed (elevated window? try running as Administrator)")
                continue
        moved += 1

    print(f"\n{moved} window(s) {'would be ' if dry else ''}rescued.")


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("This tool only runs on Windows.")
    main()
