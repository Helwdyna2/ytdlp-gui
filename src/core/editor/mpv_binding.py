"""Low-level ctypes binding for the libmpv client and render APIs."""

from __future__ import annotations

import ctypes
import ctypes.util
import locale
import logging
from pathlib import Path
from typing import Iterable, Optional


MPV_FORMAT_NONE = 0
MPV_FORMAT_STRING = 1
MPV_FORMAT_OSD_STRING = 2
MPV_FORMAT_FLAG = 3
MPV_FORMAT_INT64 = 4
MPV_FORMAT_DOUBLE = 5

MPV_EVENT_NONE = 0
MPV_EVENT_FILE_LOADED = 8
MPV_EVENT_END_FILE = 7
MPV_EVENT_PROPERTY_CHANGE = 22

MPV_RENDER_PARAM_INVALID = 0
MPV_RENDER_PARAM_API_TYPE = 1
MPV_RENDER_PARAM_OPENGL_INIT_PARAMS = 2
MPV_RENDER_PARAM_OPENGL_FBO = 3
MPV_RENDER_PARAM_FLIP_Y = 4

MPV_RENDER_API_TYPE_OPENGL = b"opengl"
GL_RGBA8 = 0x8058

logger = logging.getLogger(__name__)
_MPV_LOCALE_CONFIGURED = False


class MpvBindingError(RuntimeError):
    """Raised when libmpv calls fail."""


def ensure_c_numeric_locale() -> bool:
    """Force a C numeric locale so libmpv can initialize reliably."""

    global _MPV_LOCALE_CONFIGURED

    if _MPV_LOCALE_CONFIGURED:
        return True

    current = locale.setlocale(locale.LC_NUMERIC, None)
    if current == "C":
        _MPV_LOCALE_CONFIGURED = True
        return True

    try:
        locale.setlocale(locale.LC_NUMERIC, "C")
    except locale.Error:
        logger.exception(
            "libmpv requires LC_NUMERIC='C', but the current locale %r could not be changed.",
            current,
        )
        return False

    logger.info(
        "Adjusted LC_NUMERIC from %r to 'C' for libmpv compatibility.",
        current,
    )
    _MPV_LOCALE_CONFIGURED = True
    return True


WakeupCallback = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
RenderUpdateCallback = ctypes.CFUNCTYPE(None, ctypes.c_void_p)
GetProcAddressCallback = ctypes.CFUNCTYPE(
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p
)


class MpvEvent(ctypes.Structure):
    _fields_ = [
        ("event_id", ctypes.c_int),
        ("error", ctypes.c_int),
        ("reply_userdata", ctypes.c_uint64),
        ("data", ctypes.c_void_p),
    ]


class MpvEventProperty(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char_p),
        ("format", ctypes.c_int),
        ("data", ctypes.c_void_p),
    ]


class MpvOpenGLInitParams(ctypes.Structure):
    _fields_ = [
        ("get_proc_address", GetProcAddressCallback),
        ("get_proc_address_ctx", ctypes.c_void_p),
        ("extra_exts", ctypes.c_char_p),
    ]


class MpvOpenGLFBO(ctypes.Structure):
    _fields_ = [
        ("fbo", ctypes.c_int),
        ("w", ctypes.c_int),
        ("h", ctypes.c_int),
        ("internal_format", ctypes.c_int),
    ]


class MpvRenderParam(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("data", ctypes.c_void_p),
    ]


def _find_mpv_library() -> Optional[str]:
    candidates = []

    discovered = ctypes.util.find_library("mpv")
    if discovered:
        candidates.append(discovered)

    candidates.extend(
        [
            "/opt/homebrew/lib/libmpv.dylib",
            "/usr/local/lib/libmpv.dylib",
            "/usr/lib/libmpv.dylib",
            "libmpv.so",
            "mpv-2.dll",
            "mpv-1.dll",
        ]
    )

    for candidate in candidates:
        try:
            if Path(candidate).exists() or not candidate.startswith("/"):
                return candidate
        except OSError:
            continue

    return None


class LibMpv:
    """Configured ctypes wrapper around the mpv shared library."""

    def __init__(self, library_path: Optional[str] = None):
        if not ensure_c_numeric_locale():
            raise MpvBindingError(
                "libmpv requires LC_NUMERIC='C' but the process locale could not be configured"
            )
        self.library_path = library_path or _find_mpv_library()
        if not self.library_path:
            raise MpvBindingError("libmpv could not be located on this system")

        self.lib = ctypes.CDLL(self.library_path)
        self._configure()

    def _configure(self) -> None:
        self.lib.mpv_create.restype = ctypes.c_void_p

        self.lib.mpv_initialize.argtypes = [ctypes.c_void_p]
        self.lib.mpv_initialize.restype = ctypes.c_int

        self.lib.mpv_terminate_destroy.argtypes = [ctypes.c_void_p]
        self.lib.mpv_terminate_destroy.restype = None

        self.lib.mpv_set_option_string.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
        ]
        self.lib.mpv_set_option_string.restype = ctypes.c_int

        self.lib.mpv_set_property.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_void_p,
        ]
        self.lib.mpv_set_property.restype = ctypes.c_int

        self.lib.mpv_get_property.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_void_p,
        ]
        self.lib.mpv_get_property.restype = ctypes.c_int

        self.lib.mpv_command.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)]
        self.lib.mpv_command.restype = ctypes.c_int

        self.lib.mpv_observe_property.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint64,
            ctypes.c_char_p,
            ctypes.c_int,
        ]
        self.lib.mpv_observe_property.restype = ctypes.c_int

        self.lib.mpv_set_wakeup_callback.argtypes = [
            ctypes.c_void_p,
            WakeupCallback,
            ctypes.c_void_p,
        ]
        self.lib.mpv_set_wakeup_callback.restype = None

        self.lib.mpv_wait_event.argtypes = [ctypes.c_void_p, ctypes.c_double]
        self.lib.mpv_wait_event.restype = ctypes.POINTER(MpvEvent)

        self.lib.mpv_error_string.argtypes = [ctypes.c_int]
        self.lib.mpv_error_string.restype = ctypes.c_char_p

        self.lib.mpv_render_context_create.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p,
            ctypes.POINTER(MpvRenderParam),
        ]
        self.lib.mpv_render_context_create.restype = ctypes.c_int

        self.lib.mpv_render_context_set_update_callback.argtypes = [
            ctypes.c_void_p,
            RenderUpdateCallback,
            ctypes.c_void_p,
        ]
        self.lib.mpv_render_context_set_update_callback.restype = None

        self.lib.mpv_render_context_render.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(MpvRenderParam),
        ]
        self.lib.mpv_render_context_render.restype = None

        self.lib.mpv_render_context_free.argtypes = [ctypes.c_void_p]
        self.lib.mpv_render_context_free.restype = None

    def check(self, status: int, context: str) -> None:
        if status >= 0:
            return
        error = self.lib.mpv_error_string(status)
        detail = error.decode("utf-8", "replace") if error else f"error {status}"
        raise MpvBindingError(f"{context}: {detail}")


class MpvClient:
    """Thin object-oriented wrapper around an mpv_handle."""

    def __init__(self, binding: LibMpv):
        self.binding = binding
        self.handle = self.binding.lib.mpv_create()
        if not self.handle:
            raise MpvBindingError("mpv_create() returned NULL")

    def initialize(self) -> None:
        self.binding.check(self.binding.lib.mpv_initialize(self.handle), "mpv_initialize")

    def terminate(self) -> None:
        if self.handle:
            self.binding.lib.mpv_terminate_destroy(self.handle)
            self.handle = None

    def set_option_string(self, name: str, value: str) -> None:
        self.binding.check(
            self.binding.lib.mpv_set_option_string(
                self.handle, name.encode("utf-8"), value.encode("utf-8")
            ),
            f"mpv_set_option_string({name})",
        )

    def set_property_flag(self, name: str, value: bool) -> None:
        flag = ctypes.c_int(1 if value else 0)
        self.binding.check(
            self.binding.lib.mpv_set_property(
                self.handle,
                name.encode("utf-8"),
                MPV_FORMAT_FLAG,
                ctypes.byref(flag),
            ),
            f"mpv_set_property({name})",
        )

    def get_property_flag(self, name: str) -> bool:
        flag = ctypes.c_int()
        self.binding.check(
            self.binding.lib.mpv_get_property(
                self.handle,
                name.encode("utf-8"),
                MPV_FORMAT_FLAG,
                ctypes.byref(flag),
            ),
            f"mpv_get_property({name})",
        )
        return bool(flag.value)

    def command(self, args: Iterable[str]) -> None:
        encoded = [arg.encode("utf-8") for arg in args]
        argv = (ctypes.c_char_p * (len(encoded) + 1))()
        for index, value in enumerate(encoded):
            argv[index] = value
        argv[len(encoded)] = None
        self.binding.check(self.binding.lib.mpv_command(self.handle, argv), "mpv_command")

    def observe_property(self, reply_userdata: int, name: str, fmt: int) -> None:
        self.binding.check(
            self.binding.lib.mpv_observe_property(
                self.handle, reply_userdata, name.encode("utf-8"), fmt
            ),
            f"mpv_observe_property({name})",
        )

    def set_wakeup_callback(self, callback: WakeupCallback) -> None:
        self.binding.lib.mpv_set_wakeup_callback(self.handle, callback, None)

    def wait_event(self) -> MpvEvent:
        event_ptr = self.binding.lib.mpv_wait_event(self.handle, 0.0)
        if not event_ptr:
            return MpvEvent()
        return event_ptr.contents


class MpvRenderContext:
    """Wrapper around mpv_render_context."""

    def __init__(self, binding: LibMpv, handle: ctypes.c_void_p):
        self.binding = binding
        self.handle = handle

    @classmethod
    def create(
        cls,
        binding: LibMpv,
        client: MpvClient,
        init_params: MpvOpenGLInitParams,
    ) -> "MpvRenderContext":
        render_handle = ctypes.c_void_p()
        api_type = ctypes.c_char_p(MPV_RENDER_API_TYPE_OPENGL)
        params = (MpvRenderParam * 3)()
        params[0] = MpvRenderParam(
            MPV_RENDER_PARAM_API_TYPE, ctypes.cast(api_type, ctypes.c_void_p)
        )
        params[1] = MpvRenderParam(
            MPV_RENDER_PARAM_OPENGL_INIT_PARAMS,
            ctypes.cast(ctypes.byref(init_params), ctypes.c_void_p),
        )
        params[2] = MpvRenderParam(MPV_RENDER_PARAM_INVALID, None)

        binding.check(
            binding.lib.mpv_render_context_create(
                ctypes.byref(render_handle), client.handle, params
            ),
            "mpv_render_context_create",
        )
        return cls(binding, render_handle)

    def set_update_callback(self, callback: RenderUpdateCallback) -> None:
        self.binding.lib.mpv_render_context_set_update_callback(
            self.handle, callback, None
        )

    def render(self, fbo: int, width: int, height: int, flip_y: bool = True) -> None:
        fbo_info = MpvOpenGLFBO(fbo=fbo, w=width, h=height, internal_format=GL_RGBA8)
        flip_flag = ctypes.c_int(1 if flip_y else 0)
        params = (MpvRenderParam * 3)()
        params[0] = MpvRenderParam(
            MPV_RENDER_PARAM_OPENGL_FBO,
            ctypes.cast(ctypes.byref(fbo_info), ctypes.c_void_p),
        )
        params[1] = MpvRenderParam(
            MPV_RENDER_PARAM_FLIP_Y,
            ctypes.cast(ctypes.byref(flip_flag), ctypes.c_void_p),
        )
        params[2] = MpvRenderParam(MPV_RENDER_PARAM_INVALID, None)
        self.binding.lib.mpv_render_context_render(self.handle, params)

    def free(self) -> None:
        if self.handle:
            self.binding.lib.mpv_render_context_free(self.handle)
            self.handle = None
