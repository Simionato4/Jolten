'use client'

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
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
    horaCompleta: new Date(d.timestamp).toLocaleTimeString('pt-BR'),
    ocupado: d.movimento,
    fundo: 1,
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={formatted} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="gradOcupado" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#22c55e" stopOpacity={0.55} />
            <stop offset="100%" stopColor="#22c55e" stopOpacity={0.08} />
          </linearGradient>
        </defs>

        <XAxis
          dataKey="hora"
          tick={{ fontSize: 11 }}
          interval="preserveStartEnd"
          minTickGap={60}
        />
        <YAxis
          domain={[0, 1]}
          ticks={[0, 1]}
          tick={{ fontSize: 11 }}
          tickFormatter={(v) => (v === 1 ? 'Ocupado' : 'Vazio')}
          width={56}
        />

        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const item = payload[0]?.payload as { horaCompleta: string; ocupado: number }
            const ocupado = item?.ocupado === 1
            return (
              <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 shadow-md text-sm">
                <p className="text-gray-400 text-xs mb-1">{item?.horaCompleta}</p>
                <p className={`font-semibold ${ocupado ? 'text-green-600' : 'text-gray-400'}`}>
                  {ocupado ? '● Ocupada' : '○ Vazia'}
                </p>
              </div>
            )
          }}
        />

        {/* Cinza de fundo — sempre preenchido até 1, representa o estado Vazio */}
        <Area
          type="stepAfter"
          dataKey="fundo"
          stroke="none"
          fill="#e5e7eb"
          strokeWidth={0}
          dot={false}
          isAnimationActive={false}
          legendType="none"
        />

        {/* Verde — sobrepõe o cinza apenas quando ocupado=1 */}
        <Area
          type="stepAfter"
          dataKey="ocupado"
          stroke="#22c55e"
          fill="url(#gradOcupado)"
          strokeWidth={2}
          dot={false}
          legendType="none"
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
