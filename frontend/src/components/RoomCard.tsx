'use client'

import Link from 'next/link'
import type { RoomStatus } from '@/types/room'

interface Props {
  room: RoomStatus
}

export function RoomCard({ room }: Props) {
  const statusColor = room.ocupada
    ? 'bg-green-500'
    : 'bg-gray-400'

  const minutos = Math.floor(room.tempo_vazia / 60)
  const segundos = room.tempo_vazia % 60
  const tempoLabel = minutos > 0
    ? `${minutos}m ${segundos}s`
    : `${segundos}s`

  return (
    <Link href={`/rooms/${room.sala_id}`}>
      <div className="bg-white rounded-2xl shadow p-6 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-800">Sala {room.sala_id}</h2>
          <span className={`w-3 h-3 rounded-full ${statusColor}`} />
        </div>

        <div className="space-y-2 text-sm text-gray-600">
          <div className="flex justify-between">
            <span>Ocupação</span>
            <span className={`font-medium ${room.ocupada ? 'text-green-600' : 'text-gray-500'}`}>
              {room.ocupada ? 'Ocupada' : 'Vazia'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Iluminação</span>
            <span className={`font-medium ${room.luminosidade ? 'text-yellow-500' : 'text-gray-500'}`}>
              {room.luminosidade ? 'Ligada' : 'Desligada'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Vazia há</span>
            <span className="font-medium">{tempoLabel}</span>
          </div>
        </div>
      </div>
    </Link>
  )
}
