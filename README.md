# PokerVision AI Coach — 0.6.0

Academia independente de Texas Hold'em para Windows, com fichas fictícias. Inclui o Cash Game jogável da Fase 1, o coach local da Fase 2 e a continuação da Fase 3: revisão visual, oito assuntos de treino, quadro de mãos, laboratório de equity, plano de estudo, comparação de períodos e jogo assistido dentro do simulador. A Fase 3 permanece com pendências registradas. A Fase 4 foi iniciada com um Sit & Go jogável de seis participantes, premiação fictícia e introdução ao ICM.

## Iniciar

Validado com Python 3.11.5 no Windows x64. O ambiente `.venv` deste checkout já foi atualizado.

```powershell
cd D:\projetos-bruno\projeto-PokerVision-AI-Coach\PokerVision-AI-Coach
.venv\Scripts\python.exe -m pokervision
```

Ou dê dois cliques em `iniciar.bat`. Para uma instalação nova:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

A instalação de dependências exige internet. Jogar, consultar históricos e usar o guia verificado funcionam sem internet, GPU, Ollama ou serviços pagos. Reinicie o aplicativo após atualizar o código; uma janela já aberta continua usando a versão antiga.

## Aprender e jogar

1. Em **Configurações**, escolha Aprendizagem ou Avaliação e aplique entre mãos. Blinds são as apostas obrigatórias menor/maior; o stack é o saldo de fichas. Os rótulos mostram português e o guia explica os nomes usados no poker.
2. Em **Jogar Cash Game**, clique em **Nova mão**. A mesa possui você e cinco adversários virtuais. Sua vez aparece em verde.
3. Os botões permitem Desistir, Passar, Pagar, Apostar/Aumentar ou colocar Todas as fichas. Passe o mouse para ver explicações. **Total na rodada** inclui fichas que você já colocou naquela rodada, não apenas o acréscimo.
4. O painel explica o preço para continuar usando os valores atuais. Isso não estima sua chance de ganhar nem determina uma jogada ótima. Em situações de all-in, a conta simplificada com o pote inteiro é omitida.
5. **Entender os termos** abre um guia com exemplos de pote, equity, taxa da mesa, posição, mãos possíveis dos adversários, stack efetivo, etapas da mão e combinações vencedoras. O histórico traduz cartas antigas como `Th` para `10 de copas` sem modificar os registros originais.
6. Ao terminar, confira o saldo inicial/final e o histórico. Receber fichas pode incluir devoluções e não é necessariamente lucro. Inicie outra mão mantendo stacks e avançando o botão. Reponha fichas nas Configurações quando necessário.

## Sit & Go — primeira entrega da Fase 4

Abra **Jogar Sit & Go** no menu lateral, configure os valores fictícios e clique em **Iniciar novo torneio**. Você joga contra cinco adversários; todos começam com as mesmas fichas. A aposta obrigatória aumenta a cada quantidade configurada de mãos. Não há recomposição: ficar sem fichas ao fim da mão elimina o participante.

A cada mão concluída, clique em **Próxima mão**. A aba **Classificação / ICM** mostra posições já definidas, prêmios fictícios e, entre mãos na Aprendizagem, a diferença entre valor proporcional às fichas e expectativa de prêmio pelo ICM. Em Avaliação, dicas/ICM e outros recursos de estudo ficam bloqueados até encerrar o torneio.

Se você for eliminado, pode acompanhar os bots ou acelerar o restante até o campeão. A classificação final aparece automaticamente. Torneios são salvos entre mãos; use o seletor abaixo da mesa para abrir ou retomar. Uma mão em andamento ao fechar será descartada, com aviso; mãos já concluídas permanecem registradas. Cash Game e Sit & Go são isolados e não ficam em andamento simultaneamente.

Há dois esquemas de prêmio (dois ou três premiados), inscrições em pontos fictícios e tratamento explícito de eliminações simultâneas. O ICM é um modelo didático de premiação; não é previsão, solver ou recomendação de all-in. A interface desta entrega suporta seis jogadores, sem antes. Mesa de nove, níveis por relógio e treino estratégico ICM mais amplo permanecem pendentes.

Instruções e limites: [Sit & Go](docs/SIT_AND_GO.md). Pendências preservadas da Fase 3: [lista de continuidade](docs/PENDING_PHASE3.md).

## Jogo assistido — ajuda antes de decidir (0.5)

1. Em **Configurações**, escolha **Aprendizagem** e aplique entre mãos.
2. Abra **Jogar Cash Game → Nova mão**. Na sua vez, clique em **Jogo assistido: pausar e estudar equity**.
3. A janela mostra suas cartas e as cartas comunitárias já abertas. Ações, bots e início de nova mão ficam bloqueados durante o estudo. Nenhuma carta privada dos bots ou carta futura do baralho jogável é consultada.
4. Escolha mãos aleatórias para os adversários ou o mesmo conjunto do quadro Mãos iniciais para todos. A escolha é uma hipótese sua, não um range estimado automaticamente a partir das apostas.
5. Clique em **Calcular esta hipótese**. O cálculo roda em worker, sem Ollama/GPU, contra todos os adversários que ainda participam, inclusive os que estão sem fichas para apostar.
6. Explore as barras, os potes e as possibilidades de cartas. As possibilidades são sorteios independentes, não as cartas reais que sairão. Mesmo as mãos adversárias sorteadas não são mostradas nessa janela.
7. Clique em **Concluir estudo e voltar à mesma decisão** ou feche a janela. O cálculo é cancelado se necessário e você volta à mesma mão, com as mesmas cartas, fichas e jogador da vez. Escolha sua ação normalmente.

A hipótese é explícita: você paga o preço atual ou passa se não há custo; todos os adversários ainda na mão acompanham esse preço até o limite do saldo; ninguém aumenta ou desiste; as próximas rodadas são passadas até a comparação final. A análise não prevê como os bots realmente responderão, não modela fold equity e não escolhe uma ação ótima.

**Equity contra todos** é a média da participação em uma comparação de mãos: 1 por vitória, 1/2 em empate de dois, 1/3 em empate de três etc. Com all-ins, esse número não pode ser simplesmente multiplicado pelo pote total: você pode ser elegível somente a parte das fichas. A tabela avalia cada pote entre seus participantes, inclui fichas de quem desistiu, devolve apostas não cobertas e desconta a taxa fictícia configurada. Distribui fichas inteiras e sobras na mesma ordem do motor.

O **recebimento médio** por pote inclui suas próprias contribuições; não é lucro nem uma recomendação de pagar. As faixas conservadoras de 95% medem apenas erro de amostragem por estimativa, não a qualidade da hipótese sobre adversários. A explicação separa o pote atual dos pagamentos hipotéticos dos outros jogadores. Conjuntos estreitos demais para sortear todos sem repetir cartas são recusados, sem inventar combinações ou trocar de hipótese silenciosamente.

O modo **Avaliação** não permite abrir o Jogo assistido. As análises concluídas são salvas com a mão terminada, vinculadas ao snapshot da decisão e às hipóteses usadas; a última análise de cada decisão substitui a anterior. O histórico informa que a mão teve cálculo assistido. Esses resultados não contam como acertos ou erros de exercícios.

O laboratório independente continua oferecendo seus exemplos de um adversário; o Jogo assistido usa a quantidade real de participantes da mesa e projeção de potes sob a hipótese declarada.

## Treinamento — Fase 3 em evolução

Estas funcionalidades trabalham localmente, sem carregar um modelo de IA:

- **Revisão visual:** escolha uma mão salva e navegue por suas decisões com Anterior/Próxima ou pela barra. Mostra suas cartas, apenas as cartas da mesa já abertas naquele momento, as fichas e a ação registrada. Não revela mãos alheias ou cartas futuras. Também pode abrir por **Analisar mãos → Rever visualmente esta mão**. É uma revisão dos snapshots do usuário, não uma reprodução de todas as ações dos adversários. Mãos antigas sem snapshots continuam com histórico textual.
- **Treinamento:** clique em **Novo exercício**, escolha uma resposta e pressione **Conferir minha resposta**. Há oito assuntos: combinações vencedoras, preço para continuar, apostas/botões, ordem de jogar, leitura de mãos iniciais, cenários de primeira aposta antes das cartas da mesa, custo de acompanhar na aposta obrigatória maior e cartas que completam um flush. As decisões de primeira aposta seguem uma regra didática declarada no enunciado; não são gabaritos de estratégia ótima. A correção mostra a resposta certa e o raciocínio. Nos exercícios de comparação todas as cartas são abertas propositalmente; isso é diferente de uma decisão real do simulador com cartas escondidas.
- **Exercício da sua decisão:** na revisão, **Praticar a conta desta decisão** gera uma pergunta com aquele pote e aquele pagamento. Só aparece habilitado quando a conta simples é aplicável; all-ins com possíveis potes separados não usam essa simplificação. Não utiliza o resultado futuro da mão para corrigir.
- **Mãos iniciais:** quadro de 169 classes, exemplos de conjuntos restrito/intermediário/amplo, edição por clique, contagem exata de combinações e explicação das seis posições. As seleções são exemplos próprios para aprender a ler ranges, não tabelas GTO nem instruções obrigatórias para apostar. Escolher uma posição explica a ordem de agir; não transforma o exemplo em recomendação ótima para aquele assento.
- **Meu progresso:** respostas/acertos por assunto, amostra, porcentagem, faixa ilustrativa de incerteza e últimas dez respostas. Escolha Todo o histórico ou janelas móveis de 7/30 dias. Nas janelas, aparecem também a amostra/taxa do período anterior de igual duração e a diferença em pontos percentuais. Sem amostra em um dos períodos não há comparação; a sugestão de estudo continua usando todo o histórico recente, não apenas o filtro da tela. Selecione uma linha para praticar aquele assunto. Até haver três respostas por assunto, a sugestão prioriza os menos praticados; depois, o menor acerto suavizado nas últimas vinte respostas de cada assunto.

- **Plano de estudo:** monta três blocos de cinco novas respostas, priorizando assuntos pouco praticados e taxas recentes de acerto menores. O plano e a contagem inicial ficam salvos; completar um bloco significa praticar, não dominar o conteúdo. Montar outro plano refaz as metas, preservando todas as tentativas anteriores.
- **Laboratório de equity:** escolha cartas, um exemplo e de 100 a 2000 simulações. Compare vitórias, empates, derrotas, equity e frequência de subir de categoria. Pode usar uma mão adversária específica, mãos aleatórias ou o conjunto selecionado em Mãos iniciais. Há apenas um adversário nesta comparação; ao importar uma decisão de mesa com mais jogadores, o painel avisa que está simplificando o cenário. Cartas privadas alheias nunca são importadas da partida.

No laboratório, equity é a média de 1 por vitória, 0,5 por empate e 0 por derrota contra um adversário. “Categoria superior” compara o tipo da melhor combinação inicial com a final; não inclui apenas melhorar cartas de desempate. Um par que vira trinca pode continuar perdendo. Sem ao menos três cartas da mesa, a categoria inicial não é definida. Cada possibilidade exibida depois da simulação é um sorteio hipotético, não uma previsão da próxima mão.

Contra um conjunto de mãos, são enumeradas as combinações físicas legais, retirando as cartas conhecidas; o sorteio é uniforme entre essas combinações, não entre as classes. O laboratório não modela folds, apostas futuras, taxas, vários adversários ou potes separados. A faixa de amostragem é conservadora (Hoeffding, 95%), mede só o erro Monte Carlo sob o modelo escolhido e não trata a hipótese sobre o adversário como certeza. O cálculo roda em worker, tem cancelamento e semente reproduzível. Não requer Ollama ou GPU.

A primeira resposta de cada exercício é a única registrada. Depois de ver a correção, gere outro exercício para tentar novamente. Perguntas podem reaparecer em variações; os resultados não são amostras completamente independentes. No dashboard de exercícios, a faixa de 95% usa Wilson e é ilustrativa, não uma certificação de habilidade. Não há nota de prontidão para torneios reais. Ganhos/perdas fictícios nas mãos não contam como acerto ou erro nos exercícios.

Na Avaliação, exercícios, conjuntos de mãos, laboratório, plano e revisões ficam bloqueados até **Finalizar sessão e revisar** no Coach IA. Termine a mão antes de finalizar a sessão. Ao reiniciar o aplicativo, tentativas e acertos permanecem salvos no banco.

## Coach IA — Fase 2

O modo inicial é **Sem LLM**, que já oferece explicações verificadas. Não há downloads automáticos.

- **Aprendizagem:** na sua vez, clique em **Pedir explicação desta decisão**. Escolha entender o preço, as opções, a posição ou as cartas da mesa. A página Coach IA usa exclusivamente as informações disponíveis antes de agir.
- **Avaliação:** o pedido de ajuda fica bloqueado durante as mãos. Entre mãos, na página Coach IA, clique em **Finalizar sessão e revisar** para acessar as decisões da sessão. Alterar o combo nas Configurações sem aplicar não muda o modo de uma sessão em andamento.
- **Revisão:** selecione uma decisão da sessão finalizada ou uma mão em **Analisar mãos → Estudar as decisões desta mão no Coach**. O aplicativo preserva snapshots anteriores às ações, sem cartas escondidas de outros jogadores e sem resultados futuros. Registros antigos não ganham decisões inventadas: continuam disponíveis como histórico textual.
- **Respostas guardadas:** explicações são persistidas por decisão; revisões restauram a explicação anterior quando houver uma.

O coach usa Pydantic para validar snapshot, análise matemática e resposta. A IA seleciona e ordena explicações de um catálogo em português; não publica texto livre, inventa probabilidades ou recalcula as contas. Qualquer dado numérico alterado, tópico inválido ou resposta incompleta provoca retorno ao guia verificado. Essa restrição deliberada reduz a flexibilidade de conversa para manter a coerência matemática. Não é um chat aberto nem um solver GTO.

A resposta do Ollama é recebida gradualmente em worker. A interface mostra o progresso de recepção; o conteúdo só é publicado após validação completa. A explicação determinística já fica visível enquanto a IA trabalha. A mesa e a interface continuam responsivas. Uma solicitação do painel por vez; um bloqueio compartilhado impede inferências concorrentes. Cancelamento interrompe a leitura local, mas a liberação efetiva de trabalho/memória no servidor depende do Ollama.

## Configurar Ollama opcional

Instale/inicie o Ollama separadamente se quiser usar a IA. O aplicativo conversa apenas com o servidor local padrão `http://127.0.0.1:11434`; não inicia serviços nem altera variáveis do servidor.

1. Abra **Coach IA → Verificar computador e Ollama**. A verificação lista CPU, RAM disponível/total, memória do aplicativo, GPU/VRAM/driver NVIDIA quando detectáveis e modelos locais instalados. Falta de GPU não impede o guia ou o simulador.
2. Escolha **Econômico** (prefere `qwen3:0.6b-q4_K_M`) ou **Equilibrado** (prefere `qwen3:1.7b-q4_K_M`). Aliases instalados `qwen3:0.6b`/`qwen3:1.7b` também são aceitos como alternativas. Outros modelos locais podem ser selecionados explicitamente na lista; não há garantia de qualidade para eles. Modelos identificados como remotos/cloud são excluídos da lista.
3. Se faltar modelo, escolha um dos dois Qwen3 em **Baixar modelo…**. Um diálogo informa o uso de internet/disco e exige confirmação. O botão não instala o servidor. Atualize a verificação após o download. É possível cancelar o pedido; arquivos parciais podem permanecer no cache do Ollama.
4. Marque **Usar somente CPU** se necessário. Falhas de inferência que mencionam GPU/CUDA/memória provocam uma tentativa em CPU; demais falhas retornam ao guia. A seleção automática de hardware pertence ao Ollama.
5. **Liberar modelo da memória** envia uma solicitação explícita ao servidor. Por padrão o modelo fica carregado por até dois minutos após o uso, conforme o servidor permitir.

Parâmetros: contexto 2048, até 384 tokens, temperatura 0.2, `think=false`, `keep_alive=2m`, timeout total de 90 segundos para explicação. O cancelamento é verificado durante a leitura. APIs/modelos incompatíveis retornam ao guia, sem tentar baixar alternativas silenciosamente.

Proteção de RAM: abaixo de 1,5 GB disponíveis usa apenas o guia; de 1,5 a 3 GB reduz Equilibrado para Econômico. São limites conservadores de engenharia, não garantias de desempenho. As medições são pontuais; a disponibilidade pode mudar após a leitura. Não há reserva de memória ou monitoramento contínuo nesta versão.

Configurações opcionais para quem administra o servidor: `OLLAMA_NUM_PARALLEL=1` e `OLLAMA_MAX_LOADED_MODELS=1`. Configure-as no ambiente do processo do Ollama e reinicie o servidor quando apropriado. Definir variáveis dentro deste aplicativo não alteraria uma instância já em execução; o aplicativo não aplica essas mudanças.

Referências oficiais: [API de chat](https://docs.ollama.com/api/chat), [Qwen3 1.7B](https://ollama.com/library/qwen3:1.7b-q4_K_M), [Qwen3 0.6B](https://ollama.com/library/qwen3:0.6b-q4_K_M), [instalação do Qt](https://doc.qt.io/qtforpython-6/gettingstarted.html).

## Regras e matemática entregues

- Cash Game 6-max com regras independentes da interface: pré-flop até showdown, heads-up, posições vagas, raises mínimos, all-ins curtos, reabertura cumulativa, potes laterais, devoluções não cobertas, empates e odd chip à esquerda do botão.
- Cinco adversários heurísticos recebem apenas suas próprias cartas e informações públicas. Não usam solver, ranges calibrados ou estratégia GTO; não há dificuldade selecionável. A distribuição não é ajustada para beneficiar ou prejudicar o usuário.
- Ranking exato de cinco a sete cartas em Python. Monte Carlo reproduzível contra mãos uniformes, pot odds, SPR e EV de call sob hipóteses explícitas estão na API matemática. A mesa não calcula equity automaticamente nem pede probabilidades ao LLM; o laboratório e o jogo assistido oferecem execução sob demanda em worker. Erro padrão de Monte Carlo mede só amostragem sob o modelo uniforme, não incerteza dos ranges reais.
- Rake fictício opcional: apenas com flop, por pote, arredondado para baixo, com teto por mão; devoluções não sofrem taxa. Não reproduz regras de salas específicas. Sem antes neste MVP.

## Dados e atualização

Banco `data/pokervision.sqlite3`, relativo à pasta de execução. O iniciador fixa a pasta do projeto. Migração até schema v4 preserva sessões, mãos, preferências, explicações e tentativas de exercícios, acrescentando os checkpoints de torneios. Mão de Sit & Go e checkpoint são gravados na mesma transação. Novas mãos incluem decisões estruturadas no snapshot já existente. Para backup, feche o aplicativo e copie o banco. Não apague `data` durante atualizações.

Mãos concluídas são salvas imediatamente. Mãos em andamento não são retomadas após encerrar; o fechamento pede confirmação. Testes usam bancos temporários separados. O programa não armazena credenciais externas.

## Verificação e limites de validação

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
```

A suíte cobre regras, matemática, persistência, migração v1/v2/v3, exercícios e progresso, snapshots sem informação futura, fallback de respostas inconsistentes, CPU, ausência de GPU, pressão de memória, concorrência, protocolo HTTP/streaming, timeout/cancelamento e GUI responsiva. O teste HTTP usa um servidor simulado local e não carrega modelos. O teste GUI usa Qt offscreen. Capturas ficam em `artifacts/`.

Hardware detectado nesta máquina: GTX 1650 com 4096 MB de VRAM e aproximadamente 16 GB de RAM. A suíte verifica a integração Ollama e seus erros com servidor de teste; não exige um modelo real carregado. Instalação e download de modelos são opcionais e autorizados pelo usuário. Não há benchmark formal nem promessa de latência ou consumo da IA nesta GPU.

Dependências diretas validadas: PySide6 6.12.0, Pydantic 2.14.1, psutil 7.2.2 e pytest 9.2.0. `requirements-lock.txt` registra as versões do ambiente. `eval7` continua opcional e não é usado/validado; o avaliador Python evita compilação nativa no Windows.

## Próximas fases

A Fase 3 agora cobre exercícios básicos e cenários didáticos, recomendação por acertos, plano de prática, revisão visual das decisões, leitura de conjuntos de mãos e comparação probabilística contra um adversário. Ainda não há currículo estratégico completo, identificação comprovada de erros em partidas, reprodução de todas as ações da mesa, mesa de torneio de nove jogadores, análise de decisões por prêmioEV, MTT, carreira, visão computacional, bankroll educacional ou executável empacotado. O resumo da sessão não chama jogadas de erros sem hipóteses suficientes. Polimento de layout e acessibilidade continua possível.

O programa não captura mesas reais, não importa PokerCraft e não interage com contas ou clientes de poker. Feche-o antes de abrir GGPoker ou outro cliente real. Assistência existe somente no simulador próprio.

O schema agora é v4, com a tabela de torneios; plano e análises assistidas continuam nos registros já existentes. Não há perda ou reinício de tentativas ao atualizar.

Arquitetura: `docs/ARCHITECTURE.md`. Roadmap: `docs/ROADMAP.md`. Regras dos exercícios e das métricas: `docs/TRAINING.md`.
