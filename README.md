# Scanner Outo

Aplicacao desktop de diagnostico automovel de Daniel Geraldo, em Python/PySide6. Esta fase implementa OBD-II generico com ELM327 e analise opcional por Gemini. Nao necessita de chave Gemini para ligar, consultar dados ou guardar sessoes.

## Abrir no ambiente actual

No PowerShell:

```powershell
cd C:\Py\scanner_outo
.\.venv\Scripts\python.exe scripts\run_app.py
```

Na janela, seleccione `TCP`, origem `Emulador / simulacao`, host `127.0.0.1` e porta `35000`, e clique em `Ligar`. Em `Dados`, use `Consultar agora` ou `Iniciar actualizacao`. O intervalo inicial e 3 segundos; pedidos sao sequenciais e nao se acumulam quando uma consulta demora.

## Instalar no Windows

O ambiente foi executado com Python 3.13.15 de 64 bits, PySide6 6.12.0 e pyserial 3.5. A integracao Gemini foi testada com cliente simulado e SDK google-genai 2.29.0 instalado.

Para preparar outro checkout:

```powershell
cd C:\Py\scanner_outo
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
# Opcional, para chamadas Gemini:
.\.venv\Scripts\python.exe -m pip install -e ".[gemini]"
.\.venv\Scripts\python.exe -m scanner_outo
```

A instalacao necessita de acesso ao PyPI. No ambiente actual, o pacote ja foi instalado de forma editavel. Tambem existe `.\.venv\Scripts\scanner-outo.exe`.

## Emulador separado

Abra um terminal separado e mantenha-o aberto:

```powershell
cd C:\Py\simulador_scanner
.\.venv\Scripts\python.exe -m elm -s car -n 35000 -i 127.0.0.1
```

O emulador existente e v4.0.0. A aplicacao principal nao instala nem altera esse ambiente. A opcao `-i` limita esta ligacao ao computador local. Nao abra duas instancias na mesma porta.

O teste de terminal continua disponivel:

```powershell
cd C:\Py\scanner_outo
.\.venv\Scripts\python.exe scripts\test_elm327_tcp.py
```

## TCP Android, USB e Bluetooth

- Android: inicie o servidor ELM compativel no telefone, ligue ambos os dispositivos a mesma rede e configure na janela o IP do telefone e a porta anunciada pelo simulador. `127.0.0.1` refere-se ao computador, nao ao telefone. Seleccione origem de simulacao. TCP Android ainda precisa de validacao com o dispositivo.
- USB serial: instale o driver do adaptador, seleccione `Serial USB`, a porta COM listada e o baud rate indicado pelo fabricante. Existe um botao para actualizar as portas.
- Bluetooth: emparelhe o adaptador Classic SPP nas definicoes do Windows e identifique a porta COM de saida. Seleccione `Bluetooth SPP` e essa porta. Sem uma porta COM SPP disponivel, este modo nao pode estabelecer ligacao. BLE nao esta implementado.

O meio de transporte nao determina a origem: seleccione explicitamente `Veiculo real` quando utilizar hardware num automovel. A limpeza fica bloqueada nesse modo nesta fase.

## Dados e avarias

A aplicacao consulta suporte pelo PID 0100 e apresenta RPM, temperatura do liquido de arrefecimento e velocidade, separados por ECU. Cada leitura mostra unidade, instante local e disponibilidade. Valores ausentes sao `--`; o ultimo valor valido pode permanecer com estado `Sem dados`, `Erro de resposta` ou `Desactualizado`. Zero so e apresentado quando recebido e descodificado como zero.

Em `Avarias`, pode consultar os modos 03/07 e o freeze frame 0 do modo 02, quando houver respostas. A tabela de descricoes e pequena: para codigos fora da tabela e apresentada `Descricao nao disponivel`. Uma consulta falhada ou NO DATA nao significa que nao existam avarias. O cenario `car` validado devolveu respostas sem codigos confirmados/pendentes e `NO DATA` para freeze frame.

`Limpar na simulacao` primeiro guarda uma fotografia dos dados/codigos disponiveis e pede confirmacao. Limpar registos nao repara a causa. E necessaria uma resposta 44 e releitura coerente para confirmar a limpeza. O cenario pode nao suportar o comando, ou continuar a devolver codigos. Nenhum teste envia automaticamente o comando 04.

## Gemini e consumo

O SDK oficial e `google-genai`, conforme [documentacao oficial](https://github.com/googleapis/python-genai). O modelo inicial configuravel e [Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash); a disponibilidade real depende da API/conta.

Defina `GEMINI_API_KEY` no ambiente, ou no `.env` local existente. Nao sobrescreva o seu `.env`. `.env.example` contem apenas valores ficticios. O ficheiro real e ignorado pelo Git. Tambem e aceite `GOOGLE_API_KEY`, se a chave Gemini nao estiver definida. A chave nao e apresentada na janela nem nas mensagens de erro.

Configuracoes opcionais:

```dotenv
GEMINI_MODEL=gemini-2.5-flash
GEMINI_DAILY_LIMIT=10
GEMINI_MIN_INTERVAL=30
```

O modelo, limite diario e intervalo minimo tambem podem ser ajustados na interface durante a sessao. Para persistir esses valores, configure-os no ambiente/.env. Um limite diario zero bloqueia novas chamadas, mantendo a cache utilizavel.

Apenas `Analisar com Gemini` envia dados. `Rever dados` mostra o retrato JSON. O pedido omite configuracao de ligacao, VIN e identificadores pessoais estruturados; remova informacao pessoal introduzida nos sintomas antes de enviar. Limites: 4000 caracteres de sintomas, 24 KiB de entrada normal, 4096 tokens de saida e timeout HTTP de 20 segundos, sem repeticao automatica.

A resposta distingue factos, hipoteses, evidencias, informacao em falta e proximos testes. Nao controla componentes nem pode limpar codigos. Resultados equivalentes usam cache SQLite. As tentativas falhadas tambem contam para o limite local; o dia e contado em UTC e o intervalo persiste entre arranques. Esses limites nao garantem um tecto financeiro da conta Google. Tokens sao mostrados quando informados pela API; a cache mostra a contagem da chamada original.

## Historico e ficheiros locais

`Guardar sessao` guarda data, origem, estados, parametros, codigos, freeze frame, sintomas e analise com a fotografia enviada. O historico permite abrir um retrato separado e exportar JSON. Sessoes, cache e contagens locais ficam em `data/sessions.sqlite3`; pedidos/respostas ELM ficam em `data/scanner.log`, com rotacao. Estas pastas estao ignoradas no Git. `SCANNER_DATA_DIR` permite mudar a pasta de dados.

Ao fechar durante uma operacao, a janela aguarda o pedido em curso, cancela os proximos pedidos OBD e fecha sockets/portas. Um pedido Gemini em curso termina pelo seu timeout; nao e interrompido brutalmente.

## Testes e validacao

```powershell
cd C:\Py\scanner_outo
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
# Com o ELM327-emulator ligado:
.\.venv\Scripts\python.exe scripts\verify_gui.py --real
```

A suite usa servidores TCP e portas serial substitutos, SQLite temporario e Gemini simulado. Inclui testes Qt com a janela efectivamente aberta, workers, historico e capturas em `artifacts/`. O teste `--real` faz apenas leituras ao emulador local; a parte de cancelamento controlado e ignorada nessa execucao. Os resultados aprovados e pendentes estao em [CHECKLIST.md](CHECKLIST.md).

## Arquitectura e limites

A explicacao de cada camada esta em [docs/IMPLEMENTACAO.md](docs/IMPLEMENTACAO.md): UI, workers, servicos, transportes, ELM, OBD, Gemini, modelos, configuracao e persistencia.

Ainda exigem validacao real: USB serial, Bluetooth SPP, simulador Android e chamadas Gemini com uma chave de utilizador. A limpeza esta implementada, mas o seu efeito no cenario real nao foi testado. Freeze frame funcional foi validado com respostas controladas; o cenario instalado nao o disponibilizou.

Esta fase nao inclui BLE, suporte universal a marcas, UDS completo, ISO-TP bruto, firmware, programacao de ECU, testes de actuadores, aplicacao movel ou previsao fiavel de avarias futuras. Formatos de resposta desconhecidos produzem erro explicito. Nao foram feitos commits nem publicado o projecto.
