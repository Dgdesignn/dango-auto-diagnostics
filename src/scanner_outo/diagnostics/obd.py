from __future__ import annotations

import re
from dataclasses import dataclass


class ObdDecodeError(ValueError):
    """Resposta OBD incompleta, invalida ou diferente do pedido."""


class NoDataError(ObdDecodeError):
    """O adaptador terminou a consulta sem dados."""


class AdapterError(ObdDecodeError):
    """O adaptador devolveu um erro explicito."""


@dataclass(frozen=True)
class ObdFrame:
    ecu: str
    data: bytes


@dataclass(frozen=True)
class PidDefinition:
    pid: int
    name: str
    unit: str
    length: int


PIDS = {
    0x0C: PidDefinition(0x0C, "RPM", "rpm", 2),
    0x05: PidDefinition(0x05, "Temperatura do liquido de arrefecimento", "C", 1),
    0x0D: PidDefinition(0x0D, "Velocidade", "km/h", 1),
}

DTC_DESCRIPTIONS = {
    "P0100": "Circuito do sensor de massa/fluxo de ar",
    "P0115": "Circuito do sensor de temperatura do liquido de arrefecimento",
    "P0120": "Circuito do sensor de posicao da borboleta",
    "P0171": "Mistura demasiado pobre (banco 1)",
    "P0172": "Mistura demasiado rica (banco 1)",
    "P0300": "Falhas de combustao aleatorias ou multiplas",
    "P0301": "Falha de combustao no cilindro 1",
    "P0302": "Falha de combustao no cilindro 2",
    "P0420": "Eficiencia do catalisador abaixo do limiar (banco 1)",
    "P0562": "Tensao do sistema baixa",
}


def parse_frames(response: str, command: str = "") -> list[ObdFrame]:
    """Separa ECUs e normaliza CAN formatado pelo ELM; nao e ISO-TP bruto."""
    frames: list[ObdFrame] = []
    pending: dict[str, tuple[int, bytearray, int]] = {}
    for raw in response.upper().replace(">", "").replace("\r", "\n").splitlines():
        line = raw.strip()
        if not line or line.replace(" ", "") == command.upper().replace(" ", ""):
            continue
        if line in ("SEARCHING...", "BUS INIT: OK", "OK"):
            continue
        if "NO DATA" in line:
            raise NoDataError("Sem dados para este pedido.")
        if any(msg in line for msg in ("ERROR", "UNABLE TO CONNECT", "STOPPED", "BUS BUSY", "BUFFER FULL")) or line == "?":
            raise AdapterError("O adaptador recusou o pedido ou nao conseguiu comunicar com a ECU.")
        parts = line.split()
        ecu = "Nao identificada"
        can = False
        if len(parts) > 1 and len(parts[0]) in (3, 8) and re.fullmatch(r"[0-9A-F]+", parts[0]):
            ecu, can = parts.pop(0), True
        elif len(parts) >= 5 and parts[:2] in (["48", "6B"], ["48", "6C"]):
            ecu = parts[2]
            parts = parts[3:-1]
        compact = "".join(parts)
        if not compact or len(compact) % 2 or not re.fullmatch(r"[0-9A-F]+", compact):
            raise ObdDecodeError("Formato de resposta OBD nao reconhecido.")
        data = bytes.fromhex(compact)
        if can:
            kind = data[0] >> 4
            if kind == 0:
                length = data[0] & 15
                if not length or len(data) < length + 1:
                    raise ObdDecodeError("Mensagem CAN incompleta.")
                data = data[1:length + 1]
            elif kind == 1:
                if len(data) < 3 or ecu in pending:
                    raise ObdDecodeError("Inicio de mensagem CAN invalido.")
                length = ((data[0] & 15) << 8) + data[1]
                if length <= len(data) - 2 or length > 4095:
                    raise ObdDecodeError("Comprimento CAN invalido.")
                pending[ecu] = (length, bytearray(data[2:]), 1)
                continue
            elif kind == 2:
                if ecu not in pending:
                    raise ObdDecodeError("Fragmento CAN sem inicio.")
                length, payload, sequence = pending[ecu]
                if data[0] & 15 != sequence:
                    raise ObdDecodeError("Sequencia CAN invalida.")
                payload.extend(data[1:])
                if len(payload) < length:
                    pending[ecu] = (length, payload, (sequence + 1) % 16)
                    continue
                data = bytes(payload[:length])
                del pending[ecu]
            elif data[0] < 0x40:
                raise ObdDecodeError("Formato CAN nao suportado.")
        frames.append(ObdFrame(ecu, data))
    if pending:
        raise ObdDecodeError("Resposta CAN fragmentada incompleta.")
    if not frames:
        raise NoDataError("Nenhuma resposta OBD recebida.")
    return frames


def matching_payload(frame: ObdFrame, service: int, pid: int | None = None, freeze: bool = False) -> bytes:
    prefix = bytes([service + 0x40])
    if pid is not None:
        prefix += bytes([pid])
    if freeze:
        prefix += b"\x00"
    if not frame.data.startswith(prefix):
        raise ObdDecodeError("Servico, PID ou numero de freeze frame diferente do pedido.")
    return frame.data[len(prefix):]


def decode_pid(frame: ObdFrame, pid: int, service: int = 1) -> float:
    payload = matching_payload(frame, service, pid, freeze=service == 2)
    definition = PIDS[pid]
    if len(payload) != definition.length:
        raise ObdDecodeError(f"Comprimento invalido para {definition.name}.")
    if pid == 0x0C:
        return int.from_bytes(payload, "big") / 4
    if pid == 0x05:
        return float(payload[0] - 40)
    return float(payload[0])


def decode_rpm(response: str) -> float:
    frames = parse_frames(response, "010C")
    if len(frames) != 1:
        raise ObdDecodeError("Varias ECUs responderam; selecione uma ECU para obter RPM.")
    return decode_pid(frames[0], 0x0C)


def decode_supported(frame: ObdFrame, base: int = 0, service: int = 1) -> set[int]:
    payload = matching_payload(frame, service, base, freeze=service == 2)
    if len(payload) != 4:
        raise ObdDecodeError("Mapa de PIDs suportados incompleto.")
    mask = int.from_bytes(payload, "big")
    return {base + offset for offset in range(1, 33) if mask & (1 << (32 - offset))}


def decode_dtcs(frame: ObdFrame, service: int) -> list[str]:
    payload = matching_payload(frame, service)
    if len(payload) % 2:
        # Respostas CAN podem incluir o numero de DTCs antes dos pares.
        count = payload[0]
        if len(payload) < 1 + count * 2 or any(payload[1 + count * 2:]):
            raise ObdDecodeError("Lista de codigos de avaria incompleta.")
        payload = payload[1:1 + count * 2]
    codes = []
    for index in range(0, len(payload), 2):
        a, b = payload[index:index + 2]
        if a == b == 0:
            continue
        codes.append(f"{'PCBU'[a >> 6]}{(a >> 4) & 3}{a & 15:X}{b:02X}")
    return codes
