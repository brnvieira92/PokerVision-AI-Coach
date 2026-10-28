# PokerVision AI Coach — 0.1.0

Academia independente de Texas Hold'em para Windows, exclusivamente offline e com fichas fictícias. Esta entrega cobre o MVP jogável de Cash Game da Fase 1. Não representa o treinador completo das seis fases.

## Iniciar no Windows

Python 3.11+ (validado neste ambiente com Python 3.11.5, Windows x64).

```powershell
cd D:\projetos-bruno\projeto-PokerVision-AI-Coach\PokerVision-AI-Coach
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pokervision
```

O ambiente `.venv` deste checkout já foi criado e as dependências instaladas. Para abrir agora basta executar a última linha, ou dar dois cliques em `iniciar.bat`. A instalação requer internet; jogar, testar e consultar o histórico não requerem internet, GPU, Ollama ou serviços pagos.

## Como jogar

1. Abra **Jogar Cash Game** e pressione **Nova mão**.
2. Espere a ação dos bots. Sua vez aparece em verde na mesa e habilita os botões.
3. Use Fold, Check, Call, Bet / Raise ou All-in. O campo **Total** e a barra representam o total da sua aposta na rodada, incluindo fichas já apostadas nela. O menor total permitido é ajustado automaticamente; um all-in curto pode ficar abaixo do raise mínimo.
4. Ao terminar, o histórico mostra showdown, categoria das mãos e distribuição de fichas. Pressione **Nova mão** para continuar com os mesmos stacks e o botão avançado.
5. Em **Configurações**, entre mãos, altere blinds, stack em BB, seu assento, rake e modo. Aplicar configurações abre uma nova sessão; recompor adiciona apenas fichas que faltam para o stack escolhido. Com menos de dois stacks positivos, recomponha.
6. **Analisar mãos** consulta mãos concluídas, inclusive após reiniciar o aplicativo. É uma consulta textual; reprodução interativa de cada decisão pertence à Fase 3.

## Entregue

- Interface PySide6 escura, redimensionável e com tela cheia, mesa 6-max, animação leve de distribuição, cartas/naipes, botão/blinds, jogador da vez, barra de apostas e histórico.
- Motor no-limit desacoplado, pré-flop até showdown, exceções heads-up, posições vagas, mínimo de raise, all-in curto, reabertura cumulativa de apostas, potes laterais, devolução não coberta, empates e odd chip à esquerda do dealer.
- Cinco adversários com perfis heurísticos e acesso apenas às próprias cartas e informações públicas. Distribuição sem ajuste baseado no usuário.
- Avaliação exata de cinco a sete cartas em Python, Monte Carlo reproduzível contra mãos uniformes, pot odds, SPR e EV de call sob hipótese explícita. Pydantic valida o resultado de equity.
- Dicas determinísticas de pot odds em Aprendizagem. Avaliação oculta essas dicas durante a mão; ainda não gera revisão estratégica ou nota de desempenho.
- Blinds/stacks fictícios configuráveis, rake opcional com teto, recomposição entre mãos e sessões/mãos em SQLite com migração versionada.

## Verificação

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pip check
```

Os testes incluem baralho, categorias/desempate, ações ilegais sem mutação, blinds e heads-up, all-ins e reabertura, side pots, split/odd chip, rake, equity, migração e reabertura do banco, privacidade da observação dos bots, sessões simuladas e uma mão completa por controles da interface. O teste GUI usa Qt offscreen, sem exigir uma janela na sua área de trabalho. Produz `artifacts/mesa-validada.png`. Isso verifica a integração do aplicativo, mas não substitui testes manuais de usabilidade ou certificação de todas as regras.

Dependências diretas validadas: PySide6 6.12.0, Pydantic 2.14.1, pytest 9.2.0. `requirements-lock.txt` registra as versões do ambiente de validação.

## Limitações reais e próximos passos

- Bots não usam solver, GTO, Monte Carlo ou ranges calibrados; usam força da mão, preço, posição aproximada, número de adversários e perfis. Não há níveis de dificuldade selecionáveis. O histórico é observável, mas ainda não alimenta inferências de ranges.
- Equity está disponível na API matemática, não calculada automaticamente na mesa. Monte Carlo em Python é mais lento em cenários grandes; não execute amostragens extensas na thread gráfica. Erro padrão mede apenas erro de amostragem sob o modelo uniforme, não incerteza sobre ranges reais.
- `eval7` é opcional para experimentação; não é usado nem validado nesta entrega. O avaliador Python é o fallback funcional escolhido para evitar compilação nativa. NumPy/OpenCV/OCR e psutil não são dependências desta fase.
- Rake fictício: apenas com flop, pontos-base aplicados por pote, arredondamento para baixo, teto por mão; devoluções não sofrem rake. Não modela regras de salas específicas. Não há antes no Cash Game deste MVP.
- Mãos em andamento não são retomadas após encerrar. O fechamento pede confirmação se a mão não terminou. Mãos concluídas são salvas imediatamente e não são removidas ao iniciar uma sessão.
- Sem replayer por ação, exercícios, métricas de aprendizagem, Tournament Readiness Score, bankroll educacional, torneios, ICM, visão computacional ou IA Ollama. As fases estão em `docs/ROADMAP.md`.
- Sem avatares ilustrados, animações de fichas, empacotamento `.exe`, instalador, benchmark GTX 1650 ou validação em outras versões de Python.
- O programa não captura tela, não importa PokerCraft, não interage com clientes de poker nem contas reais. Feche-o antes de abrir GGPoker ou outro cliente de poker real.

## Dados e arquitetura

Banco: `data/pokervision.sqlite3`, relativo à pasta de execução; o iniciador fixa a pasta do projeto. Para backup, feche o aplicativo e copie esse arquivo. Não apague a pasta `data` ao atualizar. Testes usam bancos temporários separados.

A arquitetura, invariantes e plano técnico estão em `docs/ARCHITECTURE.md`. Referência oficial de instalação do Qt: https://doc.qt.io/qtforpython-6/gettingstarted.html
