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
- [x] Nenhuma chave real adicionada, nenhum .env sobrescrito, sem commits/publicacao.

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
- [ ] Chamada real Gemini com credencial de utilizador (nao efectuada nesta entrega).
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
