# PokerVision AI Coach — 0.3.0

Academia independente de Texas Hold'em para Windows, com fichas fictícias. Inclui o Cash Game jogável da Fase 1, o coach local da Fase 2 e a primeira entrega da Fase 3: revisão visual, exercícios, quadro de mãos e progresso por assunto. A Fase 3 ainda não está completa; visão computacional e treinamento estratégico avançado continuam no roadmap.

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

## Treinamento — primeira entrega da Fase 3

Estas funcionalidades trabalham localmente, sem carregar um modelo de IA:

- **Revisão visual:** escolha uma mão salva e navegue por suas decisões com Anterior/Próxima ou pela barra. Mostra suas cartas, apenas as cartas da mesa já abertas naquele momento, as fichas e a ação registrada. Não revela mãos alheias ou cartas futuras. Também pode abrir por **Analisar mãos → Rever visualmente esta mão**. É uma revisão dos snapshots do usuário, não uma reprodução de todas as ações dos adversários. Mãos antigas sem snapshots continuam com histórico textual.
- **Treinamento:** clique em **Novo exercício**, escolha uma resposta e pressione **Conferir minha resposta**. Há cinco assuntos: combinações vencedoras, preço para continuar, apostas/botões, ordem de jogar e leitura de mãos iniciais. A correção mostra a resposta certa e o raciocínio. Nos exercícios de comparação todas as cartas são abertas propositalmente; isso é diferente de uma decisão real do simulador com cartas escondidas.
- **Exercício da sua decisão:** na revisão, **Praticar a conta desta decisão** gera uma pergunta com aquele pote e aquele pagamento. Só aparece habilitado quando a conta simples é aplicável; all-ins com possíveis potes separados não usam essa simplificação. Não utiliza o resultado futuro da mão para corrigir.
- **Mãos iniciais:** quadro de 169 classes, exemplos de conjuntos restrito/intermediário/amplo, edição por clique, contagem exata de combinações e explicação das seis posições. As seleções são exemplos próprios para aprender a ler ranges, não tabelas GTO nem instruções obrigatórias para apostar. Escolher uma posição explica a ordem de agir; não transforma o exemplo em recomendação ótima para aquele assento.
- **Meu progresso:** respostas/acertos por assunto, amostra, porcentagem, faixa ilustrativa de incerteza e últimas dez respostas. Selecione uma linha para praticar aquele assunto. Até haver três respostas por assunto, a sugestão prioriza os menos praticados; depois, o menor acerto suavizado nas últimas vinte respostas de cada assunto.

A primeira resposta de cada exercício é a única registrada. Depois de ver a correção, gere outro exercício para tentar novamente. Perguntas podem reaparecer em variações; os resultados não são amostras completamente independentes. A faixa de 95% usa Wilson e é ilustrativa, não uma certificação de habilidade. Não há nota de prontidão para torneios reais. Ganhos/perdas fictícios nas mãos não contam como acerto ou erro nos exercícios.

Na Avaliação, exercícios, conjuntos de mãos e revisões ficam bloqueados até **Finalizar sessão e revisar** no Coach IA. Termine a mão antes de finalizar a sessão. Ao reiniciar o aplicativo, tentativas e acertos permanecem salvos no banco.

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
- Ranking exato de cinco a sete cartas em Python. Monte Carlo reproduzível contra mãos uniformes, pot odds, SPR e EV de call sob hipóteses explícitas estão na API matemática. Equity por Monte Carlo não é executada automaticamente na interface nem pelo LLM. Erro padrão de Monte Carlo mede só amostragem sob o modelo uniforme, não incerteza dos ranges reais.
- Rake fictício opcional: apenas com flop, por pote, arredondado para baixo, com teto por mão; devoluções não sofrem taxa. Não reproduz regras de salas específicas. Sem antes neste MVP.

## Dados e atualização

Banco `data/pokervision.sqlite3`, relativo à pasta de execução. O iniciador fixa a pasta do projeto. Migração de schema v1/v2 para v3 preserva sessões, mãos, preferências e explicações, acrescentando as tentativas de exercícios. Novas mãos incluem decisões estruturadas no snapshot já existente. Para backup, feche o aplicativo e copie o banco. Não apague `data` durante atualizações.

Mãos concluídas são salvas imediatamente. Mãos em andamento não são retomadas após encerrar; o fechamento pede confirmação. Testes usam bancos temporários separados. O programa não armazena credenciais externas.

## Verificação e limites de validação

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
```

A suíte cobre regras, matemática, persistência, migração v1/v2/v3, exercícios e progresso, snapshots sem informação futura, fallback de respostas inconsistentes, CPU, ausência de GPU, pressão de memória, concorrência, protocolo HTTP/streaming, timeout/cancelamento e GUI responsiva. O teste HTTP usa um servidor simulado local e não carrega modelos. O teste GUI usa Qt offscreen. Capturas ficam em `artifacts/`.

Hardware detectado nesta máquina: GTX 1650 com 4096 MB de VRAM e aproximadamente 16 GB de RAM. No momento da verificação o Ollama recusou conexão; não foi possível validar inferência real Qwen3, download/descarregamento no servidor real ou desempenho/consumo do modelo nesta GPU. A integração e seus erros foram verificados com servidor de teste. Não há promessa de latência ou consumo da IA.

Dependências diretas validadas: PySide6 6.12.0, Pydantic 2.14.1, psutil 7.2.2 e pytest 9.2.0. `requirements-lock.txt` registra as versões do ambiente. `eval7` continua opcional e não é usado/validado; o avaliador Python evita compilação nativa no Windows.

## Próximas fases

A primeira entrega da Fase 3 cobre exercícios básicos, recomendação por acertos, revisão visual das decisões e leitura de conjuntos de mãos. Ainda não há currículo estratégico completo, identificação comprovada de erros em partidas, simulação de equity contra ranges selecionados, reprodução de todas as ações da mesa, ICM, Sit & Go, MTT, carreira, visão computacional, bankroll educacional ou executável empacotado. O resumo da sessão não chama jogadas de erros sem hipóteses suficientes. Polimento de layout e acessibilidade continua possível.

O programa não captura mesas reais, não importa PokerCraft e não interage com contas ou clientes de poker. Feche-o antes de abrir GGPoker ou outro cliente real. Assistência existe somente no simulador próprio.

Arquitetura: `docs/ARCHITECTURE.md`. Roadmap: `docs/ROADMAP.md`. Regras dos exercícios e das métricas: `docs/TRAINING.md`.
