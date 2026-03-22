# Checkpoint - OctoChat
_Atualizado em: 2026-03-20 15:30 UTC_

## Concluido
- Catálogo de 12 serviços (Slack, WhatsApp, Telegram, Discord, Gmail, Google Chat, Google Agenda, Meet, Teams, Outlook, Notion, Linear).
- Tipos refatorados: serviceType, hibernateAfter, migração de snapshots antigos.
- **UI estilo Ferdium/Rambox**: sidebar com ícones de serviço + badges de não-lidos + content area com tabs de contas.
- **Webviews embarcadas** no main window via `Window::add_child()` (Tauri feature `unstable`).
- Webviews criadas preguiçosamente (na primeira ativação da conta), mostradas/escondidas com show/hide.
- ResizeObserver mantém os bounds de todas as webviews alinhados com a content-area.
- Init script injetado em cada webview: intercepta Notification API e policia title para badges.
- Relay de notificações (webview:notification) e títulos (webview:title) via IPC para o shell.
- Lógica de hibernação por conta baseada em lastFocusedAt.
- Modais: adicionar serviço (2 passos: catálogo → form), adicionar conta, config panel inline por serviço.
- Dark theme (Catppuccin) com tooltip nativo no sidebar.
- Build release gerado: OctoChat_0.1.0_x64_en-US.msi e OctoChat_0.1.0_x64-setup.exe.

## Proximo Passo
- Instalar e validar: sidebar, webviews embarcadas, tabs de conta, badges, hibernação, notificações.

## Impedimentos
- nenhum
