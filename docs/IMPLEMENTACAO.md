# Implementacao da primeira fase

## Configuracao e arranque

`config.py` le o ambiente e o `.env` na raiz do projecto sem substituir valores ja definidos no ambiente. A chave nao aparece no `repr` da configuracao. O arranque configura apenas o logger do projecto, com rotacao de ficheiros em `data/`. Nunca sao registados pedidos Gemini, sintomas ou chaves.

`__main__.py` cria o QApplication e a janela. `scripts/run_app.py` permite iniciar directamente a partir do checkout, sem depender da instalacao editavel. A configuracao invalida produz uma mensagem generica que nao revela valores do ambiente.

## Transportes

`communication/base.py` define o contrato comum e distingue timeout de desconexao. `tcp.py` envia comandos terminados com CR, acumula fragmentos ate ao prompt `>`, limita a resposta a 64 KiB e aplica um prazo total por pedido. Um timeout fecha a ligacao: uma resposta atrasada nao pode ser interpretada como resposta ao pedido seguinte.

`serial_transport.py` usa pyserial, lista portas e aplica o mesmo terminador, limite e prazo. `bluetooth.py` reutiliza este transporte para uma porta COM de Bluetooth Classic SPP criada pelo Windows. Nao abre sockets BLE nem efectua emparelhamento automaticamente. Os testes de serial/SPP usam substitutos controlados, sem alegar validacao fisica.

## Cliente ELM e OBD

`diagnostics/elm327.py` serializa comandos, verifica as confirmacoes de inicializacao e regista apenas pedidos/respostas ELM. O teste de terminal continua a usar ATH0. A aplicacao activa ATH1 para identificar ECUs.

`diagnostics/obd.py` trata eco, linhas, prompt, SEARCHING, NO DATA e erros explicitos. Mantem cada ECU separada e valida servico, PID e comprimento antes de calcular valores. Suporta respostas sem cabecalho, CAN de 11/29 bits com cabecalho separado e mensagens CAN fragmentadas formatadas pelo ELM, verificando a sequencia por ECU. Isto nao constitui uma implementacao de ISO-TP bruto ou UDS. Formatos desconhecidos sao recusados, nunca adivinhados.

Formulas: RPM = (256*A+B)/4; temperatura = A-40 C; velocidade = A km/h. O mapa 0100 identifica quais destes PIDs cada ECU anuncia. Os modos 03/07 descodificam codigos confirmados/pendentes; aceita-se tambem o campo de contagem CAN. Existe uma pequena tabela local de descricoes genericas. Codigos desconhecidos mostram `Descricao nao disponivel`.

O freeze frame usa o modo 02, frame 0: mapa de suporte, codigo associado e os tres parametros desta fase. Sem dados ou resposta invalida nao sao convertidos em zero nem tratados como ausencia de avarias.

## Servico de diagnostico

`services.py` gere a ligacao e o estado da sessao. A porta TCP e o host sao configuraveis para o simulador Android. Uma fila de trabalho diagnostico impede pedidos concorrentes; o evento de cancelamento e verificado entre comandos.

As leituras guardam valor, unidade, ECU, instante, disponibilidade e detalhe. Uma consulta sem dados preserva a ultima medicao com estado de falha. Uma desconexao marca valores anteriores como desactualizados. A janela tambem marca leituras com mais de max(10 segundos, 3 intervalos) como desactualizadas.

A limpeza esta bloqueada para veiculo real. Na interface, antes do comando 04, sao consultados os dados disponiveis e guardada uma sessao SQLite. Depois e solicitada confirmacao. A resposta 44 e obrigatoria; os modos 03/07 sao consultados novamente e so e apresentada limpeza confirmada se nao persistirem codigos e as ECUs que confirmaram voltarem a responder. Dados de freeze frame anteriores sao invalidados. Falhas de consulta, NO DATA e codigos que persistem ficam explicitos.

## Gemini

`gemini.py` utiliza o SDK oficial `google-genai` e `models.generate_content`, com schema Pydantic, timeout HTTP, uma tentativa e limite de 4096 tokens de saida. O modelo e configuravel. Referencias consultadas: [SDK oficial](https://github.com/googleapis/python-genai) e [Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash).

So o botao de analise chama a API. O pedido recebe uma fotografia com origem, estados, unidades, codigos, freeze frame e sintomas. Nao inclui configuracao da ligacao, VIN, identificadores de utilizador ou logs. O utilizador pode rever o JSON; texto pessoal introduzido nos sintomas faz parte do pedido, por isso deve ser removido pelo utilizador antes do envio. Ha limites de 4000 caracteres de sintomas e 24 KiB no retrato normal.

A resposta separa factos medidos, hipoteses, evidencias, informacao em falta e proximos testes. O schema rejeita campos extra e conteudo invalido. Nenhuma resposta pode executar operacoes de diagnostico. Os erros do SDK sao convertidos em mensagens controladas sem incluir o texto original, que poderia conter credenciais.

O SQLite guarda resultados em cache pelo modelo, instrucao, sintomas, valores e estados. Instantes de leituras equivalentes nao obrigam a repetir a chamada. Pedidos aceites, incluindo tentativas falhadas, contam para um limite diario UTC; a reserva e atomica e o intervalo persiste entre arranques. Estes limites locais nao garantem um limite financeiro na conta Google. Os tokens sao apresentados apenas quando informados pela API; resultados em cache identificam que a contagem pertence a chamada original.

## Interface e persistencia

`ui/main_window.py` apresenta cinco separadores: Ligacao, Dados, Avarias, Analise por IA e Historico. Os estados do adaptador e da ECU sao independentes. Configuracoes de transporte/origem ficam bloqueadas durante a ligacao. A janela permite desligar, cancelar polling e manter-se utilizavel durante pedidos.

`ui/workers.py` executa operacoes fora da thread da interface, e os sinais sao entregues por ligacoes Qt enfileiradas. Uma fila gere OBD; outra gere Gemini e operacoes de historico. Fechar a janela cancela os proximos comandos e aguarda a conclusao dos workers; Gemini termina pelo timeout configurado. Sockets e portas sao fechados antes de sair.

`models.py` define os modelos de ligacao, leitura, avaria e sessao. `persistence.py` guarda fotografias completas em SQLite e exporta JSON. Cada operacao usa uma ligacao SQLite propria, com transaccao e fecho garantido. Abrir uma sessao anterior mostra um retrato separado, sem substituir a ligacao activa.
