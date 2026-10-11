from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout
from scanner_outo.ui.components import ReadingCard, Panel, Columns, label
from scanner_outo.ui.charts import ReadingChart
from scanner_outo.diagnostics.obd import DEFAULT_PIDS


class Overview(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 24)
        layout.setSpacing(24)
        self.cards = {"0C": ReadingCard("Regime do motor", "query_stats"),
                      "05": ReadingCard("Temperatura do líquido", "info"),
                      "42": ReadingCard("Tensão do módulo", "cable"),
                      "mil": ReadingCard("Luz de gestão do motor", "warning")}
        layout.addWidget(Columns(list(self.cards.values()), breakpoint=600, maximum=4))
        codes = Panel("Códigos consultados")
        self.codes = label("Não consultado")
        codes.body.addWidget(self.codes)
        readiness = Panel("Prontidão por ECU")
        self.readiness = label("Não consultado")
        readiness.body.addWidget(self.readiness)
        layout.addWidget(Columns([codes, readiness]))
        chart = Panel("Telemetria da sessão")
        self.chart = ReadingChart(window.series)
        self.chart.select_pids(DEFAULT_PIDS)
        self.chart.setMinimumHeight(280)
        chart.body.addWidget(self.chart)
        layout.addWidget(chart)
        actions = QGridLayout()
        self.shortcuts = []
        for index, (title, callback) in enumerate((
            ("Actualizar dados", window.poll), ("Consultar avarias", window.read_codes),
            ("Consultar freeze frame", window.read_freeze),
            ("Abrir análise", lambda: window.tabs.setCurrentIndex(3)))):
            button = window.button(title, callback)
            actions.addWidget(button, index // 2, index % 2)
            self.shortcuts.append(button)
        layout.addLayout(actions)

    def refresh(self, state):
        for pid, card in self.cards.items():
            if pid == "mil":
                monitors = state.get("monitor_status", {})
                entries = [ecu + ": " + ("Acesa" if s["mil"] else "Apagada") for ecu, s in monitors.items() if "mil" in s]
                card.value.setText(" / ".join(entries) or "--")
                card.detail.setText(state.get("monitor_query", {}).get("status", "Não consultado") + (" (desactualizado)" if state["adapter_status"] != "Ligado" and entries else ""))
            else:
                entries = [r for r in state["readings"] if r["pid"] == pid]
                card.value.setText(" / ".join(self.window.value_text(r["value"]) + " " + r["unit"] for r in entries) or "--")
                card.detail.setText(" / ".join(r["ecu"] + ": " + self.window.reading_status(r) for r in entries) or "Não consultado")
        self.codes.setText("\n".join(c["code"] + " | " + c["status"] + " | ECU " + c["ecu"] for c in state["codes"]) or "\n".join(kind + ": " + q["status"] for kind, q in state["code_queries"].items()) or "Não consultado")
        self.readiness.setText("\n".join(ecu + ": " + "; ".join(m["name"] + ": " + ("Concluído" if m["complete"] else "Incompleto") for m in s.get("monitors", [])) for ecu, s in state.get("monitor_status", {}).items()) or "Não consultado")
        selected = self.window.selected_pids()
        if tuple(self.chart.selector.itemData(i) for i in range(self.chart.selector.count())) != selected:
            self.chart.select_pids(selected)
        else:
            self.chart.refresh()
        for button in self.shortcuts[:3]:
            button.setEnabled(state["adapter_status"] == "Ligado" and not self.window.busy["diag"] and not self.window.closing)


def build(window):
    window.overview = Overview(window)
    window.tabs.addTab(window.overview, "Visão geral")
