# Rescue_windows
bring off-screen windows back onto the monitor (Windows 10/11)

---
rescue_windows.py - bring off-screen windows back onto the monitor (Windows 10/11)

# Usage:
    python rescue_windows.py              # rescue windows that are off-screen / title bar unreachable
    python rescue_windows.py --fit        # also pull in windows that merely hang over an edge
    python rescue_windows.py --dry-run    # just list what would be moved
    python rescue_windows.py --verbose    # print every window considered

# Notes:
  * No third-party packages needed (pure ctypes).
  * Windows running as Administrator can't be moved unless this script is
    also run as Administrator.
  * Rename to .pyw (or use pythonw.exe) to run silently from a shortcut / hotkey.
---
