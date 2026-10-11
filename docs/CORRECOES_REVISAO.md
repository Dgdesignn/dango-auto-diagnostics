# Correccoes da revisao de diagnostico

Revisao da base `57c800e`, mantendo transportes, 12 PIDs, graficos, MIL,
simulador externo e ambientes separados. Nenhum ficheiro de site-packages,
credencial ou base de dados existente foi alterado.

## Suporte por ECU e servico

`DiagnosticService.support_state()` percorre os mapas necessarios e os seus
indicadores de continuacao. Cada mapa recebido conserva os PIDs anunciados.
Nao suportado exige uma resposta valida sem o PID, ou uma continuacao
explicitamente ausente. Se 0120 falhar, o PID 42 fica com suporte nao confirmado,
identificando 0120 e o motivo. O mesmo vale para 022000 no freeze frame 0.

Os registos dos modos 01 e 02 permanecem independentes. PIDs confirmados em
mapas anteriores continuam consultaveis; PIDs desconhecidos nao sao pedidos.
Falhas de uma ECU nao retiram suporte confirmado de outra. A consulta do codigo
associado 020200 tambem exige que o mapa anuncie o PID 02.

## Freeze frame

Estados agregados e por ECU:

| Estado apresentado | Criterio |
|---|---|
| Consulta concluida | Leituras utilizaveis e todos os pedidos aplicaveis concluidos, sem mapas em falta |
| Consulta parcial | Algum dado utilizavel, mas faltam campos/mapas/pedidos; apenas codigo associado tambem e parcial |
| Sem dados utilizaveis | Respostas validas, incluindo mapas, sem leituras nem codigo utilizaveis |
| Indisponivel | Consulta inicial responde NO DATA, sem respostas utilizaveis |
| Falha de consulta | Transporte interrompido ou resposta invalida, sem dados utilizaveis |

Uma consulta individual que responde NO DATA permanece Indisponivel. Se o mapa
foi recebido mas nenhum parametro pode ser utilizado, o conjunto e Sem dados
utilizaveis; nao e uma consulta completa. Uma resposta valida sem PIDs
reconhecidos nao prova ausencia de freeze frame no veiculo.

`freeze_ecus` conserva estado, motivo, instante e estado da consulta do codigo
por ECU. `freeze_detail`, codigos e detalhes de cada leitura aparecem na janela
e no Historico e seguem no JSON guardado/exportado e na fotografia Gemini.
Uma interrupcao preserva os valores/codigos ja recebidos e identifica a consulta
incompleta. O frame 0 e historico, nao uma leitura actual do motor.

## Analise e Historico

Se a ligacao mudar durante uma chamada, a resposta continua visivel como
analise da sessao anterior, juntamente com cache e instantes originais.
Nao e associada nem guardada na nova sessao. Nenhuma mudanca provoca chamadas.

Novas fotografias guardadas incluem `captured_at` UTC. Ao abrir, a funcao
`saved_analysis_correspondence()` reconstroi os dados no instante dessa captura
e aplica a mesma equivalencia usada pela cache (valores, estados, sintomas e
faixas de idade). A hora de abertura nao volta a envelhecer as leituras.

A janela apresenta uma das quatro mensagens:

- Analise corresponde a fotografia guardada.
- Dados da sessao diferem dos usados nesta analise.
- Correspondencia nao verificavel.
- Sem analise guardada.

Registos antigos sem captura ou dados suficientes continuam legiveis e
exportaveis, mas a correspondencia nao e verificavel. Nao existe migracao SQL,
reescrita automatica ou alteracao dos dados/instantes enviados anteriormente.

## Testes reproduziveis

No PowerShell, a partir de `C:\Py\scanner_outo`:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_review_regressions.py -v
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

Os 20 testes dedicados usam adaptadores TCP controlados, SQLite temporario e
Gemini simulado. Cobrem mapas falhados/validos/sem continuacao, multiplas ECUs,
modo 02, freeze vazio/apenas codigo/parcial/completo/interrompido, exportacao,
resposta atrasada apos reconexao (incluindo cache), nova sessao sem analise
antiga e as quatro mensagens do Historico. A janela Qt e efectivamente aberta.
Capturas `artifacts/review-history-*.png` sao ignoradas pelo Git.
Resultados efectivamente obtidos estao no [CHECKLIST](../CHECKLIST.md).

## Validacao manual curta

```powershell
.\.venv\Scripts\python.exe scripts\run_app.py
```

1. Inicie Ralenti irregular | P0301 no painel local numa porta livre; ligue por
   TCP a 127.0.0.1 nessa porta, origem Emulador / simulacao. Nao termine um
   emulador externo que ja esteja em execucao.
2. Actualize Dados e consulte avarias e freeze frame. Confirme P0301, leituras,
   estado e detalhes. Guarde, abra e exporte a sessao; sem analise, o Historico
   deve indicar Sem analise guardada.
3. Para os casos de mapas falhados, freeze vazio e resposta atrasada, execute
   os testes dedicados acima. Esses casos sao respostas do adaptador de teste,
   nao comandos inventados de configuracao do ELM327.
4. Com uma analise ja disponivel, guardar sem mudar os dados deve corresponder
   quando a fotografia continua equivalente. Mudar sintomas ou validade antes
   de guardar deve indicar divergencia. Abrir mais tarde nao a cria por si so.

O botao Analisar com Gemini continua disponivel para uma chamada real explicita,
que pode consumir quota. Nao e necessario usa-lo para os testes acima.

## Limites

Hardware USB/SPP, Android, ECU fisica e Gemini remoto nao foram validados nesta
correccao. O modelo de avarias e sintetico e apenas o freeze frame 0 e consultado.
Sem metadados antigos suficientes nao e possivel provar correspondencia.
As faixas temporais existentes mantem-se: passagem de faixa entre analise e
gravar pode correctamente produzir divergencia, mesmo com valores iguais.
