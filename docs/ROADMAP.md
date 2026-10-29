# Roadmap

## Fase 1 — MVP Cash Game

Entregue o percurso jogável de ponta a ponta: seis jogadores, mão completa, bots, ações válidas, showdown, atualização de stacks, matemática inicial e histórico SQLite. Regras e integração GUI têm testes. A interface usa linguagem para iniciantes e guia de termos.

## Fase 2 — Coach local

Implementados e testados: OllamaProvider independente, tags/modelos instalados, download somente após autorização no aplicativo, recepção streaming em worker, timeout, cancelamento, tentativa CPU em erro GPU/memória, descarregamento, HardwareProfiler, ResourceManager, modos Sem LLM/Econômico/Equilibrado, snapshots pré-ação, revisão após sessão de Avaliação, explicações persistidas e migração v1/v2.

PokerCoachService recebe análises Pydantic com contas verificadas. O modelo escolhe explicações de catálogo em português, com fatos conferidos e fallback determinístico para inconsistências. Tokens brutos não são exibidos; o progresso de recepção aparece enquanto o conteúdo aguarda validação. Não há chat livre ou recomendação ótima.

Protocolo e falhas são testados com servidor local simulado; o diagnóstico detecta a GTX 1650 4 GB e aproximadamente 16 GB de RAM. O usuário pode instalar o Ollama e autorizar o modelo pela interface. Benchmarks formais de latência e consumo de inferência real nesta GPU ainda estão pendentes; a suíte não exige servidor ou modelo instalado.

## Fase 3 — Treinamento (entregas 0.3, 0.4 e 0.5)

Na versão 0.3 foram entregues revisão visual dos snapshots do usuário, exercícios determinísticos em cinco assuntos, correção passo a passo, geração de exercício de preço a partir de uma decisão, recomendação do próximo assunto e dashboard com amostras/incerteza. Quadro interativo de 169 classes com exemplos próprios, explicações de posição e contagem das 1326 combinações. Tentativas persistidas com migração v1/v2 → v3; a primeira resposta não pode ser substituída após a correção. A Avaliação bloqueia esses recursos até encerrar a sessão.

Na versão 0.4 foram acrescentados cenários de primeira aposta por regra declarada, custo de acompanhar na blind maior e completar flush; oito assuntos no total. Laboratório Monte Carlo visual contra uma mão fixa, mãos aleatórias ou combinações legais de um range. Plano de três blocos persistido e comparação dos últimos 7/30 dias com a janela anterior. O laboratório importa apenas cartas conhecidas de uma decisão e explica a simplificação para um adversário.

Na versão 0.5 foi acrescentado o Jogo assistido na Aprendizagem: pausa da decisão, cálculo contra todos os participantes, projeção de potes e devoluções com taxas, hipóteses explícitas e retorno à mesma jogada. Não recebe cartas privadas dos bots ou o baralho real. Modelo uniforme ou conjunto comum para todos; não estima ranges por ações. Resultados assistidos são salvos com a mão. O modo Avaliação bloqueia a ajuda.

Pendências da Fase 3 mantidas para entregas posteriores, registradas em [PENDING_PHASE3.md](PENDING_PHASE3.md). Ainda pendentes nesta fase: currículo estratégico mais amplo, avaliação do valor de decisões contra ranges com comportamento futuro, curvas de evolução longitudinal, relatórios por modalidade, identificação de padrões estratégicos sob hipóteses e visão computacional offline com OpenCV/OCR e correção manual de PNG/JPG. Os conjuntos do quadro não são soluções GTO e o revisor não reproduz todas as ações dos adversários. Nenhuma captura automática de clientes externos.

## Fase 4 — Sit & Go (iniciada em 0.6.0)

Primeira entrega jogável: mesa de seis participantes com stacks iguais, blinds progressivos por mãos, eliminação sem recomposição, classificação incluindo empates simultâneos, dois esquemas de premiação fictícia e relatório ICM entre mãos. Modos Aprendizagem/Avaliação, histórico de mãos, simulação do restante após eliminação e checkpoint atômico para retomada entre mãos. Cash Game preservado e isolado do torneio.

Controlador sem Qt, ICM por subconjuntos e testes até nove participantes. A interface desta entrega é somente de seis. Bots com heurística básica para stacks curtos, sem solver GTO/ICM. O jogo assistido de Cash Game não foi aplicado automaticamente ao torneio.

Pendentes da Fase 4: mesa de nove jogadores, antes, níveis por tempo, estruturas personalizáveis mais amplas, exercícios push/fold e comparação de decisões chipEV versus prêmioEV sob ranges e respostas explícitas. A fase não é declarada concluída. Uso e limitações em [SIT_AND_GO.md](SIT_AND_GO.md).

## Fase 5 — MTT

Múltiplas mesas, balanceamento/transferência, aceleração de mesas secundárias, bolha/ITM/final, carreira e estudo personalizado. Verificar invariantes de fichas e posições entre mesas.

## Fase 6 — Polimento

Acessibilidade, avatares próprios, animação de fichas, benchmarks CPU/GPU/RAM, backend eval7, PyInstaller e validação em Windows limpo. Não há executável ou instalador validado.
