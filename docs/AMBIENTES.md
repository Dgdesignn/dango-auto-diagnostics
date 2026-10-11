# Organizacao dos ambientes

## Pastas e responsabilidades

```text
pasta-base/
  scanner_outo/
    .venv/                     Python e dependencias da aplicacao
    src/scanner_outo/          Comunicacao, diagnostico, interface e servicos
    scenarios/                Cenarios personalizados versionados
    scripts/                  Launchers, descoberta de ambiente e verificadores
    config/elm-logging.json   Configuracao externa dos logs do emulador
    requirements-emulator.txt Versao validada do emulador
    tests/                    Testes unitarios e integrados
    docs/                     Instrucoes e resultados
    data/                     SQLite e log da aplicacao
    logs/emulator/            Logs do emulador, separados por porta
    artifacts/                Capturas de testes
  simulador_scanner/
    .venv/                     Python e dependencias do ELM327-emulator
```

Mantem os ambientes separados. O emulador e uma ferramenta de teste e nao uma
dependencia obrigatoria da aplicacao. Os cenarios e launchers permanecem no
repositorio para serem versionados, sem alterar `site-packages`.

## Recriar o ambiente do emulador

No ambiente actual ja existe ELM327-emulator 4.0.0. Nao e preciso reinstalar.
Para outra instalacao Windows, com Python 3.13, usa uma pasta nova:

```powershell
cd C:\Py
New-Item -ItemType Directory -Path simulador_scanner
cd .\simulador_scanner
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ..\scanner_outo\requirements-emulator.txt
.\.venv\Scripts\python.exe -c "from importlib.metadata import version; print(version('ELM327-emulator'))"
```

O ficheiro fixa a versao do emulador em 4.0.0. As dependencias transitivas sao
resolvidas pelo pip; nao e um lock completo. A instalacao requer acesso ao PyPI.
Nao copies ambientes virtuais entre computadores nem recries a `.venv` existente
sem necessidade. A aplicacao continua a ser instalada pelo seu `pyproject.toml`.

## Descoberta do Python do emulador

`scripts/emulator_environment.py` e partilhado pelo launcher e pelos testes.
A ordem de descoberta e:

1. `ELM327_PYTHON`, se definida: caminho absoluto ou relativo a raiz do projecto.
   Um caminho invalido produz erro, sem fallback silencioso.
2. `.venv` de `simulador_scanner`, ao lado da pasta do projecto, usando
   `Scripts/python.exe` no Windows ou `bin/python` nos restantes sistemas.
3. Python corrente, se nele estiver instalado o modulo `elm`.

A descoberta nao depende de `C:\Py`. Esse caminho aparece nos exemplos apenas
porque corresponde a instalacao actual. A versao e validada pelo launcher.
Para um ambiente noutra localizacao:

```powershell
$env:ELM327_PYTHON = 'D:\Ferramentas\simulador_scanner\.venv\Scripts\python.exe'
```

## Executar

Num terminal para o emulador, a partir do projecto:

```powershell
cd C:\Py\scanner_outo
# Cenario original car:
.\.venv\Scripts\python.exe scripts\run_emulator.py --scenario car --port 35000
```

Para a avaria, usa este comando em vez do anterior:

```powershell
.\.venv\Scripts\python.exe scripts\run_emulator.py --scenario rough_idle_p0301 --port 35000
```

O Python da aplicacao so descobre e chama o Python do emulador; o pacote `elm`
continua a executar na sua propria `.venv`. Mantem o terminal aberto e termina
com `Ctrl+C`. Nunca inicies ambos na mesma porta.

O comando anterior, a partir da pasta do emulador, continua valido:

```powershell
cd C:\Py\simulador_scanner
.\.venv\Scripts\python.exe -u ..\scanner_outo\scripts\run_fault_emulator.py --port 35000
```

Noutro terminal, para a aplicacao:

```powershell
cd C:\Py\scanner_outo
.\.venv\Scripts\python.exe scripts\run_app.py
```

Para o teste automatico, numa porta livre e sem chamadas Gemini reais:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\verify_fault_scenario.py
```

## Logs e dados locais

Os launchers usam `config/elm-logging.json` como modelo e a variavel
`ELM_LOG_CFG` reconhecida pelo pacote 4.0.0. O log de cada
processo usa um caminho absoluto, resolvido por uma factory de logging do
projecto. JSON e aceite pelo carregador YAML do emulador; nenhum ficheiro interno
e modificado e nao sao gerados ficheiros temporarios de configuracao.

Os logs vao para `scanner_outo/logs/emulator/elm-<porta>.log`, com append,
rotacao de 1 MB e duas copias. O caminho nao depende do terminal de onde arrancas.
Portas diferentes usam ficheiros diferentes. O log e mostrado no arranque.

`python -m elm` directamente nao passa pelos nossos launchers e conserva o
comportamento de logs do proprio pacote. Usa `run_emulator.py` para o cenario
car com a configuracao centralizada. Os `elm.log` antigos nas raizes das duas
pastas foram preservados e nao sao migrados nem apagados automaticamente.

SQLite e log da aplicacao continuam em `data/`; `SCANNER_DATA_DIR` permite
substituir essa localizacao. `.env`, `.venv`, `logs/`, `data/` e `artifacts/`
continuam ignorados pelo Git. Nao foram alteradas chaves ou sessoes existentes.

Os cenarios/launchers sao ferramentas do checkout, nao componentes do pacote
distribuido de `src`. Para os usar noutro computador, leva o repositorio completo,
nao apenas o pacote instalado da aplicacao.

## Validacao do reajuste

64 testes aprovados, sem skips: descoberta relativa, caminhos com espacos,
override invalido, logging em append, arranque car noutra pasta, P0301 via OBD,
interface, Gemini simulado, cache e persistencia. Compilacao, `pip check` e
`git diff --check` aprovados. Nenhuma chamada Gemini real foi efectuada.
A instalacao de raiz com o manifesto esta documentada, mas nao foi executada
num segundo computador; os ambientes existentes nao foram reinstalados.
