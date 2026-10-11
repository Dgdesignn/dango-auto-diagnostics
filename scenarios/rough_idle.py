"""Motor quente, parado, com ralenti irregular e P0301 confirmado."""

SCENARIO_NAME = "rough_idle_p0301"
RPM_SEQUENCE = (740, 680, 820, 710, 790)
COOLANT_C = 88
SYMPTOMS = (
    "Motor quente com funcionamento irregular ao ralenti, vibracao e oscilacao "
    "de RPM. Veiculo parado. Dados de um cenario de simulacao, nao de um veiculo real."
)


def frame(data: str) -> str:
    payload = bytes.fromhex(data)
    if not 1 <= len(payload) <= 7:
        raise ValueError("Este cenario usa apenas frames CAN simples de 1 a 7 bytes.")
    return (
        "<header>7E8</header>"
        f"<size>{len(payload):02X}</size>"
        f"<data>{payload.hex(' ').upper()}</data>"
    )


def entry(command: str, description: str, response: str | list[str]) -> dict:
    return {
        "Request": f"^{command}$", "Descr": description,
        "Header": "7E0", "Response": response,
    }


ObdMessage = {
    SCENARIO_NAME: {
        "PIDS_A": entry("0100", "Suporte 01, 05, 0C e 0D", frame("41 00 48 18 00 00")),
        "STATUS": entry("0101", "MIL activa, um DTC confirmado", frame("41 01 81 00 00 00")),
        "RPM": entry("010C", "Ralenti irregular sequencial", [
            frame(f"41 0C {rpm * 4 >> 8:02X} {rpm * 4 & 255:02X}") for rpm in RPM_SEQUENCE
        ]),
        "COOLANT_TEMP": entry("0105", "Motor quente: 88 graus Celsius", frame("41 05 80")),
        "SPEED": entry("010D", "Veiculo parado: 0 km/h", frame("41 0D 00")),
        "GET_DTC": entry("03", "P0301 confirmado", frame("43 03 01")),
        "GET_PENDING_DTC": entry("07", "Sem DTC pendente", frame("47 00 00")),
        "FREEZE_SUPPORT": entry("020000", "Suporte do freeze frame 0", frame("42 00 00 48 18 00 00")),
        "FREEZE_CODE": entry("020200", "P0301 associado ao freeze frame 0", frame("42 02 00 03 01")),
        "FREEZE_RPM": entry("020C00", "Freeze frame: 710 rpm", frame("42 0C 00 0B 18")),
        "FREEZE_TEMP": entry("020500", "Freeze frame: motor quente", frame("42 05 00 80")),
        "FREEZE_SPEED": entry("020D00", "Freeze frame: veiculo parado", frame("42 0D 00 00")),
        "UNSUPPORTED": {
            "Request": "^[0-9A-F]+$", "Descr": "Servico ou PID nao modelado",
            "Priority": 100, "Response": "<writeln>NO DATA</writeln>",
        },
    },
}
