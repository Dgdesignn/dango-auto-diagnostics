# Sistema visual DANGO

## Referencia inspeccionada

Foram inspeccionados os HTML e PNG de `design/stitch`: Visao geral, Conexao,
Diagnostico DTC, Dados ao vivo, Analise com IA, Historico, Simulador e Sistema
de Design. Nenhum desses ecraes esta em falta. O HTML adicional da plataforma
e o manual `workshop_diagnostic_utility/DESIGN.md` tambem estao disponiveis.

O projecto Stitch nao foi acessivel pelo navegador; a implementacao usa as
exportacoes locais fornecidas. As imagens exportadas incluem zonas vazias e
dados ficticios: a aplicacao preenche apenas com estados e respostas existentes.

## Tecnologia e recursos offline

Python 3.13.15, PySide6 6.12.0, Qt Widgets, QPalette/QSS, QtCharts, QtSvg e
QFontDatabase, ja instalados. Nao foi adicionada uma dependencia nem usado
QWebEngine, React, Electron, HTML executavel ou CDN em runtime.

`ui/assets/fonts/Inter.ttf` e `JetBrainsMono.ttf` sao fontes variaveis locais.
Inter serve navegacao, titulos, sintomas e controlos; JetBrains Mono serve
valores, DTCs, ECUs, eixos e JSON tecnico. QFontDatabase carrega-as no arranque.
Os tamanhos sao pixels logicos, com espacamento de letras zero.

Fontes provenientes do [repositorio Google Fonts](https://github.com/google/fonts),
pastas `ofl/inter` e `ofl/jetbrainsmono`; licenca SIL Open Font License 1.1,
incluida em `Inter-OFL.txt` e `JetBrainsMono-OFL.txt`. Icones Material Icons
Outlined provenientes de [Google Material Design Icons](https://github.com/google/material-design-icons),
licenca Apache 2.0 em `ui/assets/icons/LICENSE.txt`. Sao SVG oficiais renderizados
por QtSvg e coloridos localmente. `check.svg` foi adaptado apenas para preencher
a marca a branco. As licencas e recursos sao incluidos pelo package-data.

## Tokens

`ui/design.py` centraliza as cores, espacamentos, escala tipografica e recursos:

| Uso | Cor |
|---|---|
| Accao / hover profundo | #0F766E / #005C55 |
| Barra lateral | #213145 |
| Canvas / trabalho secundario | #F8F9FF / #EFF4FF |
| Cartao / superficie / seleccao | #FFFFFF / #E5EEFF / #DCE9FF |
| Texto / secundario / neutro | #0B1C30 / #3E4947 / #64748B |
| Contorno / sucesso no escuro | #BDC9C6 / #9CF2E8 |
| Aviso | #9C573A |
| Erro fundo / texto / destrutivo | #FFDAD6 / #93000A / #BA1A1A |

Titulo 28 px, seccao 20 px, subtitulo 16 px, corpo/tabela 13 px, secundario
12 px, tecnico 11 px e leitura destacada 20 px. Pesos 400/600; valores em
tabela usam fonte monoespacada. Espacamentos 4/8/16/24/32 px; botoes de
referencia 36 px. Curvas de 4 px em controlos/badges e 8 px em ferramentas
e leituras, conforme o HTML, sem aplicar 10 px indiscriminadamente.

## Componentes e organizacao

- `ui/shell.py`: barra lateral de 260 px, navegacao de sete destinos, estado e
  desligar; modo compacto de 72 px com icones, nomes acessiveis e tooltips.
- Cabecalho persistente: origem, scanner, simulador, consultas, ECU, tensao do
  modulo PID 42 e MIL. Em largura compacta passa a duas linhas.
- `ui/components.py`: Panel, ReadingCard, Badge, Columns, TechnicalSection e
  PageStack com QStackedWidget e QScrollArea.
- `ui/screens/`: overview, connection, diagnostics, live_data, analysis e
  history. O ecra de simulacao permanece em `ui/simulator.py`, junto da
  gestao Qt do processo que ja existia.
- `ui/theme.py`: estilos normais/desactivados/seleccionados/foco. O foco de
  teclado permanece visivel; icones desactivados mantem contraste.

Os layouts impõem dimensoes minimas e refluem sem duplicar widgets, sinais,
workers ou timers. A configuracao IA fica acima da resposta nas larguras
compactas; nunca comprime os campos para os sobrepor. As tabelas conservam
rolagem propria para detalhes tecnicos. Navegar nao consulta OBD nem Gemini.

## Ecras e adaptacoes funcionais

Visao geral apresenta RPM, temperatura, tensao, MIL, codigos, prontidao e grafico
das series existentes. Atalhos reutilizam os callbacks de consulta. Ligacao
apresenta escolhas TCP/USB/SPP, campos contextuais e estado do adaptador/ECU.
Diagnostico apresenta codigos e detalhe factual, freeze frame e prontidao em
areas tecnicas; limpeza preserva fotografia previa, restricoes e confirmacao.
Dados ao vivo mostra as 12 caixas de seleccao, comandos, intervalo, tabela e
grafico por PID/unidade/ECU, incluindo lacunas. Disponivel nao significa Normal.

IA tem sintomas/configuracao e as cinco seccoes estruturadas da resposta.
Mantem dados enviados, cache, captura, resposta original, quota, indisponibilidade,
dados alterados e aviso de sessao anterior. Historico tem arquivo e ficha de
fotografia, com abertura do detalhe original e exportacao JSON. A correspondencia
da analise continua na janela de detalhe, usando o instante guardado.
Simulador apresenta os seis cenarios existentes e estado interno, separado do
scanner; processo e portas ficam numa area recolhivel. Nenhum controlo altera
automaticamente a tabela OBD.

Nao foram copiados VIN/Volkswagen/oficina/tecnico/COM3/OBDLink/protocolo do
prototipo. Identificacao de veiculo fica Nao identificado. O painel nao afirma
10/100 Hz, velocidade CAN, CRC, certificacao, limiares mecanicos universais ou
medicao de pino 16. PDF, CSV, importacao, permanentes, modo 06, sliders e outras
funcoes nao implementadas sao omitidas. No Historico nao ha grafico temporal
inventado: os registos existentes sao fotografias.

## Executar e validar

```powershell
cd C:\Py\scanner_outo
.\.venv\Scripts\python.exe scripts\run_app.py
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 scripts\verify_stitch_visual.py --scale 1
.\.venv\Scripts\python.exe -X utf8 scripts\verify_stitch_visual.py --scale 1.25
.\.venv\Scripts\python.exe -X utf8 scripts\verify_stitch_visual.py --scale 1.5
```

O verificador usa Qt Widgets com backend offscreen, nao um mockup HTML. Executa
o fluxo real atraves da barra lateral com um emulador proprio em porta livre,
SQLite temporario e Gemini simulado. Captura 1440x900, 1120x740 e 860x600 pixels
logicos, em escalas Qt 100%, 125% e 150%, para os sete ecras e grafico; paginas
longas tambem recebem capturas da parte inferior. Os PNG ficam em
`artifacts/stitch`, ignorados pelo Git.

No ambiente nativo Windows tambem sao executados testes da janela. O monitor
limita a largura logica de 1440; as escalas adicionais sao simuladas por
QT_SCALE_FACTOR em processos separados. Nao foi alterada a escala do Windows.
Isto valida o reflow e a renderizacao Qt, nao substitui ensaio fisico em tres
monitores/escalas Windows. Resultados efectivos constam no CHECKLIST.

### Capturas locais

As capturas abaixo sao da aplicacao nativa funcional, com dados sinteticos
recebidos por OBD, e nao imagens geradas do prototipo:

- [Visao geral, 1440x900](../artifacts/stitch/1440x900-scale1-page6.png).
- [Ligacao, 1440x900](../artifacts/stitch/1440x900-scale1-page0.png).
- [Diagnostico, 1440x900](../artifacts/stitch/1440x900-scale1-page2.png).
- [Dados ao vivo, 1440x900](../artifacts/stitch/1440x900-scale1-page1.png).
- [Grafico, 1440x900](../artifacts/stitch/1440x900-scale1-chart.png).
- [Analise com IA, 1440x900](../artifacts/stitch/1440x900-scale1-page3.png).
- [Historico, 1440x900](../artifacts/stitch/1440x900-scale1-page4.png).
- [Simulador local, 1440x900](../artifacts/stitch/1440x900-scale1-page5.png).
- [IA compacta, formulario](../artifacts/stitch/860x600-scale1-page3.png).
- [IA compacta, resposta](../artifacts/stitch/860x600-scale1-bottom-page3.png).

Os links funcionam neste checkout apos executar o verificador; os PNG nao
sao publicados no Git. `scale1`, `scale1.25` e `scale1.5` identificam a matriz
offscreen. `scalenative` identifica o backend Windows, cuja geometria pode ser
limitada pelo monitor. A navegacao conserva exclusividade de seleccao, e as
tabelas reutilizam celulas inalteradas para evitar relayout inutil a cada tick.

### Barra lateral animada

O botao de menu no topo da barra lateral alterna entre 260 e 72 pixels
logicos, com uma transicao de 240 ms e curva InOutCubic. Os textos reaparecem
no fim da expansao; os icones, nomes acessiveis e tooltips continuam
disponiveis quando recolhida. O botao tambem funciona com Espaco pelo teclado.

Sem escolha manual, a barra recolhe automaticamente abaixo de 1050 pixels.
A escolha manual prevalece nos redimensionamentos seguintes, ate fechar a
janela; nao e gravada em disco. Cliques durante a animacao invertem a transicao
a partir da largura actual. A navegacao, a ligacao e os temporizadores nao
sao recriados. Os comandos de diagnostico, leituras e simulador reorganizam-se
em linhas adicionais para manter os textos visiveis numa janela compacta.

Testes especificos: `tests/test_sidebar.py` e o teste
`test_manual_sidebar_in_compact_application` em `tests/test_stitch_ui.py`.
Capturas locais: `artifacts/stitch/sidebar-expanded-compact.png` e
`artifacts/stitch/sidebar-collapsed-compact.png`.

Nao sao feitas chamadas reais Gemini. `.env`, bases locais, ambientes e
emulador externo do utilizador sao preservados. Hardware USB/SPP/Android e
Gemini remoto continuam a precisar de validacao externa. A publicacao deste
visual e da barra lateral foi solicitada separadamente pelo utilizador;
nao sao adicionadas coautorias ou colaboradores.
