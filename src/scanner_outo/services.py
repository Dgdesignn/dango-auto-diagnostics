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
    decode_pid, decode_supported, decode_dtcs, matching_payload, DEFAULT_PIDS, decode_monitor_status,
)
from scanner_outo.models import (
    ConnectionConfig, Session, Reading, TroubleCode, now_iso, NOT_QUERIED,
    QUERYING, EMPTY_CODES, UNAVAILABLE, QUERY_FAILED, COMPLETE, AVAILABLE, STALE,
    PARTIAL, NO_USABLE_DATA, SUPPORT_UNKNOWN, UNSUPPORTED,
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
                self.session.supported = self.discover_support()
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
                status, detail = self.support_state(ecu, pid)
                self.session.readings.append(Reading(f"{pid:02X}", definition.name, definition.unit, ecu,
                    status=status, detail=detail))
        if not self.session.readings:
            self.session.readings = [Reading(f"{pid:02X}", d.name, d.unit, "Não identificada", status=SUPPORT_UNKNOWN,
                                            detail="Mapa 0100 não recebido; ECU não identificada.") for pid, d in PIDS.items()]

    def support_state(self, ecu: str, pid: int, service: int = 1) -> tuple[str, str]:
        required = ((pid - 1) // 32) * 32
        suffix = "00" if service == 2 else ""
        for base in range(0, required + 1, 32):
            command = f"{service:02X}{base:02X}{suffix}"
            query = self.session.support_queries.get(f"{service:02X}/{ecu}/{base:02X}", {})
            if query.get("status") != COMPLETE:
                return SUPPORT_UNKNOWN, f"Mapa {command} não confirmado: " + query.get("detail", "não recebido.")
            pids = query["pids"]
            if base == required:
                return (NOT_QUERIED, "") if pid in pids else (UNSUPPORTED, f"PID não anunciado no mapa {command} desta ECU.")
            if base + 32 not in pids:
                return UNSUPPORTED, f"Mapa {command} recebido sem continuação; PID posterior não suportado."
        return SUPPORT_UNKNOWN, "Mapa necessário não recebido."

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

    def targeted_query(self, command: str, targets: list[str], all_ecus) -> list:
        if set(targets) == set(all_ecus):
            return self.query(command)
        frames = []
        for ecu in targets:
            # Physical addressing is only inferred for standard ISO 15765 CAN IDs.
            if len(ecu) == 3 and 0x7E8 <= int(ecu, 16) <= 0x7EF:
                header, functional = f"{int(ecu, 16) - 8:03X}", "7DF"
            elif len(ecu) == 8 and ecu.startswith("18DAF1"):
                header, functional = f"18DA{ecu[-2:]}F1", "18DB33F1"
            else:
                raise ObdDecodeError("Endereçamento individual desta ECU não suportado; pedido não enviado.")
            self.check_cancel()
            try:
                if "OK" not in self.client.send("ATSH" + header).response.upper():
                    raise ObdDecodeError("Adaptador recusou endereçamento individual; pedido não enviado.")
                frames.extend(f for f in self.query(command) if f.ecu == ecu)
            finally:
                if self.client is not None:
                    if "OK" not in self.client.send("ATSH" + functional).response.upper():
                        self.disconnect()
                        raise TransportError("Não foi possível restaurar o endereçamento funcional.")
        if not frames:
            raise NoDataError("A ECU seleccionada não respondeu.")
        return frames

    def discover_support(self, service: int = 1) -> dict[str, list[int]]:
        suffix = "00" if service == 2 else ""
        prefix = f"{service:02X}/"
        self.session.support_queries = {key: value for key, value in self.session.support_queries.items() if not key.startswith(prefix)}
        supported = {}
        for frame in self.query(f"{service:02X}00{suffix}"):
            supported[frame.ecu] = set()
            key = f"{service:02X}/{frame.ecu}/00"
            try:
                pids = decode_supported(frame, service=service)
                supported[frame.ecu].update(pids)
                self.session.support_queries[key] = {"status": COMPLETE, "pids": sorted(pids)}
            except ObdDecodeError as exc:
                self.session.support_queries[key] = {"status": QUERY_FAILED, "detail": str(exc)}
        for base in (0x20, 0x40):
            targets = [ecu for ecu, pids in supported.items() if base in pids]
            groups = [targets] if targets and set(targets) == set(supported) else [[ecu] for ecu in targets]
            for group in groups:
                try:
                    frames = self.targeted_query(f"{service:02X}{base:02X}{suffix}", group, supported)
                except ObdDecodeError as exc:
                    for ecu in group:
                        self.session.support_queries[f"{service:02X}/{ecu}/{base:02X}"] = {"status": UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED, "detail": str(exc)}
                    continue
                for ecu in group:
                    try:
                        frame = next((f for f in frames if f.ecu == ecu), None)
                        if frame is None:
                            raise NoDataError("Esta ECU não respondeu ao mapa de suporte.")
                        pids = decode_supported(frame, base, service)
                        supported[ecu].update(pids)
                        self.session.support_queries[f"{service:02X}/{ecu}/{base:02X}"] = {"status": COMPLETE, "pids": sorted(pids)}
                    except ObdDecodeError as exc:
                        self.session.support_queries[f"{service:02X}/{ecu}/{base:02X}"] = {"status": UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED, "detail": str(exc)}
        return {ecu: sorted(pids) for ecu, pids in supported.items()}

    def poll(self, selected_pids=None) -> dict:
        if not self.session.supported:
            try:
                self.session.supported = self.discover_support()
                self._initial_readings()
            except ObdDecodeError as exc:
                self.session.ecu_status = f"Sem confirmação: {exc}"
                return self.session.to_dict()
        any_valid = False
        failures = False
        for pid in PIDS:
            if pid not in (DEFAULT_PIDS if selected_pids is None else selected_pids):
                continue
            targets = [r for r in self.session.readings if r.pid == f"{pid:02X}"
                       and pid in self.session.supported.get(r.ecu, [])]
            if not targets:
                continue
            for reading in targets:
                reading.attempted_at = now_iso()
            groups = [targets] if {r.ecu for r in targets} == set(self.session.supported) else [[r] for r in targets]
            for group in groups:
                try:
                    frames = self.targeted_query(f"01{pid:02X}", [r.ecu for r in group], self.session.supported)
                except ObdDecodeError as exc:
                    failures = True
                    for reading in group:
                        reading.status = UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED
                        reading.detail = str(exc)
                        reading.stale = reading.value is not None
                    continue
                for reading in group:
                    try:
                        frame = next((f for f in frames if f.ecu == reading.ecu), None)
                        if frame is None:
                            raise NoDataError("Esta ECU não respondeu.")
                        value = decode_pid(frame, pid)
                        reading.value, reading.timestamp = value, now_iso()
                        reading.attempted_at = reading.timestamp
                        reading.status, reading.detail, reading.stale = AVAILABLE, "", False
                        any_valid = True
                    except ObdDecodeError as exc:
                        reading.status = UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED
                        reading.detail = str(exc)
                        reading.stale = reading.value is not None
                        failures = True
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
        self.read_monitor_status()
        return self.session.to_dict()

    def read_monitor_status(self) -> dict:
        self.session.monitor_status = {ecu: {"status": UNAVAILABLE, "detail": "PID 01 não anunciado pela ECU.", "timestamp": now_iso()}
                                       for ecu, pids in self.session.supported.items() if 1 not in pids}
        self.session.monitor_query = {"status": QUERYING}
        targets = [ecu for ecu, pids in self.session.supported.items() if 1 in pids]
        if not targets:
            self.session.monitor_query = {"status": UNAVAILABLE, "detail": "PID 01 não anunciado pela ECU.", "timestamp": now_iso()}
            return self.session.to_dict()
        try:
            for frame in self.targeted_query("0101", targets, self.session.supported):
                if frame.ecu not in targets:
                    continue
                try:
                    self.session.monitor_status[frame.ecu] = {**decode_monitor_status(frame), "status": COMPLETE, "timestamp": now_iso()}
                except ObdDecodeError as exc:
                    self.session.monitor_status[frame.ecu] = {"status": QUERY_FAILED, "detail": str(exc), "timestamp": now_iso()}
            for ecu in targets:
                self.session.monitor_status.setdefault(ecu, {"status": UNAVAILABLE, "detail": "Esta ECU não respondeu.", "timestamp": now_iso()})
            self.session.monitor_query = {"status": COMPLETE if all(self.session.monitor_status[ecu]["status"] == COMPLETE for ecu in targets) else QUERY_FAILED, "timestamp": now_iso()}
        except ObdDecodeError as exc:
            self.session.monitor_query = {"status": UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED, "detail": str(exc), "timestamp": now_iso()}
            for ecu in targets:
                self.session.monitor_status[ecu] = dict(self.session.monitor_query)
        except TransportError:
            self.session.monitor_query = {"status": QUERY_FAILED, "detail": "Ligação interrompida", "timestamp": now_iso()}
            raise
        return self.session.to_dict()

    def read_freeze_frame(self) -> dict:
        self.session.freeze_frame = []
        self.session.freeze_codes = {}
        self.session.freeze_ecus = {}
        self.session.freeze_status = QUERYING
        self.session.freeze_detail = ""
        try:
            support = self.discover_support(service=2)
            for ecu in support:
                self.session.freeze_ecus[ecu] = {"code_query": {"status": NOT_QUERIED}}
                for pid, definition in PIDS.items():
                    status, detail = self.support_state(ecu, pid, service=2)
                    if status == SUPPORT_UNKNOWN:
                        self.session.freeze_frame.append(Reading(f"{pid:02X}", definition.name, definition.unit, ecu,
                                                                  status=status, detail=detail))
            self._read_freeze_codes(support)
            for pid, definition in PIDS.items():
                targets = [ecu for ecu, pids in support.items() if pid in pids]
                if not targets:
                    continue
                groups = [targets] if set(targets) == set(support) else [[ecu] for ecu in targets]
                for group in groups:
                    try:
                        frames = self.targeted_query(f"02{pid:02X}00", group, support)
                    except TransportError:
                        for ecu in group:
                            self.session.freeze_frame.append(Reading(f"{pid:02X}", definition.name, definition.unit, ecu,
                                                                      status=QUERY_FAILED, detail="Ligação interrompida"))
                        raise
                    except ObdDecodeError as exc:
                        for ecu in group:
                            self.session.freeze_frame.append(Reading(f"{pid:02X}", definition.name, definition.unit, ecu, status=UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED, detail=str(exc)))
                        continue
                    for ecu in group:
                        try:
                            frame = next((f for f in frames if f.ecu == ecu), None)
                            if frame is None:
                                raise NoDataError("Esta ECU não respondeu.")
                            value = decode_pid(frame, pid, service=2)
                            self.session.freeze_frame.append(Reading(f"{pid:02X}", definition.name, definition.unit, ecu, value, AVAILABLE, now_iso()))
                        except ObdDecodeError as exc:
                            self.session.freeze_frame.append(Reading(f"{pid:02X}", definition.name, definition.unit, ecu, status=UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED, detail=str(exc)))
            self._finish_freeze()
        except ObdDecodeError as exc:
            self.session.freeze_status = UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED
            self.session.freeze_detail = str(exc)
        except TransportError:
            self._finish_freeze("Ligação interrompida; consultas restantes não concluídas.")
            raise
        return self.session.to_dict()

    def _read_freeze_codes(self, support: dict) -> None:
        for ecu, metadata in self.session.freeze_ecus.items():
            status, detail = self.support_state(ecu, 2, service=2)
            metadata["code_query"] = {"status": status, "detail": detail}
        targets = [ecu for ecu, pids in support.items() if 2 in pids]
        groups = [targets] if targets and set(targets) == set(support) else [[ecu] for ecu in targets]
        for group in groups:
            try:
                frames = self.targeted_query("020200", group, support)
            except ObdDecodeError as exc:
                for ecu in group:
                    self.session.freeze_ecus[ecu]["code_query"] = {"status": UNAVAILABLE if isinstance(exc, NoDataError) else QUERY_FAILED, "detail": str(exc)}
                continue
            for ecu in group:
                try:
                    frame = next((f for f in frames if f.ecu == ecu), None)
                    if frame is None:
                        raise NoDataError("Esta ECU não respondeu ao código associado.")
                    payload = matching_payload(frame, 2, 2, freeze=True)
                    if len(payload) != 2:
                        raise ObdDecodeError("Código de freeze frame incompleto.")
                    self.session.freeze_codes[ecu] = decode_dtcs(type(frame)(ecu, b"\x43" + payload), 3)
                    self.session.freeze_ecus[ecu]["code_query"] = {"status": COMPLETE}
                except ObdDecodeError as exc:
                    self.session.freeze_ecus[ecu]["code_query"] = {"status": QUERY_FAILED if not isinstance(exc, NoDataError) else UNAVAILABLE, "detail": str(exc)}

    def _finish_freeze(self, interruption: str = "") -> None:
        for ecu, metadata in self.session.freeze_ecus.items():
            readings = [r for r in self.session.freeze_frame if r.ecu == ecu]
            valid = [r for r in readings if r.status == AVAILABLE and r.value is not None]
            codes = self.session.freeze_codes.get(ecu, [])
            maps = {key: q for key, q in self.session.support_queries.items() if key.startswith(f"02/{ecu}/")}
            failures = [q for q in maps.values() if q["status"] != COMPLETE]
            failures += [{"status": r.status, "detail": r.detail} for r in readings if r.status != AVAILABLE]
            if metadata["code_query"]["status"] not in (COMPLETE, UNSUPPORTED):
                failures.append(metadata["code_query"])
            usable = bool(valid or codes)
            if usable:
                status = COMPLETE if valid and not failures and not interruption else PARTIAL
            elif interruption or any(q["status"] == QUERY_FAILED for q in failures):
                status = QUERY_FAILED
            elif any(q["status"] == COMPLETE for q in maps.values()) or metadata["code_query"]["status"] == COMPLETE:
                status = NO_USABLE_DATA
            else:
                status = UNAVAILABLE
            detail = [f"Frame 0: {len(valid)} leituras válidas; " + ("código " + ", ".join(codes) if codes else "sem código associado utilizável")]
            if not valid:
                detail.append("Não foram obtidas leituras dos parâmetros reconhecidos pela aplicação; isto não confirma ausência de freeze frame no veículo.")
            detail.extend(f"Mapa {key.split('/')[-1]}: {q.get('detail', q['status'])}" for key, q in maps.items() if q["status"] != COMPLETE)
            if metadata["code_query"].get("detail"):
                detail.append("Código associado: " + metadata["code_query"]["detail"])
            detail.extend(f"PID {r.pid}: {r.detail or r.status}" for r in readings if r.status != AVAILABLE)
            if interruption:
                detail.append(interruption)
            metadata.update(status=status, detail="; ".join(detail), timestamp=now_iso())
        states = [m["status"] for m in self.session.freeze_ecus.values()]
        usable = any(r.status == AVAILABLE and r.value is not None for r in self.session.freeze_frame) or any(self.session.freeze_codes.values())
        if usable:
            self.session.freeze_status = COMPLETE if states and all(s == COMPLETE for s in states) and not interruption else PARTIAL
        elif interruption or QUERY_FAILED in states:
            self.session.freeze_status = QUERY_FAILED
        else:
            self.session.freeze_status = NO_USABLE_DATA if NO_USABLE_DATA in states else UNAVAILABLE
        self.session.freeze_detail = " | ".join(ecu + ": " + m["detail"] for ecu, m in self.session.freeze_ecus.items()) or interruption or "Nenhum dado de freeze frame recebido."

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
        self.session.freeze_ecus = {}
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
