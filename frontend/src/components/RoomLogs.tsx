'use client'

import { useEffect, useRef, useState } from 'react'
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

interface LogEntry {
  timestamp: string
  mensagem: string
}

interface Props {
  salaId: string
}

export function RoomLogs({ salaId }: Props) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch(`${BASE_URL}/rooms/${salaId}/logs`, {
      headers: { 'X-API-Key': process.env.NEXT_PUBLIC_API_KEY ?? '' },
    })
      .then((r) => r.json())
      .then((data) => Array.isArray(data) ? setLogs(data) : null)
      .catch(() => null)
  }, [salaId])

  useEffect(() => {
    const url = `${BASE_URL}/events`
    const es = new EventSource(url)

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.tipo === 'log' && data.sala_id === salaId) {
          setLogs((prev) => [{ timestamp: data.timestamp, mensagem: data.mensagem }, ...prev].slice(0, 50))
        }
      } catch {}
    }

    return () => es.close()
  }, [salaId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const formatTime = (iso: string) =>
    new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  return (
    <div className="bg-white rounded-2xl shadow p-6">
      <h2 className="text-base font-semibold text-gray-700 mb-4">Logs do ESP32</h2>
      {logs.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-4">Aguardando logs...</p>
      ) : (
        <div className="font-mono text-xs bg-gray-950 text-green-400 rounded-xl p-4 max-h-64 overflow-y-auto space-y-1">
          {[...logs].reverse().map((log, i) => (
            <div key={i}>
              <span className="text-gray-500">[{formatTime(log.timestamp)}]</span>{' '}
              {log.mensagem}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}
