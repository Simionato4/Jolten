export interface RoomStatus {
  sala_id: string
  ocupada: boolean
  luminosidade: boolean
  ultimo_movimento: string
  tempo_vazia: number
  uptime?: number
  rssi?: number
  ip?: string
}

export interface RoomHistory {
  timestamp: string
  movimento: number
  luminosidade?: number
}

export type Comando = 'ON' | 'OFF'

export type LogTipo = 'movimento' | 'luminosidade' | 'remoto' | 'alerta' | 'sistema'

export interface LogEntry {
  timestamp: string
  mensagem: string
  tipo?: LogTipo
}
