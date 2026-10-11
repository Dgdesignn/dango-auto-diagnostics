from __future__ import annotations

import re
from dataclasses import dataclass
from collections.abc import Callable


class ObdDecodeError(ValueError):
    """Resposta OBD incompleta, inválida ou diferente do pedido."""


class NoDataError(ObdDecodeError):
    """O adaptador terminou a consulta sem dados."""


class AdapterError(ObdDecodeError):
    """O adaptador devolveu um erro explícito."""


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
    decoder: Callable[[bytes], float]


def percentage(data: bytes) -> float:
    return data[0] * 100 / 255


def temperature(data: bytes) -> float:
    return float(data[0] - 40)


def fuel_trim(data: bytes) -> float:
    return (data[0] - 128) * 100 / 128


def byte_value(data: bytes) -> float:
    return float(data[0])


def rpm(data: bytes) -> float:
    return int.from_bytes(data, "big") / 4


def timing(data: bytes) -> float:
    return data[0] / 2 - 64


def mass_air_flow(data: bytes) -> float:
    return int.from_bytes(data, "big") / 100


def module_voltage(data: bytes) -> float:
    return int.from_bytes(data, "big") / 1000


DEFAULT_PIDS = (0x0C, 0x05, 0x0D)


PIDS = {
    0x0C: PidDefinition(0x0C, "RPM", "rpm", 2, rpm),
    0x05: PidDefinition(0x05, "Temperatura do líquido de arrefecimento", "°C", 1, temperature),
    0x0D: PidDefinition(0x0D, "Velocidade", "km/h", 1, byte_value),
    0x04: PidDefinition(0x04, "Carga calculada do motor", "%", 1, percentage),
    0x06: PidDefinition(0x06, "Correcção curta de combustível (banco 1)", "%", 1, fuel_trim),
    0x07: PidDefinition(0x07, "Correcção longa de combustível (banco 1)", "%", 1, fuel_trim),
    0x0B: PidDefinition(0x0B, "Pressão absoluta no colector", "kPa", 1, byte_value),
    0x0E: PidDefinition(0x0E, "Avanço de ignição", "°", 1, timing),
    0x0F: PidDefinition(0x0F, "Temperatura do ar de admissão", "°C", 1, temperature),
    0x10: PidDefinition(0x10, "Caudal de massa de ar (MAF)", "g/s", 2, mass_air_flow),
    0x11: PidDefinition(0x11, "Posição da borboleta", "%", 1, percentage),
    0x42: PidDefinition(0x42, "Tensão do módulo de controlo", "V", 2, module_voltage),
}

DTC_DESCRIPTIONS = {
    "P0100": "Circuito do sensor de massa/fluxo de ar",
    "P0115": "Circuito do sensor de temperatura do líquido de arrefecimento",
    "P0120": "Circuito do sensor de posição da borboleta",
    "P0171": "Mistura demasiado pobre (banco 1)",
    "P0172": "Mistura demasiado rica (banco 1)",
    "P0300": "Falhas de combustão aleatórias ou múltiplas",
    "P0301": "Falha de combustão no cilindro 1",
    "P0302": "Falha de combustão no cilindro 2",
    "P0420": "Eficiência do catalisador abaixo do limiar (banco 1)",
    "P0562": "Tensão do sistema baixa",
}


def parse_frames(response: str, command: str = "") -> list[ObdFrame]:
    """Separa ECUs e normaliza CAN formatado pelo ELM; não e ISO-TP bruto."""
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
            raise AdapterError("O adaptador recusou o pedido ou não conseguiu comunicar com a ECU.")
        parts = line.split()
        ecu = "Não identificada"
        can = False
        if len(parts) > 1 and len(parts[0]) in (3, 8) and re.fullmatch(r"[0-9A-F]+", parts[0]):
            ecu, can = parts.pop(0), True
        elif len(parts) >= 5 and parts[:2] in (["48", "6B"], ["48", "6C"]):
            ecu = parts[2]
            parts = parts[3:-1]
        compact = "".join(parts)
        if not compact or len(compact) % 2 or not re.fullmatch(r"[0-9A-F]+", compact):
            raise ObdDecodeError("Formato de resposta OBD não reconhecido.")
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
                    raise ObdDecodeError("Inicio de mensagem CAN inválido.")
                length = ((data[0] & 15) << 8) + data[1]
                if length <= len(data) - 2 or length > 4095:
                    raise ObdDecodeError("Comprimento CAN inválido.")
                pending[ecu] = (length, bytearray(data[2:]), 1)
                continue
            elif kind == 2:
                if ecu not in pending:
                    raise ObdDecodeError("Fragmento CAN sem inicio.")
                length, payload, sequence = pending[ecu]
                if data[0] & 15 != sequence:
                    raise ObdDecodeError("Sequencia CAN inválida.")
                payload.extend(data[1:])
                if len(payload) < length:
                    pending[ecu] = (length, payload, (sequence + 1) % 16)
                    continue
                data = bytes(payload[:length])
                del pending[ecu]
            elif data[0] < 0x40:
                raise ObdDecodeError("Formato CAN não suportado.")
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
        raise ObdDecodeError(f"Comprimento inválido para {definition.name}.")
    return definition.decoder(payload)


def decode_monitor_status(frame: ObdFrame) -> dict:
    data = matching_payload(frame, 1, 1)
    if len(data) != 4:
        raise ObdDecodeError("Comprimento inválido para MIL e monitores.")
    a, b, c, d = data
    compression = bool(b & 8)
    monitors = []
    for bit, name in enumerate(("Falhas de combustão", "Sistema de combustível", "Componentes")):
        if b & (1 << bit):
            monitors.append({"name": name, "complete": not bool(b & (1 << (bit + 4)))})
    specific = (
        {0: "Catalisador NMHC", 1: "Pós-tratamento NOx/SCR", 3: "Pressão de sobrealimentação",
         5: "Sensor de gases de escape", 6: "Filtro de partículas", 7: "EGR/VVT"}
        if compression else
        {0: "Catalisador", 1: "Catalisador aquecido", 2: "Sistema evaporativo",
         3: "Ar secundário", 5: "Sonda de oxigénio", 6: "Aquecimento da sonda", 7: "EGR/VVT"}
    )
    for bit, name in specific.items():
        if c & (1 << bit):
            monitors.append({"name": name, "complete": not bool(d & (1 << bit))})
    return {"mil": bool(a & 128), "confirmed_count": a & 127,
            "engine_type": "Ignição por compressão" if compression else "Ignição por faísca",
            "monitors": monitors}


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
            raise ObdDecodeError("Lista de códigos de avaria incompleta.")
        payload = payload[1:1 + count * 2]
    codes = []
    for index in range(0, len(payload), 2):
        a, b = payload[index:index + 2]
        if a == b == 0:
            continue
        codes.append(f"{'PCBU'[a >> 6]}{(a >> 4) & 3}{a & 15:X}{b:02X}")
    return codes
