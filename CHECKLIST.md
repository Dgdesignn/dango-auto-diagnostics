# Progresso da primeira fase

## Entregue

- [x] Inspeccao do projecto existente e preservacao do teste TCP funcional.
- [x] Python efectivo 3.13.15 e dependencias instaladas no .venv principal.
- [x] Janela PySide6 executavel com Ligacao, Dados, Avarias, IA e Historico.
- [x] TCP local/configuravel; serial pyserial; Bluetooth SPP por COM Windows.
- [x] Estados independentes do adaptador/ECU e origem explicita.
- [x] Timeout total, respostas fragmentadas, limite de tamanho e serializacao.
- [x] ECU separada, servico/PID/comprimento validados e erros distintos.
- [x] RPM, temperatura, velocidade, suporte, polling e leituras antigas.
- [x] Codigos confirmados/pendentes, descricoes desconhecidas e freeze frame 0.
- [x] Limpeza restrita a simulacao, fotografia previa, confirmacao e releitura.
- [x] SDK oficial Gemini, schema, chave externa, cache e limites persistentes.
- [x] SQLite, consulta de sessoes e exportacao JSON.
- [x] Workers Qt, callbacks na thread GUI e encerramento sem workers abandonados.
- [x] README, explicacao das camadas e comandos exactos.
- [x] Nenhuma chave real adicionada ao codigo ou Git; configuracao local em `.env` ignorado.

## Verificado

- [x] Testes de descodificacao, erros, multiplas ECUs e mensagens CAN fragmentadas.
- [x] TCP fragmentado, timeout/desconexao e serial/SPP com substitutos.
- [x] SQLite/exportacao e Gemini simulado: sucesso, quota, falha e resposta invalida.
- [x] Cache, intervalos, limite diario e proteccao de mensagens de erro.
- [x] Interface aberta e operavel durante workers; guardar/abrir; falta de chave.
- [x] Interface: leitura, polling, desligar/religar e servidor inacessivel.
- [x] Capturas da janela em dimensoes normais e compactas.
- [x] ELM327-emulator v4.0.0 car: leituras de ECU 7E8 na interface.
- [x] Emulador: consultas 03/07 concluidas sem codigos; freeze frame NO DATA.
- [x] Nenhum comando 04 enviado pelos testes.

## Pendente de validacao externa

- [ ] Adaptador USB/veiculo fisico.
- [ ] Bluetooth SPP emparelhado e porta COM fisica.
- [ ] Simulador Android na rede.
- [x] Chamada real Gemini com credencial autorizada: JSON validado e tokens recebidos.
- [ ] Efeito do comando de limpeza no emulador (exige confirmacao na interface).
- [ ] Freeze frame num dispositivo/cenario que o disponibilize.

## Resultados da entrega

- `python -m unittest discover -s tests -q`: 42 testes aprovados, sem testes ignorados; inclui o arranque real por scripts/run_app.py.
- `python scripts/verify_gui.py --real`: 6 testes considerados, 4 aprovados e 2 ignorados de forma explicita (cancelamento de worker e confirmacao de limpeza usam apenas substitutos controlados).
- `python scripts/test_elm327_tcp.py`: inicializacao e RPM aprovados contra o emulador instalado, preservando o teste de terminal original.
- `python -m pip check`: nenhuma dependencia incompativel.
- `python -m compileall -q src scripts tests`: compilacao aprovada.
- Capturas Qt dos cinco separadores em 1120x740 e 860x600 unidades logicas, inspeccionadas para dados, IA e avarias. A escala de ecra Windows pode aumentar a resolucao PNG.
- Uma instancia temporaria do emulador separado foi iniciada para os testes e encerrada ao terminar. A instalacao em C:\Py\simulador_scanner nao foi alterada. Inicie-o no seu terminal antes de ligar pela aplicacao.

Dados de sessoes dos testes ficam apenas em pastas temporarias; capturas em artifacts/ estao ignoradas no Git. Gemini real, hardware e efeito da limpeza continuam pendentes conforme a lista acima.

## Revisão da interface

- [x] Origem sem dependência da posição do selector e validação entre sessão e ligação.
- [x] Histórico antigo preservado; casos de TCP local com origem real assinalados para confirmação.
- [x] Confirmação ao configurar TCP local como veículo real.
- [x] Tema Fusion com paleta e estilos completos; botões com ícone e texto visível.
- [x] Modelo, limite diário, intervalo mínimo e motivo de indisponibilidade Gemini visíveis.
- [x] Acentos em português e temperatura em °C.
- [x] Estados separados: Não consultado, Consulta em curso, Nenhum código devolvido, Indisponível e Falha de consulta.
- [x] Dados desactualizados após parar, falha de ligação ou expiração; flags também guardadas/exportadas/enviadas à IA.
- [x] 51 testes aprovados na suite completa, incluindo contraste e Gemini simulado.
- [x] Janela com emulador: 12 testes considerados, 8 aprovados e 4 ignorados por dependerem de falhas controladas/limpeza simulada.
- [x] compileall e pip check aprovados.
- [ ] Confirmar a origem real dos registos antigos 2 e 3 antes de qualquer reclassificação.
- [x] Gemini validado posteriormente com a credencial autorizada, apenas no `.env` local ignorado.

## Integracao Gemini real (11/10/2026)

- [x] Autenticacao aceite pela API.
- [x] Corrigido o pedido: `response_json_schema`, mantendo validacao Pydantic estrita.
- [x] Modelo local `gemini-3.8-flash`, indicado pela API em substituicao de 2.5 Flash para esta conta.
- [x] Dados ficticios: 850 rpm, origem emulador; JSON valido com as cinco seccoes.
- [x] Tokens informados pela API: 318 entrada, 350 saida, 1400 total.
- [x] Segunda consulta em cache, sem chamada adicional; teste de terminal com codigo de saida zero.
- [x] Janela aberta: worker, apresentacao da resposta real via cache e chave ausente dos textos.
- [x] 52 testes aprovados, incluindo regressao do formato do pedido Gemini.
- [x] `.env` confirmado como ignorado; sem novos commits ou publicacao nesta alteracao.
- [ ] Substituir a credencial partilhada por uma nova no `.env` local.

## Cenario P0301

- [x] Versao 4.0.0 e documentacao do ELM327-emulator inspeccionadas.
- [x] Cenario externo: P0301 confirmado, ralenti irregular, 88 graus Celsius, velocidade zero e freeze frame.
- [x] Launcher com API real, loopback, verificacao de porta ocupada e sem alterar site-packages.
- [x] Codigo recebido por TCP/OBD, descodificado e apresentado na janela, sem injectar dados na tabela.
- [x] Gemini exclusivamente simulado: sintomas, origem, leituras recentes e causas apenas hipoteticas.
- [x] Guardar, abrir, exportar, cache e desactualizacao apos desligar validados.
- [x] Tres testes dedicados em 35001 e 55 testes na suite completa aprovados, sem skips.
- [x] Capturas inspeccionadas, compileall e pip check aprovados.
- [x] Instancia existente em 35000 preservada; comando exacto para essa porta documentado.
- [x] Instrucoes e limites em `docs/CENARIO_P0301.md`; nenhuma chamada Gemini real automatica.
- [x] Funcionalidade em branch `feature/cenario-p0301` a partir de `develop`.

## Organizacao dos ambientes

- [x] Ambientes da aplicacao e do emulador mantidos separados, sem reinstalacao.
- [x] `requirements-emulator.txt` fixa ELM327-emulator 4.0.0; reproducao documentada em `docs/AMBIENTES.md`.
- [x] Descoberta por `ELM327_PYTHON`, pasta irma relativa ou Python corrente; erro explicito para override invalido.
- [x] Launcher comum para car/P0301, independente da pasta de arranque.
- [x] Configuracao externa de logging; logs em `logs/emulator/elm-<porta>.log`, append e rotacao.
- [x] Nenhum ficheiro interno do emulador alterado; logs antigos, chaves e sessoes preservados.
- [x] README actualizado com comandos e estado actual, distinguindo resultados historicos.
- [x] 64 testes aprovados, sem skips, incluindo 8 testes de descoberta/logging e 4 testes integrados do emulador.
- [x] compileall, pip check e diff --check aprovados; sem chamadas Gemini reais nesta alteracao.
- [ ] Instalacao de raiz noutro computador: instrucoes disponibilizadas, nao executada nesta validacao.

## Simulador com estados

- [x] API instalada 4.0.0 e documentacao oficial inspeccionadas; callbacks externos, sem editar site-packages.
- [x] Estado isolado por instancia: causa, confirmados, pendentes, MIL, freeze, leituras e monitor misfire.
- [x] healthy, rough_idle_p0301, multiple_dtcs, no_data, connection_loss e car original disponiveis.
- [x] 04/44 por TCP real, com ATH/ATS; limpa registos sem reparar causa; modo 02 deixa de devolver freeze.
- [x] Ciclos explicitos: pendente, confirmado/MIL/freeze; leitura nao avanca ciclos; resolver+limpar evita regressao.
- [x] Reposicao, isolamento entre dois servidores reais e readiness incompleto apos limpeza validados.
- [x] Painel Qt: selector, processo/portas, iniciar/parar, ciclo, resolver, repor e consultar estado.
- [x] Ligacao ao processo gerido sempre classificada como simulacao; confirmacao externa e registos antigos preservados.
- [x] Canal HTTP loopback autenticado, esquema estrito, tamanho/timeout limitados e sem comandos ECU inventados.
- [x] Reset/mudanca desligam e invalidam dados geridos anteriores; perda torna leituras antigas desactualizadas.
- [x] Porta ocupada e servidores externos preservados, inclusive ao fechar a janela.
- [x] Encerramento normal, durante arranque e forçado por timeout testados; handle do filho proprio no Windows.
- [x] Suite completa: 81 testes aprovados (64 existentes e 17 novos), sem ignorados na execucao local.
- [x] Execucao final em 2026-10-11: 163,925 segundos; verificacao posterior sem emuladores de teste activos.
- [x] Gemini exclusivamente simulado, incluindo origem, sintomas e leituras recentes; nenhuma chamada remota nova.
- [x] Janela efectivamente aberta; responsividade e captura `artifacts/stateful-simulator.png` verificadas.
- [x] compileall, pip check e diff --check aprovados; .env, bases locais, logs e capturas continuam ignorados.
- [x] Nenhum commit, push, alteracao de autoria ou publicacao nesta tarefa.
- [ ] USB/Bluetooth/Android/ECU fisica e Gemini remoto: nao validados nesta fase.
- [ ] Linux/macOS e instalacao apenas por wheel: nao validados; painel local requer launchers do checkout.
- [ ] Criterios de ECU real, monitores adicionais e captura fisica de freeze frame: fora deste modelo pedagogico.

Comandos, roteiro e limites em `docs/SIMULADOR_ESTADOS.md`. Os resultados de
seccoes anteriores sao historicos e nao substituem esta validacao.
