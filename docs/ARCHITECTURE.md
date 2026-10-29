# Arquitetura

## Plano e inspeção

O checkout inicial continha apenas `.git`. A Fase 1 criou o motor independente e a mesa jogável. Na Fase 2 foram preservados esse motor e os registros existentes; acrescentaram-se snapshots pré-ação, coach opcional, workers e migração de dados. A primeira entrega da Fase 3 acrescenta revisão visual, exercícios e métricas sem dependências pesadas. Interface didática e fórmulas continuam funcionando sem servidor de IA.

## Módulos e dependências

- `cards.py`: baralho e ranking lexicográfico exato de cinco a sete cartas.
- `engine.py`: `Table`/`Player`, regras de no-limit, sem GUI, banco ou IA.
- `math_engine.py`: fórmulas, Monte Carlo e resultados Pydantic, sem texto do coach.
- `bots.py`: projeção pública `Observation` + cartas próprias. Ações passam novamente pela validação do motor.
- `education.py`: vocabulário, guia, tradução de históricos antigos e lições básicas na mesa.
- `coach.py`: `DecisionSnapshot`, `DecisionAnalysis`, `DecisionRecord`, `LessonChoice` e `CoachReply`. PokerCoachService valida e organiza o catálogo de explicações. Snapshots têm apenas cartas do usuário, board e dados públicos anteriores à ação; não contêm vencedor, resultado ou cartas privadas alheias.
- `ollama.py`: HTTP local via stdlib, tags, chat, pull e unload. Sem credenciais ou downloads implícitos. Limites de resposta, timeout total e leitura cancelável. Respostas HTTP chunked são tratadas por HTTPResponse; o reader verifica cancelamento/timeout sem invalidar o buffer a cada pausa de rede.
- `resources.py`: HardwareProfiler com psutil/nvidia-smi e fallback sem GPU. ResourceManager serializa inferências e reduz o modo sob pouca RAM. Não altera configuração de servidor ou outros aplicativos.
- `workers.py`: tarefas Qt, sinais e CancelToken. BackgroundJobs admite uma operação do painel por vez; inferências também compartilham um bloqueio independente da GUI. Cancelamento não publica resposta parcial como concluída.
- `coach_panel.py`: configuração, diagnóstico, autorização de download, progresso, cancelamento, seleção/revisão de decisões e persistência de explicações. Resultados antigos são descartados quando o contexto muda ou a janela fecha.
- `storage.py`: SQLite com schema v3; sessões, mãos, preferências, explicações e exercise_attempts. Migração preserva dados v1/v2. Novos snapshots ficam no JSON das mãos; históricos antigos continuam legíveis.
- `ranges.py`: classes canônicas de duas cartas, matriz 13×13, contagem de combinações e conjuntos didáticos próprios.
- `training.py`: Exercise/Choice/Correction Pydantic, geradores, gabaritos, intervalo Wilson e recomendação por amostra/acertos recentes. Não depende da GUI, do LLM ou do banco.
- `review.py`: CardsCanvas e ReviewPanel; renderiza apenas os DecisionRecords, ignorando board final e cartas privadas alheias do payload da mão.
- `training_ui.py`: exercícios, quadro editável e dashboard. A correção chama o repositório antes de atualizar a tela; repetir submissão não cria uma nova tentativa.
- `ui.py`: comandos, desenho QPainter, bot timer e coordenação. Captura a decisão antes de chamar o motor, registra apenas após uma ação válida e salva ao concluir a mão. Modos de treino são fixados ao aplicar uma sessão, evitando revelar dicas por mudança não aplicada do combo.

## Fluxo de decisão

GUI → snapshot público antes da ação → análise com pot odds, hipóteses/dados ausentes → coach opcional em worker → validação → renderização de texto verificado. A ação do jogador segue GUI → Table.act → validação/transição → DecisionRecord → snapshot da mão concluída → SQLite.

A probabilidade real de ganhar não é calculada pelo LLM. A resposta deve repetir identificação/fatos e selecionar tópicos válidos, sem campos extras ou texto livre. O app publica os textos do catálogo associados aos tópicos e seus próprios números. Essa escolha limita a flexibilidade do modelo e impede que uma resposta aparentemente plausível altere contas verificadas. Erros de serviço/schema/fatos acionam explicação determinística. Cancelamento é distinto de falha: encerra o pedido sem apresentar uma nova resposta como concluída.

Na Avaliação, nenhuma explicação por decisão é permitida enquanto uma sessão estiver aberta, mesmo entre mãos. “Finalizar sessão e revisar” encerra a sessão e libera snapshots. O resumo não usa resultado final para classificar decisões como boas/ruins e não atribui notas sem fundamento.

## Invariantes do motor preservadas

Estados: `finished → preflop → flop → turn → river → finished`. Fold de todos menos um termina em qualquer etapa. Sem decisões com fichas, completa-se o board. Há burn card por etapa. Aleatoriedade padrão sem semente; sementes opcionais reproduzem testes, sem ajustar distribuição em função do usuário.

Ordem circular; no heads-up o botão posta a aposta menor e age primeiro pré-flop, e o outro começa pós-flop. `current` guarda o preço, `increment` o último aumento completo e `acted` o preço da última ação de cada jogador. Aumentos incompletos só reabrem raise quando o acréscimo acumulado desde a última ação chega ao incremento completo. Não se aumenta sem oponente capaz de responder.

Contribuições totais e apostas de cada rodada são separadas. Níveis de contribuição criam potes independentes; quem desistiu contribui mas não disputa. Um nível com um único contribuinte é devolvido. Odd chips vão primeiro aos vencedores à esquerda do botão. Rake não incide sobre devoluções.

Após ações: stacks não negativos, cartas únicas, stacks + pote conservados. Após liquidação: stacks + rake conservados. Validação de ações ocorre antes de mutações; asserts são diagnósticos adicionais.

## Limites e extensão

ResourceManager usa limites conservadores: abaixo de 1,5 GB livres, sem LLM; abaixo de 3 GB, Equilibrado vira Econômico. Não reserva memória nem monitora continuamente. Só nvidia-smi expõe GPU/VRAM nesta versão; GPUs não NVIDIA podem aparecer como não detectadas. O modo CPU do provider e o fallback matemático permanecem disponíveis.

Ollama recebe contexto 2048, previsão máxima 384, temperatura 0.2, think=false e keep_alive=2m. Protocolos e erros são testados com servidor simulado; a validação com modelo real permanece pendente enquanto o serviço não estiver disponível e o modelo não tiver sido autorizado/instalado.

A Fase 3 já acrescenta exercícios e métricas sobre os registros pré-ação; ainda faltam análise contra ranges, visão offline e treinamento estratégico mais amplo. Torneios devem coordenar Table sem introduzir Qt no motor; antes, blinds progressivos, seating e ICM terão testes próprios. Não inferir snapshots históricos completos a partir de strings antigas, nem usar informações futuras para julgar decisões.


## Exercícios e progresso

ExerciseFactory usa Random injetável para testes e UUID independente para cada exercício. Comparações usam o avaliador exato existente; preço usa pot_odds. O banco guarda o enunciado/alternativas/gabarito completos, a escolha e o resultado, permitindo auditar tentativas sem depender de uma versão futura do gerador. exercise_id é chave primária e bloqueia recontagem ou troca de resposta depois da primeira submissão. Há um perfil local de treino, sem contas externas.

A recomendação primeiro cobre amostras inferiores a três respostas por assunto; depois usa (acertos recentes + 1)/(respostas recentes + 2), com janela de vinte por assunto. O dashboard mostra contagens de todo o histórico e faixa Wilson com z=1.96; a faixa é apenas ilustrativa sob exercícios repetidos/correlacionados. Notas estratégicas e Tournament Readiness Score não são calculados.

O quadro de mãos agrupa seis combinações por par, quatro por classe do mesmo naipe e doze por classe de naipes diferentes. As 169 classes cobrem as 1326 combinações sem cartas conhecidas. Não há cálculo de blockers ou equity da seleção nessa entrega. As seleções são exemplos pedagógicos próprios, sem frequências mistas ou calibração por solver.
