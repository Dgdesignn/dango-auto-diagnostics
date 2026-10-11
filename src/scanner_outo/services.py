from __future__ import annotations

import threading
from dataclasses import asdict

from scanner_outo.communication.base import ElmTransport, TransportError
from scanner_outo.communication.tcp import TcpElmTransport
from scanner_outo.communication.serial_transport import SerialElmTransport
from scanner_outo.communication.bluetooth import BluetoothElmTransport
from scanner_outo.diagnostics.elm327 import Elm327Client
from scanner_outo.diagnostics.obd import (
    PIDS, DTC_DESCRIPTIONS, ObdDecodeError, NoDataError, parse_frames,
    decode_pid, decode_supported, decode_dtcs, matching_payload,
)
from scanner_outo.models import (
    ConnectionConfig, Session, Reading, TroubleCode, now_iso, NOT_QUERIED,
    QUERYING, EMPTY_CODES, UNAVAILABLE, QUERY_FAILED, COMPLETE, AVAILABLE, STALE,
)


class OperationCancelled(RuntimeError):
    pass


class DiagnosticService:
    """Uma unica fila de worker executa todas as operações desta sessão."""

    def __init__(self) -> None:
        self.transport: ElmTransport | None = None
        self.client: Elm327Client | None = None
        self.session = Session()
        self.cancel = threading.Event()

    def check_cancel(self) -> None:
        if self.cancel.is_set():
            raise OperationCancelled("Operação cancelada.")

    def connect(self, config: ConnectionConfig) -> dict:
        self.disconnect()
        self.session = Session(simulation=config.simulation, connection=asdict(config))
        if config.kind == "TCP":
            self.transport = TcpElmTransport(config.host, config.port, config.timeout)
        elif config.kind in ("Serial USB", "Bluetooth SPP"):
            if not config.serial_port:
                raise TransportError("Selecione uma porta COM.")
            cls = BluetoothElmTransport if config.kind == "Bluetooth SPP" else SerialElmTransport
            self.transport = cls(config.serial_port, config.baudrate, config.timeout)
        else:
            raise TransportError("Tipo de ligação não suportado; BLE não implementado.")
        try:
            self.transport.open()
            self.client = Elm327Client(self.transport)
            self.client.initialize()
            self.check_cancel()
            self.client.enable_headers()
            self.session.adapter_status = "Ligado"
            try:
                frames = self.query("0100")
                self.session.supported = {f.ecu: sorted(decode_supported(f)) for f in frames}
                self.session.ecu_status = "Comunicação confirmada"
            except ObdDecodeError as exc:
                self.session.ecu_status = f"Sem confirmação: {exc}"
            self._initial_readings()
            return self.session.to_dict()
        except Exception:
            self.disconnect()
            raise

    def _initial_readings(self) -> None:
        self.session.readings = []
        for ecu, supported in self.session.supported.items():
            for pid, definition in PIDS.items():
                self.session.readings.append(Reading(f"{pid:02X}", definition.name, definition.unit, ecu,
                    status=NOT_QUERIED if pid in supported else "Não suportado"))
        if not self.session.readings:
            self.session.readings = [Reading(f"{pid:02X}", d.name, d.unit, "Não identificada", status="Suporte não confirmado") for pid, d in PIDS.items()]

    def query(self, command: str):
        self.check_cancel()
        if self.client is None:
            raise TransportError("Ligue primeiro ao adaptador.")
        try:
            return parse_frames(self.client.send(command).response, command)
        except TransportError:
            self.disconnect()
            self.session.ecu_status = "Comunicação interrompida"
            raise

    def poll(self) -> dict:
        if not self.session.supported:
            try:
                frames = self.query("0100")
                self.session.supported = {f.ecu: sorted(decode_supported(f)) for f in frames}
                self._initial_readings()
            except ObdDecodeError as exc:
                self.session.ecu_status = f"Sem confirmação: {exc}"
                return self.session.to_dict()
        any_valid = False
        failures = False
        for pid in PIDS:
            targets = [r for r in self.session.readings if r.pid == f"{pid:02X}" and r.status != "Não suportado"]
            if not targets:
                continue
            try:
                frames = self.query(f"01{pid:02X}")
                seen = set()
                for frame in frames:
                    value = decode_pid(frame, pid)
                    reading = next((r for r in targets if r.ecu == frame.ecu), None)
                    if reading is None:
                        raise ObdDecodeError("Resposta de ECU não anunciada no mapa de suporte.")
                    reading.value, reading.timestamp = value, now_iso()
                    reading.status, reading.detail, reading.stale = AVAILABLE, "", False
                    seen.add(frame.ecu)
                    any_valid = True
                for reading in targets:
                    if reading.ecu not in seen:
                        reading.status, reading.detail = UNAVAILABLE, "Esta ECU não respondeu."
                        reading.stale = reading.value is not None
                        failures = True
            except ObdDecodeError as exc:
                failures = True
                for reading in targets:
                    reading.status = UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED
                    reading.detail = str(exc)
                    reading.stale = reading.value is not None
        self.session.ecu_status = "Comunicação parcial" if any_valid and failures else "Comunicação confirmada" if any_valid else "Sem leituras válidas"
        return self.session.to_dict()

    def read_codes(self) -> dict:
        codes = []
        queries = {kind: {"status": NOT_QUERIED} for kind in ("Confirmado", "Pendente")}
        self.session.codes = codes
        self.session.code_queries = queries
        for service, label in ((3, "Confirmado"), (7, "Pendente")):
            queries[label] = {"status": QUERYING}
            try:
                frames = self.query(f"{service:02X}")
                counts = {}
                for frame in frames:
                    decoded = decode_dtcs(frame, service)
                    counts[frame.ecu] = len(decoded)
                    codes.extend(TroubleCode(code, DTC_DESCRIPTIONS.get(code, "Descrição não disponível"), label, frame.ecu) for code in decoded)
                queries[label] = {"status": COMPLETE if any(counts.values()) else EMPTY_CODES, "success": True, "ecus": counts, "timestamp": now_iso()}
            except ObdDecodeError as exc:
                queries[label] = {"status": UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED, "success": False, "detail": str(exc), "timestamp": now_iso()}
            except TransportError:
                queries[label] = {"status": QUERY_FAILED, "success": False, "detail": "Ligação interrompida", "timestamp": now_iso()}
                raise
        self.session.codes, self.session.code_queries = codes, queries
        return self.session.to_dict()

    def read_freeze_frame(self) -> dict:
        self.session.freeze_frame = []
        self.session.freeze_codes = {}
        self.session.freeze_status = QUERYING
        self.session.freeze_detail = ""
        try:
            support = {f.ecu: decode_supported(f, service=2) for f in self.query("020000")}
            code_detail = ""
            try:
                for frame in self.query("020200"):
                    payload = matching_payload(frame, 2, 2, freeze=True)
                    if len(payload) != 2:
                        raise ObdDecodeError("Codigo de freeze frame incompleto.")
                    self.session.freeze_codes[frame.ecu] = decode_dtcs(type(frame)(frame.ecu, b"\x43" + payload), 3)
            except ObdDecodeError as exc:
                code_detail = f"; código associado indisponível: {exc}"
            for pid, definition in PIDS.items():
                targets = [ecu for ecu, pids in support.items() if pid in pids]
                if not targets:
                    continue
                try:
                    frames = self.query(f"02{pid:02X}00")
                    seen = set()
                    for frame in frames:
                        if frame.ecu not in targets:
                            raise ObdDecodeError("ECU freeze frame não anunciada.")
                        value = decode_pid(frame, pid, service=2)
                        self.session.freeze_frame.append(Reading(f"{pid:02X}", definition.name, definition.unit, frame.ecu, value, AVAILABLE, now_iso()))
                        seen.add(frame.ecu)
                    for ecu in set(targets) - seen:
                        self.session.freeze_frame.append(Reading(f"{pid:02X}", definition.name, definition.unit, ecu, status=UNAVAILABLE))
                except ObdDecodeError as exc:
                    for ecu in targets:
                        self.session.freeze_frame.append(Reading(f"{pid:02X}", definition.name, definition.unit, ecu, status=UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED, detail=str(exc)))
            self.session.freeze_status = COMPLETE
            self.session.freeze_detail = "Frame 0" + code_detail
        except ObdDecodeError as exc:
            self.session.freeze_status = UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED
            self.session.freeze_detail = str(exc)
        except TransportError:
            self.session.freeze_status = QUERY_FAILED
            self.session.freeze_detail = "Ligação interrompida"
            raise
        return self.session.to_dict()

    def clear_codes(self) -> dict:
        if not self.session.simulation:
            raise TransportError("Limpeza permitida apenas em simulação.")
        self.session.clear_status = "Limpeza solicitada; ainda não confirmada."
        try:
            frames = self.query("04")
        except (TransportError, ObdDecodeError):
            self.session.clear_status = "Limpeza não confirmada; pedido falhou ou sem suporte."
            raise
        if not frames or any(f.data != b"\x44" for f in frames):
            self.session.clear_status = "Limpeza não confirmada; resposta diferente de 44."
            raise ObdDecodeError("Limpeza não confirmada pelo adaptador.")
        acknowledged = {f.ecu for f in frames}
        self.session.clear_status = "Resposta 44 recebida; a verificar por releitura."
        self.session.freeze_frame = []
        self.session.freeze_codes = {}
        self.session.freeze_status = "Dados anteriores a limpeza invalidados; voltar a consultar"
        self.read_codes()
        queries = self.session.code_queries
        if all(queries.get(label, {}).get("success") is True and acknowledged <= set(queries[label].get("ecus", {})) for label in ("Confirmado", "Pendente")) and not self.session.codes:
            self.session.clear_status = "Informacao de diagnóstico limpa: resposta 44 e releitura confirmadas."
        else:
            self.session.clear_status = "Resposta 44 recebida; releitura inconclusiva ou códigos ainda presentes."
        return self.session.to_dict()

    def disconnect(self) -> dict:
        if self.transport:
            self.transport.close()
        self.transport = None
        self.client = None
        self.session.adapter_status = "Desligado"
        self.session.ecu_status = "Não ligada"
        for reading in self.session.readings:
            if reading.value is not None:
                reading.status = STALE
                reading.stale = True
        return self.session.to_dict()
