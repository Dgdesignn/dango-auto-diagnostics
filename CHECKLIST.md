# Progresso da primeira fase

## Barra lateral animada

- [x] Botao de menu acessivel, com tooltip e activacao por teclado.
- [x] Expansao/recolha entre 260 e 72 pixels; animacao InOutCubic de 240 ms.
- [x] Cliques rapidos invertem a animacao sem acumular transicoes.
- [x] Escolha manual mantida ao redimensionar; comportamento responsivo por omissao.
- [x] Sete ecras testados com barra expandida em janela de 860x600, sem cortar controlos.
- [x] Comandos de diagnostico, dados e simulador adaptados a linhas adicionais.
- [x] Tres testes especificos aprovados; teste adicional na aplicacao real aprovado.
- [x] Regressao final: 120 testes aprovados, sem falhas/ignorados, em 366,287 s.
- [x] compileall e pip check aprovados; diff --check do codigo e documentacao aprovados.
- [x] Espacos finais preexistentes em tres linhas da referencia HTML e numa linha da licenca Inter preservados.
- [x] Capturas expandida/recolhida em artifacts/stitch; credenciais, logs e bases excluidos do Git.
- [x] Nenhuma chamada Gemini real; emulador externo e dados do utilizador preservados.

## Visual DANGO baseado no Stitch

- [x] Inspeccionados HTML/PNG dos sete ecras e Sistema de Design, fornecidos em design/stitch; nenhuma referencia obrigatoria em falta.
- [x] Qt Widgets mantido; sem dependencia nova, sem QWebEngine, React ou Electron.
- [x] Tokens centralizados, fontes Inter/JetBrains Mono e Material Outlined locais com licencas; package-data configurado.
- [x] Navegacao lateral, cabecalho de estados reais, sete ecras, modo compacto e rolagem.
- [x] Visao geral usa leituras/series existentes sem consultas automaticas; 12 PIDs e estados preservados.
- [x] IA em cinco seccoes, Historico em arquivo/ficha e areas tecnicas recolhiveis; sem copiar dados ficticios.
- [x] Corrigida sincronizacao de seleccao dos PIDs e sobreposicao do formulario IA no modo compacto.
- [x] 12 testes de interface existentes aprovados em 112,406 s; verificacoes funcionais mantidas, expectativas visuais adaptadas.
- [x] Tres testes novos de navegacao/recursos/fluxo/perda aprovados na primeira execucao dedicada em 69,039 s.
- [x] Suite final: 116 testes aprovados (113 existentes e 3 novos), sem falhas/ignorados, em 355,902 s.
- [x] Primeira regressao completa: 115 aprovaram e um timeout ao iniciar polling; corrigida recriacao de celulas inalteradas e repetida toda a suite.
- [x] Seleccao exclusiva na navegacao e nos transportes, inclusive ao clicar novamente no destino activo.
- [x] compileall, pip check e diff --check aprovados; segredos, bases locais, logs e capturas continuam ignorados.
- [x] Matriz final offscreen: sete ecras em 1440x900, 1120x740 e 860x600 logicos, escalas 100/125/150%; capturas em artifacts/stitch.
- [x] Verificador final por escala: 100% aprovado em 40,917 s; 125% em 39,062 s; 150% em 43,797 s, sem falhas/ignorados.
- [x] Capturas inspeccionadas em dimensoes normais/compactas e escalas diferentes; formulario IA sem sobreposicao e graficos com amostras OBD reais do cenario.
- [ ] Escalas fisicas Windows 100/125/150 em monitores distintos: nao executadas; matriz Qt offscreen em verificacao.
- [x] Nenhuma chamada real Gemini, commit, push ou alteracao de autoria nesta tarefa.

Sistema visual, fontes, licencas, adaptacoes e comandos em
[docs/SISTEMA_VISUAL.md](docs/SISTEMA_VISUAL.md). Resultados anteriores abaixo
sao historicos.

## Correccoes da revisao de 57c800e

- [x] Suporte desconhecido distinto de nao suportado, por ECU e modo 01/02; motivo e mapa em falta apresentados.
- [x] Apenas PIDs confirmados consultados; suporte anterior preservado e continuacao ausente conclusiva.
- [x] Freeze frame completo/parcial/sem dados utilizaveis/indisponivel/falha, sem sucesso por lista vazia.
- [x] Codigo isolado apresentado como parcial; respostas validas de outra ECU preservadas.
- [x] Estados e detalhes em interface, Historico, exportacao e fotografia Gemini.
- [x] Resposta atrasada identificada como sessao anterior, com cache/instantes; nova sessao guardada sem essa analise.
- [x] Historico compara no instante guardado usando equivalencia existente; quatro mensagens e registos antigos preservados.
- [x] 20 testes dedicados aprovados, sem ignorados, em 20,493 segundos; Qt, TCP controlado, SQLite temporario e Gemini simulado.
- [x] Regressao completa: 113 testes aprovados, sem falhas/ignorados, em 326,703 segundos em 11/10/2026 (93 existentes e 20 novos).
- [x] Janela Qt executada e capturas do Historico inspeccionadas; emuladores de teste em portas proprias, sem interferir com 35000.
- [x] compileall, pip check e diff --check aprovados; .env, .venv, logs, bases locais e capturas ignorados pelo Git.
- [x] Gemini exclusivamente simulado nesta correccao; dados locais e registos antigos preservados.
- [ ] Hardware fisico, Android e Gemini remoto: validacao externa, nao executada nesta correccao.

Roteiro e criterios em [docs/CORRECOES_REVISAO.md](docs/CORRECOES_REVISAO.md).
As seccoes seguintes registam validacoes historicas.

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

## Evolução: 12 PIDs, MIL, gráficos e fotografia IA

- [x] Repositório inicialmente limpo em main; instruções e versão actual inspeccionadas.
- [x] Registo extensível dos 12 PIDs com funções próprias, unidades e comprimentos exactos.
- [x] Fórmulas e monitores conferidos nas fontes primárias python-OBD; endereçamento no manual ELM327.
- [x] Descoberta 0100/0120/0140 por continuação de cada ECU, incluindo tensão no PID 42.
- [x] Pedidos só para PIDs anunciados; endereçamento físico CAN para subconjuntos, com restauração funcional.
- [x] Mapas incompletos não autorizam adivinhar suporte; payload inválido de uma ECU não invalida outra.
- [x] Selecção de PIDs, incluindo todos/iniciais; worker sequencial sem acumular ciclos.
- [x] Cenários saudável/P0301/múltiplas com 12 valores sintéticos; causa resolvida passa a saudável sem apagar códigos.
- [x] Freeze frame de 12 parâmetros, vector independente das leituras ao vivo.
- [x] MIL, contagem anunciada, motor e monitores suportados descodificados de 0101 pelo transporte OBD.
- [x] MIL apagada, não consultado, indisponível e falha continuam distintos; nenhuma leitura do painel injectada no scanner.
- [x] Gráficos QtCharts, hora local/unidade, série por ECU, lacunas e limite de 300 amostras por PID/ECU.
- [x] Parar conserva pontos; nova ligação/reposição limpa séries; Guardar conserva fotografia, não séries.
- [x] Captura/instante da resposta, idades, validade e avisos explícitos no pedido Gemini.
- [x] Resultado anterior conservado e marcado após mudanças; sem chamadas automáticas.
- [x] Cache v2 por estados/faixas temporais, TTL 300 s e apresentação do pedido/instante original.
- [x] Origem consistente, limites, esquema estrito e credenciais externas preservados.
- [x] Estados independentes do simulador, scanner e consultas; nomes portugueses e ajuda junto dos controlos.
- [x] Sessões antigas sem campos novos guardadas/abertas/exportadas sem alteração; sem migração SQL.
- [x] 12 testes novos aprovados em 26,315 s; TCP real do pacote 4.0.0, Gemini apenas simulado.
- [x] Primeira regressão completa: 89 testes aprovados, sem ignorados, em 258,718 s.
- [x] Execução final completa: 93 testes aprovados (81 existentes e 12 novos), sem falhas/ignorados, em 278,498 s, em 11/10/2026.
- [x] Janela efectivamente aberta e operada em testes Qt, callbacks e contador de responsividade.
- [x] Capturas finais 1120x740 e 860x600 inspeccionadas: dados/gráfico, avarias/MIL, IA e simulador.
- [x] Ajuste do intervalo inicial do eixo temporal e tipografia compacta; horas e unidades legíveis.
- [x] compileall, pip check e diff --check aprovados; nenhum ficheiro de site-packages alterado.
- [x] Instâncias de teste próprias em portas livres; simulador do utilizador, .env, ambientes e base local preservados.
- [x] Nenhum commit, push ou alteração de autoria nesta tarefa; HEAD mantém ab3ce82.
- [ ] Hardware USB/SPP, Android, ECU real, múltiplas ECUs físicas e Gemini remoto: validação externa pendente.
- [ ] Persistência de séries e modelo físico do motor: não implementados nesta evolução.

Roteiro exacto, referências, política da cache e limites:
[docs/EVOLUCAO_DIAGNOSTICO.md](docs/EVOLUCAO_DIAGNOSTICO.md).
As contagens acima distinguem a primeira execução, os testes dedicados
e a regressão final completa. Nenhuma chamada Gemini remota foi feita.
