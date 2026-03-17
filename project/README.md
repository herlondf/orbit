# OctoChat Project

Esqueleto inicial do produto `OctoChat` no recorte `R0`.

## Objetivo desta base
- Materializar a UI inicial do shell multichat.
- Preparar o contrato `Tauri v2 + React`.
- Validar a pasta `src-tauri/` no host Windows real com Rust/MSVC.
- Persistir localmente o workspace operacional do operador.

## Comandos
- `npm install`
- `npm run dev`
- `npm run build`
- `npm run tauri:dev`
- `npm run tauri:build`
- `build_windows.bat`
- `build_windows.bat --skip-install`

## Host validado
- O host Windows ja possui `WebView2`, `Rust stable-msvc` e Microsoft C++ Build Tools.
- `cargo check --manifest-path src-tauri/Cargo.toml` ja foi validado no ambiente MSVC.
- `npm run tauri:dev` ja compilou e executou `target/debug/octochat.exe` no host.

## Foco do R0
- Sidebar operacional de servicos.
- Contrato de contas/perfis isolados.
- Palco visual para webviews por servico.
- Preparacao para tray, notificacoes e observabilidade local.

## Estado atual do R0
- `src/App.tsx`: shell multichat com busca, fixacao de servicos, focus mode, telemetria visual e snapshot persistido em `localStorage`.
- `src/contracts.ts`: contrato do workspace, servicos, contas e preferencias do operador.
- `src/storage.ts`: persistencia local do snapshot do workspace.
- `src-tauri/src/lib.rs`: comandos iniciais `runtime_probe` e `build_session_contract` para o runtime Tauri.
- `src/serviceHost.ts`: host inicial de webviews reais por conta, via `WebviewWindow`, com `dataDirectory` segregado por sessao e operacoes em lote por servico.
- `src/desktopShell.ts`: base nativa de tray e notificacoes para o shell desktop.
- `src/App.tsx`: restaura sessoes vivas persistidas, sincroniza o shell com webviews abertas, opera abertura/fechamento em lote por servico e exibe trilha de eventos do runtime para validacao manual.
- `src-tauri/app-icon.svg` + `src-tauri/icons/`: icones do app gerados para permitir build/dev real no Windows.
- `.gitignore`: passa a ignorar `src-tauri/target` e `src-tauri/gen` para evitar ruido de build da issue.
- `build_windows.bat`: prepara MSVC + Rust no host Windows e dispara `npm run tauri:build` para gerar o `.exe` e os bundles do app.

## Limite ainda aberto
- O runtime Tauri ja compila e executa no host Windows, mas o centro da UI principal ainda e um slot visual; as webviews reais ainda abrem como janelas dedicadas por conta.
- O shell ja consegue solicitar abertura/fechamento de webviews reais por conta e por servico, com restauracao de sessoes vivas persistidas e reconciliacao operacional visivel no log, mas a validacao interativa desse comportamento ainda precisa ser feita manualmente no app rodando.
- Tray e notificacoes ja tem base nativa no shell, mas a validacao funcional no app rodando continua pendente.
- O proximo salto de produto e decidir entre manter multi-janela operacional ou mover para composicao mais integrada de multiplas webviews simultaneas no shell principal.
