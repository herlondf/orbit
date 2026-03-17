# Issue OctoChat

## Problema
- Ferramentas como Rambox concentram muitos mensageiros, mas a base em Electron tende a consumir muita memoria, degradar com varias contas abertas e ficar instavel em uso prolongado.
- O workspace ainda nao tem uma aplicacao desktop multichat leve, governavel e previsivel para consolidar WhatsApp Web, Telegram, Slack, Discord, Gmail/Inbox e outros web apps em um unico shell.

## Objetivo
- Entregar um desktop app multichat mais leve e estavel que Electron para uso diario, com multiplos servicos, sessoes isoladas por conta e operacao previsivel em Windows como prioridade inicial.
- Fechar um MVP que prove ganho de estabilidade, consumo aceitavel de recursos e base tecnica extensivel para plugins, sync e recursos corporativos depois.

## Escopo
- Levantamento e consolidacao dos requisitos funcionais, nao funcionais e restricoes da primeira release.
- Definicao de arquitetura e stack do produto, com trade-offs registrados.
- Planejamento por etapas com entregas incrementais e criterio de promocao entre elas.
- Inicio da implementacao do esqueleto tecnico do produto apos o fechamento do planejamento.

### MVP proposto
- Shell desktop com multiplas webviews/servicos.
- Suporte a varias contas por servico com isolamento de sessao/storage.
- Sidebar com servicos fixados, badges basicos e alternancia rapida.
- Notificacoes nativas e abertura focada do servico/origem.
- Persistencia local de configuracao, layout e estado de sessoes.
- Busca rapida/atalhos principais e bandeja do sistema.
- Base observavel para diagnosticar travamentos e falhas de webview.

### Fase 2+
- Plugins/extensoes por servico.
- Sync opcional de configuracao entre dispositivos.
- Workspaces/perfis corporativos.
- Regras de notificacao, focus mode e automacoes.
- Telemetria opcional, crash reporting e politicas de rollout.

## Fora de Escopo
- Implementar sync em nuvem no MVP.
- Suportar Linux/macOS logo na primeira entrega; o alvo inicial e Windows.
- Criar integracoes nativas profundas com APIs privadas de cada mensageiro.
- Resolver bloqueios impostos por mudancas dos web apps de terceiros.

## Criterios de Aceite
- [ ] Requisitos do MVP, fases seguintes e restricoes estao documentados de forma objetiva.
- [ ] A stack inicial foi definida com justificativa tecnica e trade-offs claros.
- [ ] O plano de execucao foi quebrado em etapas pequenas, com proximo passo unico.
- [ ] Existe uma arquitetura base definida para iniciar o esqueleto do produto.

## Etapas
- `triage`: consolidar problema, escopo, restricoes e hipotese de produto.
- `analysis`: comparar stacks e fechar a arquitetura base.
- `planning`: decompor MVP em milestones e definir criterio de promocao.
- `implementation`: abrir o projeto e entregar shell inicial, webviews e persistencia.
- `verification`: validar consumo, estabilidade, notificacoes e fluxo operacional.

## Stack Inicial Recomendada
- **Desktop shell**: `Tauri v2` com `Rust`.
- **UI**: `React + TypeScript + Vite`.
- **Estado/persistencia**: store local no app + keychain/segredo nativo para material sensivel.
- **Empacotamento Windows**: toolchain padrao do Tauri.

### Motivo da escolha
- `Tauri` usa a webview nativa do sistema, reduzindo overhead frente a um runtime Chromium embarcado completo.
- `Tauri v2` suporta multiplas webviews/janelas e plugins oficiais para capacidades relevantes do shell desktop.
- `Rust` e um backend enxuto e previsivel para orquestrar sessoes, notificacoes, bandeja e integracoes nativas, sem assumir a fragilidade de Electron.
- `React + TypeScript` acelera a camada de produto sem acoplar a UI ao backend.

### Alternativas descartadas neste momento
- `Electron`: maior ecossistema, mas vai contra a meta principal de leveza/estabilidade.
- `Wails`: interessante para desktop leve, mas o ecossistema e a superficie pronta para plugins/capacidades de shell ainda parecem menos maduros para um multichat com varias integrações.
- `Flutter Desktop`: forte para UI nativa, mas menos aderente ao caso em que o core do produto e orquestrar varios web apps/webviews.

## Arquitetura Base
- `shell`: janela principal, system tray, atalhos, lifecycle e notificacoes.
- `workspace manager`: cadastro de servicos, contas, perfis e layout.
- `session manager`: isola storage/cookies por conta e controla ciclo de vida das webviews.
- `service host`: cria/descarta webviews e aplica politicas por servico.
- `renderer`: sidebar, area de tabs, badges, busca rapida e configuracoes.
- `observability`: logs locais, erros de carregamento e eventos de runtime.

## Backlog Inicial
- `R0`: discovery tecnico e prova de conceito de multiwebview + isolamento de sessao.
- `R1`: shell MVP com sidebar, cadastro de servicos e persistencia local.
- `R2`: notificacoes, tray, atalhos e UX minima operacional.
- `R3`: hardening de estabilidade, consumo e instalacao Windows.

## Referencias
- Tauri v2 docs: https://v2.tauri.app/
- Tauri window/webview APIs: https://v2.tauri.app/reference/javascript/api/namespacewebviewwindow/
- Tauri plugins: https://v2.tauri.app/plugin/
- Wails docs: https://wails.io/docs/introduction
- Flutter desktop docs: https://docs.flutter.dev/platform-integration/desktop
