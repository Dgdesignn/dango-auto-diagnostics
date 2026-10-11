"""Estado pedagogico por instancia; independente do pacote ELM e da interface."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock

from scenarios.rough_idle import RPM_SEQUENCE, frame

SCENARIOS = ("healthy", "rough_idle_p0301", "multiple_dtcs", "no_data", "connection_loss", "car")
NO_DATA = "<writeln>NO DATA</writeln>"
MODELED_PIDS = (4, 5, 6, 7, 11, 12, 13, 14, 15, 16, 17, 66)


def support_mask(base: int, freeze: bool = False) -> str:
    pids = set(MODELED_PIDS) | ({2} if freeze else {1}) | {32, 64}
    mask = sum(1 << (32 - (pid - base)) for pid in pids if base < pid <= base + 32)
    return f"{mask:08X}"


def synthetic_values(active: bool, multiple: bool = False, captured: bool = False) -> dict[int, str]:
    # Predefined test vectors, not a physical model or a copy of current readings.
    return {4: "38" if captured else "40" if active else "2E", 5: "80",
            6: "94" if captured else "A0" if active and multiple else "8A" if active else "82",
            7: "88" if captured else "98" if active and multiple else "86" if active else "81",
            11: "2F" if captured else "32" if active else "22", 12: "0B18" if captured else "0BB8",
            13: "00", 14: "8A" if captured else "88" if active else "98",
            15: "49" if captured else "4B", 16: "014A" if captured else "015E" if active else "0104",
            17: "0B" if captured else "0D" if active else "0A", 66: "36B0" if captured else "3778"}


class VehicleState:
    def __init__(self, scenario: str, loss_after_requests: int = 12):
        if type(loss_after_requests) is not int or loss_after_requests < 1:
            raise ValueError("O limite de pedidos deve ser um inteiro positivo.")
        self.lock = RLock()
        self.loss_after_requests = loss_after_requests
        self.reset(scenario)

    def reset(self, scenario: str | None = None) -> dict:
        with self.lock:
            scenario = scenario or self.scenario
            if scenario not in SCENARIOS:
                raise ValueError("Cenario desconhecido.")
            self.scenario = scenario
            self.causes = (["P0301"] if scenario == "rough_idle_p0301" else
                           ["P0300", "P0171", "P0302"] if scenario == "multiple_dtcs" else [])
            self.confirmed = self.causes[:2]
            self.pending = self.causes[2:]
            self.mil = bool(self.confirmed)
            self.freeze = self._freeze() if self.confirmed else None
            # Apenas o monitor continuo de falhas de combustao e modelado.
            self.monitors = {} if scenario in ("car", "no_data") else {"misfire": "complete"}
            self.cycles = 0
            self.rpm_index = 0
            self.rpm = 740 if self.causes else 750
            self.requests = 0
            self.loss_latched = False
            return self.snapshot()

    def _freeze(self) -> dict:
        return {"code": self.confirmed[0], "rpm": 710, "coolant_c": 88, "speed_kmh": 0,
                "values": synthetic_values(True, self.scenario == "multiple_dtcs", captured=True)}

    def snapshot(self) -> dict:
        with self.lock:
            return deepcopy({"scenario": self.scenario, "active_causes": self.causes,
                             "confirmed": self.confirmed, "pending": self.pending,
                             "mil": self.mil, "freeze": self.freeze, "monitors": self.monitors,
                             "cycles": self.cycles, "rpm": self.rpm, "coolant_c": 88,
                             "speed_kmh": 0, "obd_requests": self.requests,
                             "loss_latched": self.loss_latched,
                             "loss_after_requests": self.loss_after_requests})

    def control(self, action: str) -> dict:
        with self.lock:
            if action == "status":
                return self.snapshot()
            if action == "reset":
                return self.reset()
            if self.scenario in ("car", "no_data"):
                raise ValueError("Este cenario nao modela ciclos nem causas.")
            if action == "resolve":
                self.causes = []
                self.rpm = 750
            elif action == "cycle":
                self.cycles += 1
                self.monitors["misfire"] = "complete"
                if self.causes:
                    if self.cycles == 1 and not self.confirmed:
                        self.pending = list(self.causes)
                    elif self.cycles >= 2:
                        self.confirmed = list(self.causes)
                        self.pending = []
                        self.mil = True
                        if self.freeze is None:
                            self.freeze = self._freeze()
            else:
                raise ValueError("Accao desconhecida.")
            return self.snapshot()

    def should_disconnect(self) -> bool:
        with self.lock:
            self.requests += 1
            if self.scenario == "connection_loss" and self.requests > self.loss_after_requests:
                self.loss_latched = True
            return self.loss_latched

    @staticmethod
    def encoded_codes(codes: list[str]) -> str:
        return " ".join(f"{int(code[1:], 16):04X}" for code in codes) or "0000"

    def response(self, command: str) -> str:
        with self.lock:
            if self.scenario == "no_data":
                return NO_DATA
            if command == "04":
                self.confirmed = []
                self.pending = []
                self.mil = False
                self.freeze = None
                self.cycles = 0
                self.monitors = {name: "incomplete" for name in self.monitors}
                return frame("44")
            if command in ("03", "07"):
                codes = self.confirmed if command == "03" else self.pending
                return frame(("43 " if command == "03" else "47 ") + self.encoded_codes(codes))
            if command in ("0100", "0120", "0140"):
                base = int(command[2:], 16)
                return frame(f"41 {base:02X} {support_mask(base)}")
            if command == "0101":
                count = len(self.confirmed) | (128 if self.mil else 0)
                readiness = 0 if not self.monitors else (0x11 if self.monitors["misfire"] == "incomplete" else 1)
                return frame(f"41 01 {count:02X} {readiness:02X} 00 00")
            if command == "010C":
                self.rpm = RPM_SEQUENCE[self.rpm_index % len(RPM_SEQUENCE)] if self.causes else 750
                self.rpm_index += 1
                return frame(f"41 0C {self.rpm * 4:04X}")
            if len(command) == 4 and command.startswith("01"):
                pid = int(command[2:], 16)
                values = synthetic_values(bool(self.causes), self.scenario == "multiple_dtcs")
                if pid in values:
                    return frame(f"41 {pid:02X} {values[pid]}")
            if command.startswith("02") and self.freeze:
                if command in ("020000", "022000", "024000"):
                    base = int(command[2:4], 16)
                    return frame(f"42 {base:02X} 00 {support_mask(base, freeze=True)}")
                if command == "020200":
                    return frame("42 02 00 " + self.encoded_codes([self.freeze["code"]]))
                if len(command) == 6 and command.endswith("00"):
                    pid = int(command[2:4], 16)
                    if pid in self.freeze["values"]:
                        return frame(f"42 {pid:02X} 00 {self.freeze['values'][pid]}")
            return NO_DATA


def dynamic_messages(state: VehicleState) -> dict:
    commands = ("0100", "0120", "0140", "0101", "03", "07", "04", "020000", "022000", "024000", "020200")
    commands += tuple(f"01{pid:02X}" for pid in MODELED_PIDS)
    commands += tuple(f"02{pid:02X}00" for pid in MODELED_PIDS)
    def respond(_emulator, command, _pid, _entry):
        return state.response(command.replace(" ", "").upper())
    entries = {command: {"Request": f"^{command}$", "Header": "7E0",
                         "Descr": command, "ResponseHeader": respond} for command in commands}
    entries["UNSUPPORTED"] = {"Request": "^[0-9A-F]+$", "Priority": 100,
                              "Descr": "Nao modelado", "Response": NO_DATA}
    return entries
