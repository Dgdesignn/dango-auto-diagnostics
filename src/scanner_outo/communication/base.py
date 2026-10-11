from __future__ import annotations

from abc import ABC, abstractmethod


class TransportError(RuntimeError):
    """Erro ao abrir, usar ou fechar um transporte ELM327."""


class ElmTransport(ABC):
    """Contrato comum para transportes ELM327.

    Implementacoes futuras de USB serial, Bluetooth e TCP para simuladores
    Android devem seguir esta interface para manter a camada de diagnostico
    independente do meio fisico.
    """

    @abstractmethod
    def open(self) -> None:
        """Abre a ligacao ao adaptador."""

    @abstractmethod
    def close(self) -> None:
        """Fecha a ligacao ao adaptador."""

    @abstractmethod
    def request(self, command: str) -> str:
        """Envia um comando ELM327/OBD-II e devolve a resposta bruta."""

    def __enter__(self) -> ElmTransport:
        self.open()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()


class TransportTimeout(TransportError):
    """Prazo de resposta excedido."""


class TransportDisconnected(TransportError):
    """Ligacao indisponivel ou interrompida."""

