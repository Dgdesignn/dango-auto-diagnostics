"""Camada de diagnostico OBD-II."""

from scanner_outo.diagnostics.elm327 import Elm327Client
from scanner_outo.diagnostics.obd import decode_rpm

__all__ = ["Elm327Client", "decode_rpm"]

