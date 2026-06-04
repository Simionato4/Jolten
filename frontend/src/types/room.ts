export interface RoomStatus {
  sala_id: string
  ocupada: boolean
  luminosidade: boolean
  ultimo_movimento: string
  tempo_vazia: number
}

export interface RoomHistory {
  timestamp: string
  movimento: number
  luminosidade?: number
}

export type Comando = 'ON' | 'OFF'
