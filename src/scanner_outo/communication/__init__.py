"""Camada de comunicacao com adaptadores ELM327."""

from scanner_outo.communication.base import ElmTransport, TransportError
from scanner_outo.communication.tcp import TcpElmTransport

__all__ = ["ElmTransport", "TcpElmTransport", "TransportError"]

