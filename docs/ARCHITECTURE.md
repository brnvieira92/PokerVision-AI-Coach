# Plano técnico e arquitetura

## Inspeção e plano

O checkout continha somente `.git`; não havia funcionalidades, dependências ou instruções AGENTS.md a preservar. Python detectado: 3.11.5. Plano da Fase 1: criar pacote instalável; implementar regras sem Qt; adicionar matemática/bots/persistência; conectar UI; validar casos adversariais e partida completa; documentar limites.

## Dependências e direção

- `cards.py`: baralho, validação e ranking lexicográfico exato. Independente.
- `engine.py`: `Table` e `Player`, sem GUI, persistência ou IA. A API pública recebe ações somente do ator atual. Valores sempre em fichas inteiras.
- `math_engine.py`: fórmulas, simulação e `EquityResult` Pydantic. Independente do texto do coach. Não vê o estado secreto da mesa.
- `bots.py`: `Observation` contém somente informações autorizadas. `Bot.decide()` retorna ação/total, validada novamente pelo motor. Nenhuma referência à mesa é passada ao agente.
- `storage.py`: sessões e snapshots de mãos concluídas em SQLite; `PRAGMA user_version=1`. Transações e unicidade por sessão/mão evitam gravação duplicada. Rejeita versões futuras do schema.
- `ui.py`: renderização própria com QPainter, configurações, comandos e consultas. QTimer dá tempo ao event loop entre decisões dos bots. Cálculos pesados não são chamados pela UI desta fase.

Fluxo: UI → Table.act → transição/validação → atualização gráfica; ao concluir → Repository.save. Bots: Table → projeção Observation → Bot → Table.act. A matemática não depende de Bot ou UI.

## Máquina de estados e invariantes

Estados: `finished → preflop → flop → turn → river → finished`; fold de todos menos um termina em qualquer street. Quando não resta decisão com fichas, a mesa completa o board automaticamente. Há burn card em cada street comunitária. A distribuição utiliza Random sem semente por padrão e aceita semente apenas para reprodução de testes. A ordem dos participantes é circular; em heads-up o botão posta SB e age primeiro pré-flop, enquanto BB age primeiro pós-flop.

`current` é o preço da rodada; `increment` guarda o último aumento completo; `acted` registra o preço enfrentado por cada jogador na última ação. All-in incompleto muda o preço e obriga calls/folds, mas só reabre raise quando o aumento desde a última ação atinge o incremento completo, inclusive por soma de all-ins curtos. Não se permite aumentar sem oponente capaz de responder.

Contribuições totais são separadas das apostas da street. Ao liquidar, os níveis de contribuição criam potes independentes; jogadores que abandonaram contribuem mas não disputam. Um nível com um único contribuinte devolve a parte não coberta. Cada pote é dividido somente entre seus vencedores elegíveis; odd chips seguem a ordem à esquerda do botão. O rake não incide sobre devoluções.

Após ações: stacks/contribuições não negativos; cartas conhecidas únicas; soma de stacks + pote mantém o total inicial. Após liquidação: stacks + rake mantém o total inicial. `assert_integrity` é diagnóstico adicional; validação das ações usa exceções antes de mutações.

## Extensão nas próximas fases

Criar `PokerCoachService` que aceite análises Pydantic e observações autorizadas, sem receber cartas privadas de adversários. `OllamaProvider` deve usar worker/fila de uma inferência, cancelamento e fallback determinístico; ResourceManager e HardwareProfiler ficarão fora do motor. Downloads de modelos e alterações de servidor requerem autorização explícita. Não há chamadas de rede nesta entrega.

Extrair configuração de mesa para modelos próprios quando houver torneios; SNG/MTT coordenarão instâncias de Table, com blinds, antes, transferências e eliminações testados separadamente. ICM terá módulo matemático independente e casos de referência. Antes de promover ao SNG, ampliar testes de antes e estruturas de blinds.

Exercícios/estatísticas/revisão devem consultar decisões e snapshots anteriores à ação, não usar resultado futuro para avaliar estratégia. A Fase 3 deve adicionar schema versionado para esses snapshots; não inferir decisões históricas estruturadas a partir das strings atuais. Imagens serão importadas manualmente e validadas offline, sem captura automática.
