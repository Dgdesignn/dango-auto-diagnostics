# Cenario de avaria P0301

## Implementacao

Foi inspeccionado o ELM327-emulator **4.0.0**, instalado em
`C:\Py\simulador_scanner\.venv`. A
[documentacao do projecto](https://github.com/Ircama/ELM327-emulator#emulator-as-a-library)
descreve o dicionario `ObdMessage`, o carregamento externo por `merge` e a classe
`Elm` como biblioteca TCP. O launcher usa essa biblioteca e os argumentos
`net_port` e `net_interface` confirmados no codigo instalado; nao usa um comando
ELM inventado para configurar avarias.

- `scenarios/rough_idle.py`: dicionario externo com as respostas OBD e sintomas sugeridos.
- `scripts/run_fault_emulator.py`: instancia `Elm`, conserva os comandos AT do pacote
  e aplica callbacks de `scenarios/vehicle.py` apenas a essa instancia.
- `tests/test_fault_scenario.py`: inicia o pacote real num processo separado e usa os
  transportes, descodificador, servicos e janela existentes, sem injectar DTCs na tabela.
- `scripts/verify_fault_scenario.py`: executa os quatro testes integrados e termina apenas
  o processo que iniciou. Usa SQLite temporario, Gemini simulado e capturas ignoradas.

Nenhum ficheiro de `site-packages` e alterado. Os dados OBD de `default` e `car`
nao sao herdados; pedidos nao modelados devolvem `NO DATA`. A versao diferente de
4.0.0 e recusada ate se validar a compatibilidade.

## Dados do cenario

Uma ECU responde como `7E8`, a pedidos fisicos `7E0` ou funcionais `7DF`.

| Pedido | Resposta com cabecalho | Significado |
| --- | --- | --- |
| `0100` | `7E8 06 41 00 48 18 00 00` | Suporte dos PIDs 01, 05, 0C e 0D |
| `0101` | `7E8 06 41 01 81 01 00 00` | MIL ligada, um DTC confirmado, monitor misfire modelado |
| `010C` | `7E8 04 41 0C ...` | Ciclo 740, 680, 820, 710, 790 rpm |
| `0105` | `7E8 03 41 05 80` | Temperatura de 88 graus Celsius |
| `010D` | `7E8 03 41 0D 00` | Velocidade de 0 km/h |
| `03` | `7E8 03 43 03 01` | P0301 confirmado |
| `07` | `7E8 03 47 00 00` | Nenhum codigo pendente |
| `020200` | `7E8 05 42 02 00 03 01` | P0301 associado ao freeze frame 0 |

Freeze frame 0: 710 rpm, 88 graus Celsius, 0 km/h. A descodificacao de RPM usa
`(A * 256 + B) / 4`, e de temperatura `A - 40`. O suporte e coerente com os PIDs
declarados. A fase do ciclo RPM pode continuar apos religar; reiniciar o launcher
cria novos contadores. A oscilacao depende das consultas, nao do tempo fisico.

P0301 descreve falha de combustao no cilindro 1; nao identifica uma peca especifica.
O pedido Gemini reforca que causas sao hipoteses, nao conclusoes de substituicao.

## Iniciar manualmente em 127.0.0.1:35000

1. Desliga a aplicacao do emulador actual. No terminal desse emulador, termina-o
   normalmente. Nao deixes duas instancias a tentar utilizar a porta 35000.
2. Num terminal PowerShell, executa exactamente:

```powershell
cd C:\Py\scanner_outo
& C:\Py\simulador_scanner\.venv\Scripts\python.exe -u scripts\run_fault_emulator.py --port 35000
```

Espera pela mensagem `READY ELM327-emulator 4.0.0: rough_idle_p0301 em 127.0.0.1:35000`.
Mantem este terminal aberto. `Ctrl+C` termina esta instancia. Se a porta estiver
ocupada, o launcher falha com mensagem clara, sem terminar outros processos.
O servidor fica limitado a loopback, sem acesso pela rede externa.

Tambem podes usar a descoberta automatica, a partir da pasta do projecto:

```powershell
.\.venv\Scripts\python.exe scripts\run_emulator.py --scenario rough_idle_p0301 --port 35000
```

Ambos usam o Python do emulador e guardam logs em `logs/emulator/elm-35000.log`.
Os ambientes e a sua reproducao estao em [AMBIENTES.md](AMBIENTES.md).

3. Noutro terminal, abre a aplicacao:

```powershell
cd C:\Py\scanner_outo
.\.venv\Scripts\python.exe scripts\run_app.py
```

4. Selecciona TCP, `127.0.0.1`, porta `35000` e origem de emulador/simulacao.
   Clica em **Ligar**, depois em **Consultar avarias**. Deve surgir P0301,
   confirmado, ECU 7E8, com a descricao de falha de combustao no cilindro 1.
5. Consulta o freeze frame. Em Dados, clica em **Iniciar actualizacao**: RPM oscila
   entre 680 e 820, temperatura fica em 88 graus Celsius e velocidade em zero.
6. Em Analise por IA, informa os sintomas:

```text
Motor quente com funcionamento irregular ao ralenti, vibracao e oscilacao de RPM.
Veiculo parado. Dados de um cenario de simulacao, nao de um veiculo real.
```

7. Usa **Rever dados** para conferir origem de simulacao, P0301, sintomas e
   parametros recentes. Mantem a actualizacao activa ou clica em **Actualizar**
   imediatamente antes da analise. **Parar** marca os valores como desactualizados;
   nao envies esses valores como se fossem recentes.
8. A chamada real so acontece quando carregares em **Analisar com Gemini**.
   A chave continua apenas no `.env` local. O modelo e os limites sao os da janela.
   O resultado deve distinguir factos, hipoteses e testes de confirmacao, sem
   afirmar que o codigo prova uma falha de vela, bobina ou injector.
9. **Guardar sessao**, **Abrir sessao** e **Exportar JSON** devem preservar a origem,
   codigo, estados, sintomas e fotografia enviada ao Gemini. Os dados do teste
   manual ficam na base local da aplicacao, nunca no Git.

## Teste automatico, sem Gemini real

Usa a .venv da aplicacao para Qt e o Python do emulador para o servidor:

```powershell
cd C:\Py\scanner_outo
.\.venv\Scripts\python.exe -X utf8 scripts\verify_fault_scenario.py
```

O teste escolhe uma porta livre e nao interrompe o emulador em 35000. Se quiseres
validar especificamente essa porta, para primeiro o emulador manual e executa:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\verify_fault_scenario.py --port 35000
```

Essa opcao inicia uma instancia temporaria; nao se liga a uma instancia existente.
Uma porta ocupada causa falha, nao altera nem interrompe a instancia actual.
Tambem podes usar `--port 35001` para testar ao lado do emulador actual.

Os testes confirmam o pedido 03, resposta 43 com bytes 03 01, descodificacao,
apresentacao Qt, dois ciclos RPM, temperatura, velocidade, freeze frame, leituras
recentes, sintomas, origem, Gemini simulado, cache, guardar/abrir/exportar e dados
desactualizados apos desligar. O cliente simulado verifica o pedido recebido e
devolve causas possiveis e testes; o gerador real esta bloqueado por uma assercao.
Nao e carregado `.env`, nao sao enviadas credenciais nem feitas chamadas Google.

Capturas: `artifacts/fault-p0301-codes.png` e `artifacts/fault-p0301-ai.png`.
Se faltar o emulador, a suite geral assinala estes testes como ignorados;
o verificador dedicado falha explicitamente. `ELM327_PYTHON` pode apontar para
outro ambiente que tenha a mesma versao instalada.

A pasta irma `simulador_scanner/.venv` e descoberta automaticamente, sem caminho
fixo para `C:\Py`. O quarto teste verifica o launcher `car` a partir de outra
pasta e a localizacao centralizada dos logs.

## Resultado historico da primeira validacao

- ELM327-emulator 4.0.0 inspeccionado e iniciado pelo launcher externo.
- Tres testes dedicados aprovados em `127.0.0.1:35001`; porta 35000 ocupada
  pela instancia existente, que foi preservada.
- Suite completa: 55 testes aprovados, sem testes ignorados, incluindo nova
  instancia em porta livre escolhida automaticamente.
- Pedido recebido pelo transporte: `03`; resposta real do emulador:
  `7E8 03 43 03 01`; descodificacao: P0301 confirmado, ECU 7E8.
- Dois ciclos de RPM recebidos e descodificados, 88 graus Celsius e 0 km/h.
- Janela, Gemini simulado, cache, SQLite, abrir, exportar e leituras antigas aprovados.
- Capturas de avarias e IA inspeccionadas; compilacao e `pip check` aprovados.
- Nenhuma chamada real ao Gemini nem comando de limpeza enviados nesta validacao.
- Branch Gitflow: `feature/cenario-p0301`, criada a partir de `develop`.
  `main` e `develop` preservadas, sem merge ou push automatico.

## Limites

- Dados sinteticos de uma unica ECU, nao um modelo de combustao ou de um veiculo especifico.
- RPM oscilante e P0301 sao coerentes para testar o fluxo, mas nao provam a causa mecanica.
- Nao simula fuel trims, sensores de oxigenio, contadores de falhas, modo 06 ou codigos permanentes.
- O PID 0101 modela agora MIL, contagem e um monitor misfire simplificado; nao valida readiness fisico.
- Freeze frame e fixo, nao captura automaticamente o instante de uma falha.
- Limpeza 04 implementada: devolve `44`, limpa registos sem resolver a causa.
- Nao testa USB, Bluetooth, Android, ECU real ou reparacao fisica.
- Gemini simulado valida o fluxo e o pedido, nao o comportamento de um modelo real;
  a resposta real depende do modelo e deve ser revista por uma pessoa.

## Evolucao com estados

Os cenarios adicionais, controlo separado, interface, limpeza e reaparecimento
estao documentados em [SIMULADOR_ESTADOS.md](SIMULADOR_ESTADOS.md).
A validacao historica acima nao deve ser confundida com os resultados da suite actual.
