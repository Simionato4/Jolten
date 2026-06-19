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
    movimento: d.movimento,
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={formatted} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="gradMovimento" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="hora" tick={{ fontSize: 11 }} interval="preserveStartEnd" minTickGap={40} />
        <YAxis
          domain={[0, 1]}
          ticks={[0, 1]}
          tick={{ fontSize: 11 }}
          tickFormatter={(v) => (v === 1 ? 'Ocupado' : 'Vazio')}
          width={56}
        />
        <Tooltip
          formatter={(v: unknown) => [v === 1 ? 'Ocupada' : 'Vazia', 'Estado']}
        />
        <Area
          type="stepAfter"
          dataKey="movimento"
          stroke="#22c55e"
          fill="url(#gradMovimento)"
          strokeWidth={2}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
