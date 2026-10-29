# Roadmap

## Fase 1 — MVP Cash Game

Entregue o percurso jogável de ponta a ponta: seis jogadores, mão completa, bots, ações válidas, showdown, atualização de stacks, matemática inicial e histórico SQLite. Regras e integração GUI têm testes. A interface usa linguagem para iniciantes e guia de termos.

## Fase 2 — Coach local

Implementados e testados: OllamaProvider independente, tags/modelos instalados, download somente após autorização no aplicativo, recepção streaming em worker, timeout, cancelamento, tentativa CPU em erro GPU/memória, descarregamento, HardwareProfiler, ResourceManager, modos Sem LLM/Econômico/Equilibrado, snapshots pré-ação, revisão após sessão de Avaliação, explicações persistidas e migração v1/v2.

PokerCoachService recebe análises Pydantic com contas verificadas. O modelo escolhe explicações de catálogo em português, com fatos conferidos e fallback determinístico para inconsistências. Tokens brutos não são exibidos; o progresso de recepção aparece enquanto o conteúdo aguarda validação. Não há chat livre ou recomendação ótima.

Validação real Qwen3/Ollama continua pendente: o servidor não estava em execução nesta máquina. Nenhum modelo foi baixado. Protocolo e falhas testados com servidor local simulado; diagnóstico real detectou GTX 1650 4 GB e aproximadamente 16 GB RAM. Desempenho e consumo de inferência real ainda precisam ser medidos com um modelo autorizado e disponível.

## Fase 3 — Treinamento (primeira entrega em 0.3.0)

Entregues revisão visual dos snapshots do usuário, exercícios determinísticos em cinco assuntos, correção passo a passo, geração de exercício de preço a partir de uma decisão, recomendação do próximo assunto e dashboard com amostras/incerteza. Quadro interativo de 169 classes com exemplos próprios, explicações de posição e contagem das 1326 combinações. Tentativas persistidas com migração v1/v2 → v3; a primeira resposta não pode ser substituída após a correção. A Avaliação bloqueia esses recursos até encerrar a sessão.

Ainda pendentes nesta fase: currículo estratégico mais amplo, avaliação de decisões contra ranges explícitos, gráficos de evolução por período, relatórios por modalidade, identificação de padrões estratégicos sob hipóteses, visão computacional offline com OpenCV/OCR e correção manual de PNG/JPG. Os conjuntos do quadro não são soluções GTO e o revisor não reproduz todas as ações dos adversários. Nenhuma captura automática de clientes externos.

## Fase 4 — Sit & Go

Torneios 6/9 jogadores, antes, níveis, premiação fictícia, eliminações, push/fold, bolha, heads-up, ICM com casos de referência e comparação chipEV/prêmioEV.

## Fase 5 — MTT

Múltiplas mesas, balanceamento/transferência, aceleração de mesas secundárias, bolha/ITM/final, carreira e estudo personalizado. Verificar invariantes de fichas e posições entre mesas.

## Fase 6 — Polimento

Acessibilidade, avatares próprios, animação de fichas, benchmarks CPU/GPU/RAM, backend eval7, PyInstaller e validação em Windows limpo. Não há executável ou instalador validado.
