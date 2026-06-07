'use client'

import { use, useState } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { fetcher } from '@/lib/api'
import { OccupancyChart } from '@/components/OccupancyChart'
import { CommandButtons } from '@/components/CommandButtons'
import { RoomLogs } from '@/components/RoomLogs'
import {
  HomeIcon,
  LightningIcon,
  LogsIcon,
  PeopleIcon,
  BulbIcon,
  ClockIcon,
  TimerIcon,
} from '@/components/icons'
import type { RoomStatus, RoomHistory } from '@/types/room'

type Tab = 'controle' | 'logs'

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

interface Props {
  params: Promise<{ id: string }>
}

function StatCard({
  icon,
  iconColor,
  label,
  value,
  valueColor,
}: {
  icon: React.ReactNode
  iconColor: string
  label: string
  value: string
  valueColor?: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 h-22 flex flex-col justify-between">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs text-gray-400 leading-tight">{label}</p>
        <span className={`${iconColor} shrink-0`}>{icon}</span>
      </div>
      <p className={`text-base font-semibold ${valueColor ?? 'text-gray-800'}`}>{value}</p>
    </div>
  )
}

export default function RoomDetail({ params }: Props) {
  const { id } = use(params)
  const [activeTab, setActiveTab] = useState<Tab>('controle')
  const [rangeMinutes, setRangeMinutes] = useState(30)

  const { data: room } = useSWR<RoomStatus>(`/rooms/${id}`, fetcher, { refreshInterval: 5000 })
  const { data: history } = useSWR<RoomHistory[]>(
    `/rooms/${id}/history?range_minutes=${rangeMinutes}`,
    fetcher,
    { refreshInterval: 30000 }
  )

  const minutos = room ? Math.floor(room.tempo_vazia / 60) : 0
  const segundos = room ? room.tempo_vazia % 60 : 0

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-[72px] bg-gray-900 flex flex-col items-center py-4 flex-shrink-0">
        <Link
          href="/"
          className="p-2 rounded-xl text-gray-400 hover:text-white hover:bg-gray-700 transition-colors mb-6"
          title="Início"
        >
          <HomeIcon />
        </Link>

        <nav className="flex flex-col items-center gap-1 flex-1 w-full px-2">
          <button
            onClick={() => setActiveTab('controle')}
            className={`flex flex-col items-center gap-1 py-2 px-1 rounded-xl text-[10px] font-medium transition-colors w-full ${
              activeTab === 'controle'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            <LightningIcon />
            <span>Controle</span>
          </button>

          <button
            onClick={() => setActiveTab('logs')}
            className={`flex flex-col items-center gap-1 py-2 px-1 rounded-xl text-[10px] font-medium transition-colors w-full ${
              activeTab === 'logs'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            <LogsIcon />
            <span>Logs</span>
          </button>
        </nav>

        <img
          src="/jolteon.png"
          alt="Jolteon"
          className="w-10 h-10 rounded-full object-cover object-center"
          style={{ clipPath: 'circle(50%)' }}
        />
      </aside>

      {/* Main content */}
      <main className="flex-1 min-h-0 overflow-hidden bg-gray-50">
        {activeTab === 'controle' ? (
          <div className="h-full overflow-y-auto">
            <div className="p-8 max-w-2xl mx-auto">
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Sala {id}</h1>
                <span className="flex items-center gap-1.5 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-full px-3 py-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  Online
                </span>
              </div>

              {room ? (
                <div className="space-y-5">
                  {/* Stats */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <StatCard
                      icon={<PeopleIcon />}
                      iconColor="text-blue-400"
                      label="Ocupação"
                      value={room.ocupada ? 'Ocupada' : 'Vazia'}
                      valueColor={room.ocupada ? 'text-green-600' : 'text-gray-500'}
                    />
                    <StatCard
                      icon={<BulbIcon size={18} />}
                      iconColor="text-amber-400"
                      label="Iluminação"
                      value={room.luminosidade ? 'Ligada' : 'Desligada'}
                      valueColor={room.luminosidade ? 'text-amber-500' : 'text-gray-500'}
                    />
                    <StatCard
                      icon={<ClockIcon />}
                      iconColor="text-violet-400"
                      label="Último movimento"
                      value={new Date(room.ultimo_movimento).toLocaleTimeString('pt-BR')}
                    />
                    <StatCard
                      icon={<TimerIcon />}
                      iconColor="text-green-400"
                      label="Vazia há"
                      value={`${minutos}m ${segundos}s`}
                    />
                  </div>

                  {/* Chart */}
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h2 className="text-sm font-semibold text-gray-700">Atividade de ocupação</h2>
                      <select
                        value={rangeMinutes}
                        onChange={(e) => setRangeMinutes(Number(e.target.value))}
                        className="text-xs text-gray-600 border border-gray-200 rounded-lg px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                      >
                        <option value={30}>Últimos 30 minutos</option>
                        <option value={60}>Última hora</option>
                        <option value={120}>Últimas 2 horas</option>
                      </select>
                    </div>
                    {history && history.length > 0 ? (
                      <OccupancyChart data={history} />
                    ) : (
                      <p className="text-sm text-gray-400 text-center py-8">Sem dados históricos ainda.</p>
                    )}
                  </div>

                  {/* Controls */}
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
                    <h2 className="text-sm font-semibold text-gray-700 mb-4">Controle remoto</h2>
                    <CommandButtons salaId={id} />
                  </div>

                  {/* Device info */}
                  <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 grid grid-cols-4 gap-4">
                    <div>
                      <p className="text-xs text-gray-400">Dispositivo</p>
                      <p className="text-sm font-medium text-gray-700 mt-0.5">ESP32 - Sala {id}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Uptime</p>
                      <p className="text-sm font-medium text-gray-700 mt-0.5">
                        {room.uptime != null ? formatUptime(room.uptime) : '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Wi-Fi</p>
                      <p className="text-sm font-medium text-gray-700 mt-0.5">
                        {room.rssi != null ? `${room.rssi} dBm` : '—'}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">IP</p>
                      <p className="text-sm font-medium text-gray-700 mt-0.5">
                        {room.ip ?? '—'}
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-5">
                  {/* Skeleton */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <div key={i} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 h-20 animate-pulse">
                        <div className="h-3 bg-gray-100 rounded w-2/3 mb-3" />
                        <div className="h-4 bg-gray-100 rounded w-1/2" />
                      </div>
                    ))}
                  </div>
                  <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 h-64 animate-pulse">
                    <div className="h-4 bg-gray-100 rounded w-1/3 mb-4" />
                    <div className="h-full bg-gray-50 rounded-xl" />
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <RoomLogs salaId={id} />
        )}
      </main>
    </div>
  )
}
