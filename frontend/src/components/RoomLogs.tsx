'use client'

import { useEffect, useRef, useState } from 'react'
import { FilterIcon, SearchIcon, TrashIcon } from '@/components/icons'
import type { LogEntry, LogTipo } from '@/types/room'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? ''

const LOG_STYLE: Record<LogTipo, { dot: string; text: string }> = {
  remoto:       { dot: 'bg-red-400',   text: 'text-red-400' },
  luminosidade: { dot: 'bg-green-400', text: 'text-green-400' },
  movimento:    { dot: 'bg-blue-400',  text: 'text-blue-400' },
  alerta:       { dot: 'bg-amber-400', text: 'text-amber-400' },
  sistema:      { dot: 'bg-slate-400', text: 'text-slate-400' },
}

const FALLBACK_STYLE = { dot: 'bg-slate-500', text: 'text-slate-300' }

interface Props {
  salaId: string
}

export function RoomLogs({ salaId }: Props) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [autoScroll, setAutoScroll] = useState(true)
  const [search, setSearch] = useState('')
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
    const es = new EventSource(`${BASE_URL}/events`)

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        // data.tipo is the SSE event kind; data.log_tipo is the log category
        if (data.tipo === 'log' && data.sala_id === salaId) {
          const entry: LogEntry = {
            timestamp: data.timestamp,
            mensagem: data.mensagem,
            tipo: data.log_tipo as LogTipo | undefined,
          }
          setLogs((prev) => [entry, ...prev].slice(0, 200))
        }
      } catch {}
    }

    return () => es.close()
  }, [salaId])

  useEffect(() => {
    if (autoScroll) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs, autoScroll])

  const formatTime = (iso: string) =>
    new Date(iso).toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })

  const filtered = search.trim()
    ? logs.filter((l) => l.mensagem.toLowerCase().includes(search.toLowerCase()))
    : logs

  const displayed = [...filtered].reverse()

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="flex items-center gap-3 px-8 py-5 bg-white border-b border-gray-200 shrink-0">
        <h1 className="text-xl font-bold text-gray-900 flex-1">Logs do ESP32</h1>

        <button className="flex items-center gap-1.5 text-sm text-gray-500 border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition-colors">
          <FilterIcon />
          Filtros
        </button>

        <div className="relative">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Buscar nos logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-1.5 text-sm border border-gray-200 rounded-lg w-48 focus:outline-none focus:ring-2 focus:ring-blue-400 placeholder:text-gray-500"
          />
        </div>
      </div>

      {/* Log panel */}
      <div className="flex-1 min-h-0 mx-6 my-4 bg-slate-900 rounded-2xl overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 font-mono text-sm">
          {displayed.length === 0 ? (
            <p className="text-slate-500 text-center py-8">Aguardando logs...</p>
          ) : (
            displayed.map((log, i) => {
              const style = LOG_STYLE[log.tipo as LogTipo] ?? FALLBACK_STYLE
              return (
                <div
                  key={i}
                  className="flex items-start gap-3 py-2.5 border-b border-slate-800 last:border-0"
                >
                  <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${style.dot}`} />
                  <span className="text-slate-500 shrink-0">[{formatTime(log.timestamp)}]</span>
                  <span className={style.text}>{log.mensagem}</span>
                </div>
              )
            })
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-8 py-4 bg-white border-t border-gray-200 shrink-0">
        <div
          role="switch"
          aria-checked={autoScroll}
          onClick={() => setAutoScroll((v) => !v)}
          className="flex items-center gap-2.5 text-sm text-gray-600 cursor-pointer select-none"
        >
          <div
            className={`w-10 h-5 rounded-full relative transition-colors shrink-0 ${
              autoScroll ? 'bg-blue-500' : 'bg-gray-300'
            }`}
          >
            <span
              className={`block w-4 h-4 bg-white rounded-full absolute top-0.5 shadow transition-transform ${
                autoScroll ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </div>
          <span>Auto scroll</span>
        </div>

        <button
          onClick={() => setLogs([])}
          className="flex items-center gap-1.5 text-sm text-gray-500 border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 hover:text-red-500 hover:border-red-200 transition-colors"
        >
          <TrashIcon />
          Limpar logs
        </button>
      </div>
    </div>
  )
}
