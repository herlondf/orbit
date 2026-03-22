export type ServiceCatalogEntry = {
  type: string
  name: string
  icon: string
  color: string
  defaultUrl: string
  description: string
}

export const serviceCatalog: ServiceCatalogEntry[] = [
  {
    type: 'slack',
    name: 'Slack',
    icon: 'SL',
    color: '#d46d2a',
    defaultUrl: 'https://app.slack.com/',
    description: 'Mensageiro corporativo',
  },
  {
    type: 'whatsapp',
    name: 'WhatsApp',
    icon: 'WA',
    color: '#2e936d',
    defaultUrl: 'https://web.whatsapp.com/',
    description: 'Mensageiro pessoal e business',
  },
  {
    type: 'telegram',
    name: 'Telegram',
    icon: 'TG',
    color: '#2a8dc5',
    defaultUrl: 'https://web.telegram.org/a/',
    description: 'Mensageiro com canais e bots',
  },
  {
    type: 'discord',
    name: 'Discord',
    icon: 'DC',
    color: '#456ae6',
    defaultUrl: 'https://discord.com/app',
    description: 'Comunidades e voz',
  },
  {
    type: 'gmail',
    name: 'Gmail',
    icon: 'GM',
    color: '#b95d4b',
    defaultUrl: 'https://mail.google.com/',
    description: 'Email Google',
  },
  {
    type: 'gchat',
    name: 'Google Chat',
    icon: 'GC',
    color: '#1a73e8',
    defaultUrl: 'https://chat.google.com/',
    description: 'Chat corporativo Google',
  },
  {
    type: 'gcalendar',
    name: 'Google Agenda',
    icon: 'GA',
    color: '#4285f4',
    defaultUrl: 'https://calendar.google.com/',
    description: 'Calendário e reuniões',
  },
  {
    type: 'gmeet',
    name: 'Google Meet',
    icon: 'MT',
    color: '#00ac47',
    defaultUrl: 'https://meet.google.com/',
    description: 'Videoconferência Google',
  },
  {
    type: 'teams',
    name: 'Microsoft Teams',
    icon: 'MS',
    color: '#6264a7',
    defaultUrl: 'https://teams.microsoft.com/',
    description: 'Colaboração Microsoft',
  },
  {
    type: 'outlook',
    name: 'Outlook',
    icon: 'OL',
    color: '#0078d4',
    defaultUrl: 'https://outlook.live.com/',
    description: 'Email Microsoft',
  },
  {
    type: 'notion',
    name: 'Notion',
    icon: 'NT',
    color: '#37352f',
    defaultUrl: 'https://www.notion.so/',
    description: 'Notas e documentação',
  },
  {
    type: 'linear',
    name: 'Linear',
    icon: 'LN',
    color: '#5e6ad2',
    defaultUrl: 'https://linear.app/',
    description: 'Gestão de projetos',
  },
  {
    type: 'custom',
    name: 'Personalizado',
    icon: '⚡',
    color: '#6c7086',
    defaultUrl: 'https://',
    description: 'Qualquer site ou webapp',
  },
]

export function getCatalogEntry(type: string): ServiceCatalogEntry | undefined {
  return serviceCatalog.find((entry) => entry.type === type)
}
