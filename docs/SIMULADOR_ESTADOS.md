# Simulador local com estados

## Ambientes e API validada

Aplicação: `C:\Py\scanner_outo\.venv`. Emulador:
`C:\Py\simulador_scanner\.venv`, ELM327-emulator **4.0.0**.
A versão e o código instalados foram inspeccionados; o launcher recusa outras versões.
A [documentação oficial](https://github.com/Ircama/ELM327-emulator#configuring-response-strings)
confirma os callbacks `ResponseHeader(self, cmd, pid, uc_val)` e as tags
`header`, `size`, `data`. É este ponto de extensão que produz respostas dinâmicas,
formatadas pelo pacote segundo ATH/ATS/CAF, recebidas pelo TCP OBD real.

Nenhum ficheiro interno do pacote é modificado. Os comandos AT são copiados para
cada instância; `VehicleState`, protegido por `RLock`, mantém causas, códigos,
MIL, freeze frame, leituras e monitor separados. Consultar RPM avança apenas a
sequência de valores, nunca o ciclo de diagnóstico.

## Organização da implementação

- `scenarios/vehicle.py`: modelo puro de estado, retratos independentes e respostas
  dinâmicas de 01/02/03/04/07. Não depende de Qt, Gemini ou bases de dados.
- `scenarios/control.py`: servidor HTTP separado de OBD; autentica token efémero,
  valida o JSON e expõe apenas status, cycle, resolve, reset e shutdown.
- `scripts/run_fault_emulator.py`: reutiliza a classe Elm instalada, copia AT e
  liga callbacks ao estado desta instância. Uma subclasse interrompe o socket
  no limiar configurado e fecha o cliente durante o encerramento do emulador.
- `scripts/control_emulator.py`: cliente de terminal para esse canal local; não
  liga à porta OBD e não altera tabelas ou sessões da aplicação.
- `src/scanner_outo/ui/simulator.py`: QProcess próprio, descoberta reutilizada de
  ambiente, handshake validado e pedidos HTTP em workers. No Windows, conserva
  um handle do filho autenticado da venv para o fallback de timeout, sem WMI.
- `src/scanner_outo/ui/main_window.py`: distingue ligação gerida/externa, fixa
  origem de simulação para o processo próprio e coordena desligar/invalidar antes
  da reposição. A confirmação, fotografia e releitura da limpeza existentes mantêm-se.
- `tests/test_stateful_simulator.py`: testa modelo, servidores reais isolados e
  janela Qt; os DTCs atravessam transportes, descodificadores e serviços existentes.

## Cenários

| Cenário | Estado inicial |
| --- | --- |
| `healthy` | Sem causas/códigos; MIL apagada; 750 rpm, 88 °C, 0 km/h; sem freeze frame. |
| `rough_idle_p0301` | Causa activa; P0301 confirmado; MIL acesa; sequência 740, 680, 820, 710, 790 rpm; 88 °C; 0 km/h; freeze de P0301 a 710 rpm. |
| `multiple_dtcs` | Causas sintéticas de falhas de combustão/mistura pobre: P0300 e P0171 confirmados, P0302 pendente; MIL acesa; mesmo ralenti irregular; freeze associado a P0300. Não estabelece relação causal entre estes códigos. |
| `no_data` | AT funcional; todos os pedidos OBD, incluindo limpeza, devolvem NO DATA. Não equivale a consulta concluída sem códigos. |
| `connection_loss` | Inicialmente saudável; interrompe o socket no pedido OBD N+1, após N pedidos permitidos. AT não conta. A interrupção fica latched até repor/reiniciar o cenário. |
| `car` | Dicionário original do pacote, sem substituição dos seus dados ou semântica por este modelo. Ciclo/resolução não disponíveis. |

O limite da perda é `--loss-after-requests` (por omissão 12). Exemplo determinístico:
com N=4, Ligar envia um `0100`, Actualizar envia três PIDs; o próximo pedido
OBD perde a ligação. Pedidos de avarias/freeze também contam. O canal de controlo
continua acessível para repor o cenário.

## Limpar não é reparar

Nos cenários personalizados com dados, `04` recebido por TCP devolve `44`,
limpa confirmados/pendentes, MIL e freeze frame, repõe o contador de ciclos e
torna incompleto o único monitor modelado: falhas de combustão (`misfire`).
A causa e o ralenti irregular permanecem activos.

O PID `0101` anuncia somente este monitor: byte B=01 quando concluído e B=11
após limpar; C/D=00 não anunciam monitores adicionais. A interpretação dos bits
foi conferida com o [descodificador python-OBD](https://github.com/brendan-w/python-OBD/blob/master/obd/decoders.py).
O retrato inicial representa diagnóstico já realizado; novos ciclos explícitos
executam novamente este monitor simplificado. Não são simulados critérios físicos,
monitores de catalisador, fuel trims, modo 06 ou códigos permanentes.

Sequência pedagógica após limpar P0301:

1. Consultas `03`/`07`: sem códigos; MIL apagada; modo `02`: NO DATA.
2. **Novo ciclo**: P0301 pendente; MIL apagada; sem freeze; monitor concluído.
3. **Novo ciclo**: P0301 confirmado; MIL acesa; freeze frame sintético de 710 rpm.
4. **Resolver causa** não apaga o histórico: deixa os códigos já registados.
5. Limpar depois de resolver e executar novos ciclos não gera novamente P0301.
6. **Repor cenário** restaura o retrato inicial, incluindo causa, códigos e contadores.

Esta regra de dois ciclos é didáctica, não uma afirmação sobre todas as ECUs.
P0301 identifica falha de combustão no cilindro 1, não uma peça específica.

## Execução pelo terminal

Num PowerShell, a partir do projecto, sem activar ambientes:

```powershell
cd C:\Py\scanner_outo
.\.venv\Scripts\python.exe scripts\run_emulator.py --scenario rough_idle_p0301 --port 35000
```

Alternativa directa, usando o ambiente separado:

```powershell
& C:\Py\simulador_scanner\.venv\Scripts\python.exe -X utf8 -u C:\Py\scanner_outo\scripts\run_fault_emulator.py --scenario multiple_dtcs --port 35000
```

Para perda controlada:

```powershell
.\.venv\Scripts\python.exe scripts\run_emulator.py --scenario connection_loss --port 35000 --loss-after-requests 4
```

Escolhe qualquer cenário da tabela com `--scenario`. `car` permanece o valor
por omissão do launcher comum. `Ctrl+C` pára a instância manual.
Porta ocupada produz erro e não termina o servidor existente; usa, por exemplo,
`--port 35001` para correr ao lado dele. Logs: `logs/emulator/elm-<porta>.log`.

Cada arranque imprime uma linha `CONTROL` com uma porta livre e token efémero
local (não é chave Gemini). O controlo usa HTTP autenticado em **127.0.0.1**,
separado do socket ELM; não existe qualquer comando de controlo inventado para ECU.
Podes escolher a porta com `--control-port 35002`. Pedidos têm tamanho limitado,
esquema estrito e acções enumeradas; não executam código arbitrário.

Noutro terminal, preenche os valores impressos por essa instância:

```powershell
cd C:\Py\scanner_outo
$controlPort = 35002 # substituir pela porta CONTROL, se automática
$controlToken = 'TOKEN_EFEMERO_DA_LINHA_CONTROL'
.\.venv\Scripts\python.exe scripts\control_emulator.py status --port $controlPort --token $controlToken
.\.venv\Scripts\python.exe scripts\control_emulator.py cycle --port $controlPort --token $controlToken
.\.venv\Scripts\python.exe scripts\control_emulator.py resolve --port $controlPort --token $controlToken
# Desligar primeiro a aplicação antes de repor manualmente:
.\.venv\Scripts\python.exe scripts\control_emulator.py reset --port $controlPort --token $controlToken
.\.venv\Scripts\python.exe scripts\control_emulator.py shutdown --port $controlPort --token $controlToken
```

Não guardes o token em ficheiros versionados. Não alteres o `.env` nem coloques
credenciais na linha de comando. O processo gerido não recebe variáveis Gemini/Google.

## Validação na janela

```powershell
cd C:\Py\scanner_outo
.\.venv\Scripts\python.exe scripts\run_app.py
```

1. Em **Simulador local**, escolhe P0301 e uma porta livre, depois **Iniciar simulador**.
   O painel mostra PID, endereço OBD, controlo e o estado consultado.
2. Em **Ligação**, escolhe TCP, 127.0.0.1, a mesma porta e origem de simulação;
   **Ligar**. O cabeçalho distingue Simulador gerido de Servidor externo. Uma
   ligação ao processo gerido é sempre classificada como simulação, mesmo se
   tiver sido seleccionada origem de veículo real. Servidores externos conservam
   a escolha/confirmação existente; registos antigos não são reescritos.
3. Em **Dados**, Actualizar; em **Avarias**, Consultar avarias e Consultar freeze frame.
4. **Limpar registos** guarda uma fotografia em SQLite antes de pedir confirmação
   (Não por omissão), envia `04` e relê `03`/`07`. Não está disponível em veículo real.
5. No painel, usa **Novo ciclo**, depois consulta avarias; repete para confirmar.
   Usa **Resolver causa**, limpa novamente e avança ciclos: o código não regressa.
6. **Repor cenário** pede confirmação, desliga a sessão gerida e invalida os dados
   anteriores, incluindo análise associada. Liga novamente para novas leituras.
7. Para mudar cenário, **Parar simulador**, seleccionar, iniciar e ligar novamente.
   A selecção fica bloqueada enquanto esse processo corre.
8. Confere os outros cenários e a perda controlada. Após queda, valores anteriores
   ficam desactualizados. Guardar uma sessão continua a preservar a sua origem.

O painel actualiza o estado após controlos e operações OBD geridas; **Actualizar
estado** consulta-o manualmente. Estes dados são o estado interno do simulador,
não leituras injectadas nas tabelas da aplicação. Os DTCs apresentados continuam
a vir exclusivamente de respostas OBD.

QProcess e workers mantêm a interface responsiva. Só o processo iniciado por esta
janela é gerido; servidores manuais não recebem controlos locais e nunca são
terminados ao fechar. O encerramento pede shutdown pelo controlo, com timeout e
fallback limitado ao QProcess próprio e ao handle do seu filho autenticado
(redirector Python da venv no Windows), sem enumerar outros processos.
Fechar durante arranque também aguarda/encerra essa instância.
TCP externo, USB serial e Bluetooth SPP mantêm os caminhos existentes.

## Testes e limites

```powershell
cd C:\Py\scanner_outo
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_stateful_simulator.py -v
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

Os testes iniciam instâncias próprias do pacote real em portas livres, com SQLite
temporário e sem tocar na instância do utilizador em 35000. A suite antiga testa
Gemini com cliente simulado; nos testes novos o gerador remoto está proibido.
Se faltar o ambiente ELM, os testes de integração são explicitamente ignorados.
Captura do painel: `artifacts/stateful-simulator.png`, ignorada pelo Git.

Execução final em **2026-10-11**: **81 testes aprovados**, 64 existentes e 17 novos,
em 163,925 segundos, **zero ignorados**. Inclui TCP real do pacote 4.0.0,
janela aberta, origem gerida de simulação, limpeza com fotografia prévia,
ciclos, resolução, reposição, múltiplos DTCs, NO DATA, perda de ligação,
isolamento, validação do controlo, CLI manual, porta ocupada, servidor externo
preservado e encerramento normal/durante arranque/forçado. A verificação posterior
não encontrou processos dos novos emuladores de teste ainda activos.

`compileall`, `pip check` e `git diff --check` passaram; a captura do painel foi
inspeccionada, sem sobreposições. Gemini só foi testado com cliente simulado.
Detalhes no CHECKLIST. Sem commits, push ou publicação nesta alteração.
Ambientes, sessões e `.env` existentes preservados.

Limitações: modelo sintético de uma ECU/frames CAN simples; freeze frame usa
valores predefinidos; RPM depende das consultas, não do tempo; a reposição de
`car` não reinicia os contadores internos do pacote (parar/iniciar é o reset completo).
A gestão local requer o checkout com os launchers, não apenas uma wheel instalada.
USB, Bluetooth, Android, ECU física e Gemini remoto não foram validados nesta fase.
