# resources_rc.py — manually generated for App Launcher
# Compatible with PyQt6 and Python 3.14
from PyQt6 import QtCore

# Register the embedded icon path
qt_resource_data = b""
qt_resource_name = b"\x0e\x00A\x00p\x00p\x00L\x00a\x00u\x00n\x00c\x00h\x00e\x00r\x00.\x00i\x00c\x00o"
qt_resource_struct = b"\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00"

def qInitResources():
    QtCore.qRegisterResourceData(0x03, qt_resource_struct, qt_resource_name, qt_resource_data)

def qCleanupResources():
    QtCore.qUnregisterResourceData(0x03, qt_resource_struct, qt_resource_name, qt_resource_data)

qInitResources()
