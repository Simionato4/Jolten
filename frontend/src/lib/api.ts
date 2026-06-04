import type { RoomStatus, RoomHistory, Comando } from '@/types/room'

const BASE = process.env.NEXT_PUBLIC_API_URL
const API_KEY = process.env.NEXT_PUBLIC_API_KEY

export const fetcher = (url: string) =>
  fetch(`${BASE}${url}`).then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    return r.json()
  })

export async function sendCommand(salaId: string, comando: Comando): Promise<void> {
  const res = await fetch(`${BASE}/rooms/${salaId}/command`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY ?? '',
    },
    body: JSON.stringify({ comando }),
  })
  if (!res.ok) throw new Error(`Erro ao enviar comando: HTTP ${res.status}`)
}

export type { RoomStatus, RoomHistory }
