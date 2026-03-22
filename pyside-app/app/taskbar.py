"""taskbar.py — Windows taskbar overlay badge via ITaskbarList3."""
from __future__ import annotations
import sys

_taskbar = None


def _get_taskbar():  # pragma: no cover
    global _taskbar
    if _taskbar is not None:
        return _taskbar
    if sys.platform != 'win32':
        return None
    try:
        import comtypes.client
        import comtypes.shell
        _taskbar = comtypes.client.CreateObject(
            '{56FDF344-FD6D-11d0-958A-006097C9A090}',
            interface=comtypes.shell.ITaskbarList3,
        )
        _taskbar.HrInit()
    except Exception:
        _taskbar = None
    return _taskbar


def update_badge(hwnd: int, count: int) -> None:
    """Update the taskbar overlay icon with a badge count.

    On non-Windows or if comtypes is not available, this is a no-op.
    """
    if sys.platform != 'win32':
        return
    try:
        _update_badge_win32(hwnd, count)
    except Exception:
        pass


def _update_badge_win32(hwnd: int, count: int) -> None:  # pragma: no cover
    """Internal: update badge on Windows using GDI."""
    import ctypes
    import ctypes.wintypes

    if count <= 0:
        _clear_overlay(hwnd)
        return

    # Draw badge using GDI
    size = 16
    hdc_screen = ctypes.windll.user32.GetDC(0)
    hdc = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
    ctypes.windll.user32.ReleaseDC(0, hdc_screen)

    bmi_header = (ctypes.c_uint32 * 10)(
        40, size, -(size), 1, 32, 0, size * size * 4, 0, 0, 0
    )
    bits = ctypes.c_void_p()
    hbm = ctypes.windll.gdi32.CreateDIBSection(
        hdc, ctypes.byref((ctypes.c_byte * 40).from_buffer_copy(bytes(bmi_header))),
        0, ctypes.byref(bits), None, 0
    )
    old_bm = ctypes.windll.gdi32.SelectObject(hdc, hbm)

    # Fill red circle
    brush = ctypes.windll.gdi32.CreateSolidBrush(0x0000CC)  # red in BGR
    pen = ctypes.windll.gdi32.CreatePen(0, 0, 0x0000CC)
    old_brush = ctypes.windll.gdi32.SelectObject(hdc, brush)
    old_pen = ctypes.windll.gdi32.SelectObject(hdc, pen)
    ctypes.windll.gdi32.Ellipse(hdc, 0, 0, size, size)

    ctypes.windll.gdi32.SelectObject(hdc, old_brush)
    ctypes.windll.gdi32.SelectObject(hdc, old_pen)
    ctypes.windll.gdi32.DeleteObject(brush)
    ctypes.windll.gdi32.DeleteObject(pen)

    # Draw text
    label = str(min(count, 99))
    ctypes.windll.gdi32.SetBkMode(hdc, 1)  # TRANSPARENT
    ctypes.windll.gdi32.SetTextColor(hdc, 0xFFFFFF)
    rect = (ctypes.c_int * 4)(0, 0, size, size)
    ctypes.windll.user32.DrawTextW(hdc, label, -1, rect, 0x0025)  # DT_CENTER|DT_VCENTER|DT_SINGLELINE

    ctypes.windll.gdi32.SelectObject(hdc, old_bm)
    hicon = ctypes.windll.user32.CreateIconIndirect(
        ctypes.byref((ctypes.c_byte * 20)(
            1,  # fIcon
            0, 0,  # xHotspot, yHotspot
            *([0] * 4),  # hbmMask placeholder
            *([0] * 4),  # hbmColor placeholder
        ))
    )

    try:
        tb = _get_taskbar()
        if tb:
            tb.SetOverlayIcon(hwnd, hicon, 'notifications')
    except Exception:
        pass

    ctypes.windll.user32.DestroyIcon(hicon)
    ctypes.windll.gdi32.DeleteObject(hbm)
    ctypes.windll.gdi32.DeleteDC(hdc)


def _clear_overlay(hwnd: int) -> None:  # pragma: no cover
    try:
        tb = _get_taskbar()
        if tb:
            tb.SetOverlayIcon(hwnd, None, '')
    except Exception:
        pass
