'use client'

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import type { RoomHistory } from '@/types/room'

interface Props {
  data: RoomHistory[]
}

export function OccupancyChart({ data }: Props) {
  const formatted = data.map((d) => ({
    hora: new Date(d.timestamp).toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
    }),
    ocupado: d.movimento,
    fundo: 1,
  }))

  const total = formatted.length
  const comMovimento = formatted.filter((d) => d.ocupado === 1).length
  const pct = total > 0 ? Math.round((comMovimento / total) * 100) : 0

  return (
    <div>
      {/* Legend */}
      <div className="flex items-center gap-4 mb-4">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm bg-green-500" />
          <span className="text-xs text-gray-500">Movimento</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm bg-gray-200" />
          <span className="text-xs text-gray-500">Sem movimento</span>
        </div>
        <div className="ml-auto text-xs font-medium text-gray-400">
          {pct}% do período com movimento
        </div>
      </div>

      <ResponsiveContainer width="100%" height={190}>
        <AreaChart data={formatted} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="gradOcupado" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22c55e" stopOpacity={0.8} />
              <stop offset="100%" stopColor="#22c55e" stopOpacity={0.12} />
            </linearGradient>
            <linearGradient id="gradVazio" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#e5e7eb" stopOpacity={0.8} />
              <stop offset="100%" stopColor="#e5e7eb" stopOpacity={0.2} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />

          <XAxis
            dataKey="hora"
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            interval="preserveStartEnd"
            minTickGap={50}
            axisLine={false}
            tickLine={false}
          />

          <YAxis
            domain={[0, 1]}
            ticks={[0, 1]}
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            tickFormatter={(v) => (v === 1 ? 'Sim' : 'Não')}
            width={32}
            axisLine={false}
            tickLine={false}
          />

          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const d = payload[0]?.payload as { hora: string; ocupado: number }
              const mov = d?.ocupado === 1
              return (
                <div className="bg-white border border-gray-100 rounded-xl px-3 py-2.5 shadow-lg">
                  <p className="text-gray-400 text-xs mb-1.5">{d?.hora}</p>
                  <div
                    className={`flex items-center gap-1.5 text-sm font-semibold ${
                      mov ? 'text-green-600' : 'text-gray-400'
                    }`}
                  >
                    <span
                      className={`w-2 h-2 rounded-full shrink-0 ${
                        mov ? 'bg-green-500' : 'bg-gray-300'
                      }`}
                    />
                    {mov ? 'Movimento detectado' : 'Sem movimento'}
                  </div>
                </div>
              )
            }}
          />

          {/* Gray background — always fills to 1, represents "no movement" baseline */}
          <Area
            type="stepAfter"
            dataKey="fundo"
            stroke="none"
            fill="url(#gradVazio)"
            strokeWidth={0}
            dot={false}
            isAnimationActive={false}
            legendType="none"
          />

          {/* Green overlay — rises to 1 only when movement is detected */}
          <Area
            type="stepAfter"
            dataKey="ocupado"
            stroke="#16a34a"
            fill="url(#gradOcupado)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
            legendType="none"
            activeDot={{ r: 4, fill: '#16a34a', stroke: '#fff', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
