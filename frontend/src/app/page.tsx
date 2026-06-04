'use client'

import { useRealtime } from '@/lib/hooks/useRealtime'
import { RoomCard } from '@/components/RoomCard'

export default function Dashboard() {
  const { rooms, connected } = useRealtime()

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Jolteon IoT</h1>
            <p className="text-gray-500 text-sm mt-1">Monitoramento de salas em tempo real</p>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-400'}`} />
            <span className="text-gray-500">{connected ? 'Conectado' : 'Reconectando...'}</span>
          </div>
        </div>

        {rooms.length === 0 ? (
          <div className="text-center py-24 text-gray-400">
            <p className="text-lg">Nenhuma sala detectada.</p>
            <p className="text-sm mt-2">Aguardando dados do ESP32...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {rooms.map((room) => (
              <RoomCard key={room.sala_id} room={room} />
            ))}
          </div>
        )}
      </div>
    </main>
  )
}
