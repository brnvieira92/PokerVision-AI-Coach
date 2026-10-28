# Roadmap honesto

## Fase 1 — MVP Cash Game

Entregue o percurso jogável de ponta a ponta: seis jogadores, mão completa, bots, ações válidas, showdown e atualização de stacks. Regras e integração GUI têm testes. Matemática inicial e histórico SQLite disponíveis. Polimento e validação ampliada de regras continuam possíveis; isso não conclui as fases seguintes.

## Fase 2 — Coach local

Pendentes OllamaProvider e PokerCoachService, descoberta/listagem de modelos instalados, confirmação de download, Qwen3 1.7B/0.6B, worker/streaming/cancelamento/timeout, fallback verificado, HardwareProfiler, ResourceManager e testes de respostas inválidas e falta de memória. Modos Aprendizagem/Avaliação atuais apenas mostram/ocultam pot odds; não são a revisão completa da Fase 2. Variáveis OLLAMA_NUM_PARALLEL=1 e OLLAMA_MAX_LOADED_MODELS=1 serão documentadas como configuração opcional do servidor, sem alterar automaticamente um serviço em execução.

## Fase 3 — Treinamento

Ranges explícitos, exercícios, replayer por decisão, snapshots estruturados pré-ação, dashboard por conceito, amostras e incerteza, análises de imagens PNG/JPG com correção manual, OpenCV/OCR e validação de duplicatas. Não existe captura de clientes externos.

## Fase 4 — Sit & Go

Torneios 6/9 jogadores, antes, níveis, premiação fictícia, eliminações, push/fold, bolha, heads-up, ICM exato em referências pequenas, chipEV versus prêmioEV, relatórios.

## Fase 5 — MTT

Múltiplas mesas, balanceamento e transferência, aceleração de outras mesas, bolha/ITM/final, carreira e estudo personalizado. Testar invariantes de fichas e seating entre mesas.

## Fase 6 — Polimento

Acessibilidade, avatares próprios, animação de fichas, benchmarks CPU/GPU/RAM, avaliação de backend eval7, empacotamento PyInstaller e validação em máquina Windows limpa. Não há executável validado nesta entrega.
