'use client'

import { useState } from 'react'
import { sendCommand } from '@/lib/api'
import type { Comando } from '@/types/room'

interface Props {
  salaId: string
}

export function CommandButtons({ salaId }: Props) {
  const [loading, setLoading] = useState<Comando | null>(null)
  const [feedback, setFeedback] = useState<string | null>(null)

  async function handleCommand(comando: Comando) {
    setLoading(comando)
    setFeedback(null)
    try {
      await sendCommand(salaId, comando)
      setFeedback(`Comando ${comando} enviado com sucesso.`)
    } catch {
      setFeedback('Erro ao enviar comando.')
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
          className="flex-1 bg-yellow-400 hover:bg-yellow-500 disabled:opacity-50 text-white font-semibold py-2 px-4 rounded-xl transition-colors"
        >
          {loading === 'ON' ? 'Enviando...' : '💡 Ligar'}
        </button>
        <button
          onClick={() => handleCommand('OFF')}
          disabled={loading !== null}
          className="flex-1 bg-gray-700 hover:bg-gray-800 disabled:opacity-50 text-white font-semibold py-2 px-4 rounded-xl transition-colors"
        >
          {loading === 'OFF' ? 'Enviando...' : '🛑 Desligar'}
        </button>
      </div>
      {feedback && (
        <p className="text-sm text-center text-gray-600">{feedback}</p>
      )}
    </div>
  )
}
