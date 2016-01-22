"""
Service support for Kivy / P4A
"""

__all__ = ["Service"]

import os
if "ANDROID_ARGUMENT" in os.environ:
    from servicelib.android_service import Service
else:
    from servicelib.subprocess_service import Service
