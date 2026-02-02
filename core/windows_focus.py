import sys

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    SW_RESTORE = 9

    def force_foreground(hwnd: int):
        if not hwnd:
            return

        # Restore if minimized
        user32.ShowWindow(hwnd, SW_RESTORE)

        foreground_hwnd = user32.GetForegroundWindow()
        if foreground_hwnd == hwnd:
            return

        current_thread = kernel32.GetCurrentThreadId()
        foreground_thread = user32.GetWindowThreadProcessId(
            foreground_hwnd, None
        )

        # Attach input threads (THIS IS THE KEY)
        user32.AttachThreadInput(
            foreground_thread, current_thread, True
        )

        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        user32.SetFocus(hwnd)

        # Detach threads
        user32.AttachThreadInput(
            foreground_thread, current_thread, False
        )
