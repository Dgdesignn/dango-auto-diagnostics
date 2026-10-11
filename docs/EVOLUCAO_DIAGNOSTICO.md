# Evolução do diagnóstico

## Implementação e referências

O registo `diagnostics/obd.py` associa cada PID a comprimento, unidade e uma
função de descodificação. Implementação própria, sem copiar código externo.
Os comprimentos abaixo são só os bytes de dados, excluindo serviço/PID/frame.

| PID | Dados | Fórmula | Unidade |
|---|---:|---|---|
| 04 carga | 1 | A × 100 / 255 | % |
| 05 líquido | 1 | A - 40 | °C |
| 06 correcção curta B1 | 1 | (A - 128) × 100 / 128 | % |
| 07 correcção longa B1 | 1 | (A - 128) × 100 / 128 | % |
| 0B MAP | 1 | A | kPa absolutos |
| 0C RPM | 2 | (256A + B) / 4 | rpm |
| 0D velocidade | 1 | A | km/h |
| 0E avanço | 1 | A / 2 - 64 | ° |
| 0F admissão | 1 | A - 40 | °C |
| 10 MAF | 2 | (256A + B) / 100 | g/s |
| 11 borboleta | 1 | A × 100 / 255 | % |
| 42 módulo | 2 | (256A + B) / 1000 | V |

Referências primárias do projecto python-OBD, conferidas em 11/10/2026:
[comandos e comprimentos](https://github.com/brendan-w/python-OBD/blob/master/obd/commands.py),
[descodificadores](https://github.com/brendan-w/python-OBD/blob/master/obd/decoders.py),
[escalas de RPM/MAF/tensão](https://github.com/brendan-w/python-OBD/blob/master/obd/UnitsAndScaling.py)
e [monitores por tipo de ignição](https://github.com/brendan-w/python-OBD/blob/master/obd/codes.py).
São referências de implementação, não substituem a norma SAE J1979 licenciada.

`0101` tem quatro bytes: A indica MIL e contagem; B indica suporte/prontidão
dos três monitores contínuos e tipo de ignição; C/D indicam suporte/incompletude
dos monitores específicos desse motor. Bits reservados não geram monitores.
Contagem anunciada não substitui os códigos lidos em 03/07.

`services.py` segue continuação por ECU: bit de PID 20 no mapa 00, PID 40 no
mapa 20, PID 42 no mapa 40. Mapas falhados não autorizam adivinhar suporte.
Quando todas as ECUs anunciam um PID, usa pedido funcional; para um subconjunto,
usa endereçamento CAN físico e restaura o funcional. Ver
[manual ELM327, endereçamento e cabeçalhos](https://www.elmelectronics.com/wp-content/uploads/2016/07/ELM327DS.pdf),
secção “Setting the Headers”, páginas 38–41. IDs padrão 7E8–7EF e 18DAF1xx
são reconhecidos. Endereçamento individual de outros protocolos não é inferido:
num subconjunto não endereçável o pedido é recusado com motivo explícito.

Pedidos permanecem sequenciais num worker; um tick enquanto ocupado é descartado,
não enfileirado. Por defeito mantém os três PIDs anteriores. Seleccionar mais
PIDs aumenta a duração de um ciclo, que pode exceder o intervalo escolhido.

## Valores sintéticos

`scenarios/vehicle.py` permanece externo ao ELM327-emulator 4.0.0. Não altera
o pacote nem instala o scanner no ambiente do emulador. Os cenários modelados
anunciam `9E3F8001 / 00000001 / 40000000` no modo 01. O modo 02 usa
`5E3F8001 / 00000001 / 40000000`, incluindo o código associado no PID 02.

Valores aproximados após quantização OBD:

| Grandeza | Saudável/resolvido | P0301 activo | Múltiplas activas | Freeze próprio |
|---|---:|---:|---:|---:|
| Carga % | 18,04 | 25,10 | 25,10 | 21,96 |
| Líquido °C | 88 | 88 | 88 | 88 |
| STFT % | 1,5625 | 7,8125 | 25 | 15,625 |
| LTFT % | 0,78125 | 4,6875 | 18,75 | 6,25 |
| MAP kPa | 34 | 50 | 50 | 47 |
| RPM | 750 | 740/680/820/710/790 | mesma sequência | 710 |
| Velocidade km/h | 0 | 0 | 0 | 0 |
| Avanço ° | 12 | 4 | 4 | 5 |
| Admissão °C | 35 | 35 | 35 | 33 |
| MAF g/s | 2,60 | 3,50 | 3,50 | 3,30 |
| Borboleta % | 3,92 | 5,10 | 5,10 | 4,31 |
| Módulo V | 14,2 | 14,2 | 14,2 | 14,0 |

Os valores são vectores de teste plausíveis para um motor quente parado, não um
modelo físico validado, nem uma relação causal universal com P0301. Freeze frame
é um vector independente predefinido, não cópia das últimas leituras. A causa
resolvida passa as leituras para saudável, preservando códigos/MIL/freeze até 04.
Só o monitor de combustão é modelado. Limpar deixa-o incompleto; um ciclo conclui-o,
mas inicialmente produz apenas pendentes; o segundo confirma e acende MIL.
`no_data`, perda de ligação e `car` original conservam os limites anteriores.
O cenário car não é ampliado artificialmente: depende das respostas do pacote.

## Gráficos e sessões

`ReadingSeries` conserva até 300 tentativas por PID/ECU numa fila limitada.
Só uma nova resposta válida produz um valor. Falhas produzem `None`, nunca zero;
o gráfico usa segmentos separados. Paragens e deselecção quebram a linha quando
há nova amostra. Parar conserva todos os pontos existentes; ligar/repor inicia
uma sessão e elimina as séries anteriores. Não há interpolação de valores ausentes.
`ui/charts.py` usa QtCharts do PySide6 instalado (6.12.0), sem dependência nova.
Um PID/unidade por gráfico, ECUs diferenciadas por linha/legenda, hora local.

SQLite continua a guardar fotografias JSON, não séries. Novos campos são opcionais
na abertura; registos antigos permanecem intactos. Não há migração SQL nem alteração
de origem automática. Registos antigos sem MIL/instantes não ganham valores inventados.

## Fotografia Gemini e cache

O pedido é uma cópia independente dos dados, com captura UTC, estado de ligação,
idade em segundos e classificação por leitura. “Recente” exige valor disponível,
instante conhecido, ligação activa e ausência de flag desactualizada. A janela usa
limiar `max(10, intervalo × 3)` segundos; a API interna usa 10 por defeito. Valores
não consultados, não suportados, indisponíveis e falhados são classificados separadamente.
Freeze frame permanece histórico, não uma leitura actual. Avisos identificam falta
de leituras recentes ou de ambas as consultas de códigos concluídas.

A cache v2 inclui modelo, instrução, valores, estados, sintomas e faixas temporais:
recente / até 60 s / até 300 s / mais de 300 s / instante desconhecido.
Idades exactas e timestamps brutos não fazem chamadas a cada segundo; transições
de faixa/validade alteram a equivalência. TTL de resposta: 300 s. Uma fotografia
nova equivalente pode reutilizar a resposta, mas são apresentados a captura,
pedido e instante de resposta originais. Cache antiga v1 não é reutilizada.

A comparação da interface usa os mesmos dados relevantes e a identidade local da
sessão, sem enviar esse identificador à API. Sintomas/códigos/MIL/ligação/valores
ou validade diferentes assinalam “Dados alterados desde esta análise”. O resultado
continua visível; uma ligação nova não o associa à nova sessão. Não há chamadas
automáticas, nem quando ciclos ou polling mudam dados. Limites e esquema estrito
mantidos; credenciais só no ambiente/.env ignorado. Testes nunca chamam a rede Gemini.

## Roteiro exacto na interface

```powershell
cd C:\Py\scanner_outo
.\.venv\Scripts\python.exe scripts\run_app.py
```

1. Em Simulador local, escolha **Ralenti irregular | P0301** e uma porta livre,
   por exemplo 35000 se não estiver ocupada. Clique **Iniciar simulador**.
2. Em Ligação, escolha TCP, Emulador / simulação, 127.0.0.1 e a mesma porta;
   clique **Ligar**. Iniciar o simulador não liga o scanner.
3. Em Dados > Parâmetros, marque os 12. Clique **Iniciar actualização**.
   Na tabela verifique unidades, zeros reais de velocidade e variação de RPM.
4. Abra Gráfico e escolha RPM, MAF ou tensão. Mude de PID: a unidade do eixo muda.
   Clique Parar: pontos permanecem, leituras ficam desactualizadas, simulador continua.
5. Em Avarias, Consulte avarias: P0301 confirmado, MIL acesa, contagem 1 e monitor
   de combustão concluído. Consulte freeze frame: 12 valores próprios, 710 rpm/14 V.
6. Limpe registos e confirme: fotografia anterior guardada, códigos vazios, MIL
   apagada, monitor incompleto e freeze indisponível ao voltar a consultá-lo.
7. No simulador, Novo ciclo; depois Consulte avarias: P0301 pendente, MIL apagada.
   Outro ciclo + consulta: confirmado/MIL acesa. Ciclo não actualiza a tabela sozinho.
8. Resolver causa deixa códigos/MIL antigos; actualizar Dados mostra 750 rpm e valores
   saudáveis. Limpar depois de resolver e avançar ciclos não recria o código.
9. Na IA, informe “Motor treme ao ralenti”. Faça uma leitura recente e consulte códigos;
   Rever dados mostra origem, captura, validade e sintomas. O botão Analisar com Gemini
   é a única chamada remota explícita e pode consumir quota. Sem chave, veja o motivo.
10. Após obter uma resposta, mude sintomas ou pare consultas: aparece o aviso de dados
    alterados, sem chamada automática. Repetir fotografia equivalente dentro do TTL
    usa cache e apresenta instante original. Guardar/Abrir/Exportar conserva a fotografia.
11. Repor cenário pede confirmação e desliga a sessão gerida; ligar de novo começa
    gráficos vazios. Um servidor externo não é encerrado pela janela.

Alternativa manual do simulador, em terminal separado e porta livre:

```powershell
cd C:\Py\scanner_outo
.\.venv\Scripts\python.exe scripts\run_emulator.py --scenario rough_idle_p0301 --port 35000
```

O launcher descobre `C:\Py\simulador_scanner\.venv`; não é preciso activá-lo
no terminal da aplicação. Para saudável use `--scenario healthy`; múltiplas:
`--scenario multiple_dtcs`; sem dados: `--scenario no_data`; perda:
`--scenario connection_loss --loss-after-requests 6`. Este último permite três
mapas de descoberta e um ciclo dos três PIDs iniciais; o pedido seguinte cai.
Para os 12 num ciclo, escolha pelo menos 15 pedidos antes da perda.

## Testes

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_evolution.py -v
.\.venv\Scripts\python.exe -m compileall -q src scenarios scripts tests
.\.venv\Scripts\python.exe -m pip check
```

Instâncias próprias em portas livres, SQLite temporário e Gemini simulado.
Não use o teste `--real` contra a porta do utilizador para executar esta suite.
Capturas de Dados/Avarias/IA/Simulador em 1120x740 e 860x600 ficam em artifacts/,
ignoradas pelo Git. Resultados efectivamente obtidos estão no CHECKLIST.
Limites externos: hardware USB/SPP/Android, ECU real, protocolos desconhecidos,
comportamento de múltiplas ECUs físicas e Gemini remoto não validados nesta tarefa.
