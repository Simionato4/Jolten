'use client'

import { useEffect, useRef, useState } from 'react'
import type { RoomStatus } from '@/types/room'

const BASE = process.env.NEXT_PUBLIC_API_URL

export function useRealtime() {
  const [rooms, setRooms] = useState<RoomStatus[]>([])
  const [connected, setConnected] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    function connect() {
      const es = new EventSource(`${BASE}/events`)
      esRef.current = es

      es.onopen = () => setConnected(true)

      es.onmessage = (e) => {
        const data = JSON.parse(e.data)

        // Ressincronização inicial ou reconexão (IMPORT-004)
        if (data.tipo === 'sync') {
          setRooms(data.salas)
          return
        }

        // Atualização incremental de uma sala
        setRooms((prev) => {
          const idx = prev.findIndex((r) => r.sala_id === data.sala_id)
          if (idx === -1) {
            return [...prev, data as RoomStatus]
          }
          const updated = [...prev]
          updated[idx] = { ...updated[idx], ...data }
          return updated
        })
      }

      es.onerror = () => {
        setConnected(false)
        es.close()
        // Reconnect após 3s
        setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      esRef.current?.close()
    }
  }, [])

  return { rooms, connected }
}
