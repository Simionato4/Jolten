'use client'

import { use } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { fetcher } from '@/lib/api'
import { OccupancyChart } from '@/components/OccupancyChart'
import { CommandButtons } from '@/components/CommandButtons'
import type { RoomStatus, RoomHistory } from '@/types/room'

interface Props {
  params: Promise<{ id: string }>
}

export default function RoomDetail({ params }: Props) {
  const { id } = use(params)

  const { data: room } = useSWR<RoomStatus>(`/rooms/${id}`, fetcher, { refreshInterval: 5000 })
  const { data: history } = useSWR<RoomHistory[]>(`/rooms/${id}/history?range_minutes=60`, fetcher, { refreshInterval: 30000 })

  const minutos = room ? Math.floor(room.tempo_vazia / 60) : 0
  const segundos = room ? room.tempo_vazia % 60 : 0

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto">
        <Link href="/" className="text-sm text-gray-400 hover:text-gray-600 mb-6 inline-block">
          ← Voltar
        </Link>

        <h1 className="text-3xl font-bold text-gray-900 mb-6">Sala {id}</h1>

        {room ? (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow p-6 grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-400">Ocupação</p>
                <p className={`text-lg font-semibold ${room.ocupada ? 'text-green-600' : 'text-gray-500'}`}>
                  {room.ocupada ? 'Ocupada' : 'Vazia'}
                </p>
              </div>
              <div>
                <p className="text-gray-400">Iluminação</p>
                <p className={`text-lg font-semibold ${room.luminosidade ? 'text-yellow-500' : 'text-gray-500'}`}>
                  {room.luminosidade ? 'Ligada' : 'Desligada'}
                </p>
              </div>
              <div>
                <p className="text-gray-400">Vazia há</p>
                <p className="text-lg font-semibold">{minutos}m {segundos}s</p>
              </div>
              <div>
                <p className="text-gray-400">Último movimento</p>
                <p className="text-lg font-semibold">
                  {new Date(room.ultimo_movimento).toLocaleTimeString('pt-BR')}
                </p>
              </div>
            </div>

            <div className="bg-white rounded-2xl shadow p-6">
              <h2 className="text-base font-semibold text-gray-700 mb-4">Histórico — última hora</h2>
              {history && history.length > 0
                ? <OccupancyChart data={history} />
                : <p className="text-sm text-gray-400 text-center py-8">Sem dados históricos ainda.</p>
              }
            </div>

            <div className="bg-white rounded-2xl shadow p-6">
              <h2 className="text-base font-semibold text-gray-700 mb-4">Controle remoto</h2>
              <CommandButtons salaId={id} />
            </div>
          </div>
        ) : (
          <p className="text-gray-400">Carregando...</p>
        )}
      </div>
    </main>
  )
}
