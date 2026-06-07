'use client'

import { useEffect, useRef, useState } from 'react'
import type { RoomStatus } from '@/types/room'

const BASE = process.env.NEXT_PUBLIC_API_URL

export function useRealtime() {
  const [rooms, setRooms] = useState<RoomStatus[]>([])
  const [connected, setConnected] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  // Pré-carrega salas via REST para evitar flash de "Nenhuma sala" enquanto SSE conecta
  useEffect(() => {
    fetch(`${BASE}/rooms`)
      .then((r) => r.json())
      .then((data) => { if (Array.isArray(data) && data.length > 0) setRooms(data) })
      .catch(() => null)
  }, [])

  useEffect(() => {
    function connect() {
      const es = new EventSource(`${BASE}/events`)
      esRef.current = es

      es.onopen = () => setConnected(true)

      es.onmessage = (e) => {
        const data = JSON.parse(e.data)

        if (data.tipo === 'sync') {
          setRooms(data.salas)
          return
        }

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
