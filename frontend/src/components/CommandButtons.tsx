'use client'

import { useState } from 'react'
import { sendCommand } from '@/lib/api'
import { BulbIcon, PowerIcon, CheckCircleIcon } from '@/components/icons'
import type { Comando } from '@/types/room'

interface Props {
  salaId: string
}

export function CommandButtons({ salaId }: Props) {
  const [loading, setLoading] = useState<Comando | null>(null)
  const [feedback, setFeedback] = useState<{ text: string; ok: boolean } | null>(null)

  async function handleCommand(comando: Comando) {
    setLoading(comando)
    setFeedback(null)
    try {
      await sendCommand(salaId, comando)
      setFeedback({ text: `Comando ${comando} enviado com sucesso.`, ok: true })
    } catch {
      setFeedback({ text: 'Erro ao enviar comando.', ok: false })
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-3">
        <button
          onClick={() => handleCommand('ON')}
          disabled={loading !== null}
          className="flex-1 flex items-center justify-center gap-3 bg-green-600 hover:bg-green-700 active:bg-green-800 disabled:opacity-60 text-white rounded-xl py-4 px-5 transition-colors"
        >
          <BulbIcon size={20} />
          <div className="text-left">
            <div className="text-sm font-bold tracking-wide leading-tight">
              {loading === 'ON' ? 'Enviando...' : 'LIGAR'}
            </div>
            <div className="text-xs font-normal opacity-80 leading-tight">Acender a luz</div>
          </div>
        </button>

        <button
          onClick={() => handleCommand('OFF')}
          disabled={loading !== null}
          className="flex-1 flex items-center justify-center gap-3 bg-red-600 hover:bg-red-700 active:bg-red-800 disabled:opacity-60 text-white rounded-xl py-4 px-5 transition-colors"
        >
          <PowerIcon />
          <div className="text-left">
            <div className="text-sm font-bold tracking-wide leading-tight">
              {loading === 'OFF' ? 'Enviando...' : 'DESLIGAR'}
            </div>
            <div className="text-xs font-normal opacity-80 leading-tight">Apagar a luz</div>
          </div>
        </button>
      </div>

      {feedback && (
        <div
          className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 transition-all ${
            feedback.ok
              ? 'text-green-700 bg-green-50 border border-green-200'
              : 'text-red-700 bg-red-50 border border-red-200'
          }`}
        >
          {feedback.ok ? (
            <CheckCircleIcon />
          ) : (
            <span className="w-3.5 h-3.5 rounded-full border-2 border-red-500 shrink-0" />
          )}
          {feedback.text}
        </div>
      )}
    </div>
  )
}
