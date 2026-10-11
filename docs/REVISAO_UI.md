# Revisão da interface

## Origem das sessões

Na base existente, os registos 2 e 3 contêm `simulation=false` tanto na sessão como na configuração TCP capturada; o host é `127.0.0.1`. Não foi encontrada uma conversão de uma sessão marcada como emulador para veículo real durante a gravação. Estes dados são consistentes com uma ligação configurada como real, mas não permitem provar a origem física: TCP local também pode encaminhar um adaptador. O tema anterior podia tornar a seleção ilegível. Não é possível reconstruir a seleção feita pelo utilizador a partir destas informações.

Os registos foram preservados. O histórico assinala `TCP local: confirmar origem`, sem reclassificar ou alterar JSON antigo. A grafia apresentada de rótulos históricos foi normalizada apenas na vista.

A seleção da origem agora associa um booleano explícito a cada opção, sem usar o índice. Esse valor é capturado no início da ligação; `session_origin` valida a consistência com a configuração capturada. A mesma regra fornece o cabeçalho, a origem guardada no SQLite e os dados enviados ao Gemini. JSON mantém `simulation` e `connection.simulation` coerentes. A gravação e análise recusam contradições. Configurar TCP local como veículo real exige uma confirmação na janela, sem deduzir a origem pelo IP.

## Visibilidade e estados

O tema anterior definia fundos claros, mas deixava cores de texto, controlos desactivados e seleções parcialmente dependentes do tema Windows. A revisão aplica Fusion e cores explícitas à paleta e stylesheet. Os botões, inputs, tabelas, listas, tabs e tooltips têm texto e fundo definidos, incluindo estados desactivados, seleccionados e em foco. Os contrastes escolhidos são testados: 4,5:1 para texto normal/desactivado/seleccionado e 3:1 para o indicador de foco.

Todos os comandos pedidos têm ícone e texto. Também foram corrigidos os acentos, as descrições e os títulos da análise Gemini; a temperatura é descodificada e apresentada em °C.

As consultas de avarias mostram explicitamente `Não consultado`, `Consulta em curso`, `Nenhum código devolvido`, `Consulta concluída` quando há códigos, `Indisponível` para NO DATA e `Falha de consulta` para respostas inválidas ou falhas de transporte. Nenhum código devolvido significa uma resposta válida vazia, não ausência de resposta nem garantia de ausência de avarias no veículo. O freeze frame tem disponibilidade e detalhe separados.

Parar o polling marca imediatamente as últimas medições como desactualizadas, mesmo quando um pedido em curso termina depois. Nova leitura explícita ou início do polling pode voltar a fornecer valores actuais. A desconexão também marca as leituras; falhas preservam o último valor com o motivo e flag `stale`. A fotografia usada no histórico, exportação e Gemini inclui esses estados. Nunca se inventa zero para ausência de dados.

## Gemini

Modelo, limite diário e intervalo mínimo são campos legíveis com os valores efectivos. Uma linha própria apresenta falta de chave, modelo vazio, limite zero ou SDK ausente; falhas remotas aparecem separadamente. A chave não é mostrada. O botão continua a permitir consulta da cache, que pode estar disponível mesmo sem uma nova chamada autorizada pelo limite local.

Foram usados clientes simulados para testar sucesso, falhas, quota, cache, limites, contagem de tokens e apresentação na janela. Não houve chamada real à API nesta revisão. A chave enviada na conversa não foi escrita em ficheiros, logs ou Git nem enviada à API. A validação real fica pendente de uma nova credencial configurada localmente.

## Validação executada

- `python -m unittest discover -s tests -q`: 51 testes aprovados.
- `python scripts/verify_gui.py --real`: 8 testes aprovados e 4 ignorados de forma explícita; as falhas controladas e confirmação de limpeza são exercitadas na suite simulada.
- Janela efectivamente aberta: ligação ao ELM327, leitura de RPM/temperatura/velocidade, modos 03/07, guardar/abrir sessão, exportação JSON, polling, parar e desligar/religar.
- Emulador devolveu respostas válidas sem códigos confirmados/pendentes e NO DATA para freeze frame. Não foi enviado comando 04; o emulador do utilizador não foi encerrado.
- Capturas Qt em 1120x740 e 860x600 unidades lógicas, incluindo seleção, controlos desactivados e foco, revistas visualmente para Dados, Avarias, IA e Histórico.
- `compileall` e `pip check` aprovados.

Pendente: confirmação dos registos antigos assinalados, chamada Gemini real, hardware USB/Bluetooth/Android e efeito de limpeza num cenário que o suporte. Nenhum novo commit ou publicação foi realizado nesta revisão.
