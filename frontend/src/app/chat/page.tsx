'use client'

import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { MessageCircle, ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { useInventory } from '@/hooks/use-inventory'
import { useProducts } from '@/hooks/use-products'
import { useChatQuery } from '@/hooks/use-chat'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hi! Ask me about inventory, sales, purchasing, or type a question.' },
  ])
  const [input, setInput] = useState('')
  const { summary: inventorySummary } = useInventory()
  const { products } = useProducts()
  const chat = useChatQuery()

  const renderStructured = (m: Message) => {
    try {
      const marker = '__JSON__'
      if (m.content.startsWith(marker)) {
        const parsed = JSON.parse(m.content.slice(marker.length))
        return (
          <div className="space-y-2">
            <div className="font-medium">{parsed.title}</div>
            <div className="text-sm text-muted-foreground">{parsed.answer_summary}</div>
            {parsed.data?.rows?.length > 0 && (
              <div className="overflow-auto border rounded-md">
                <table className="text-xs w-full">
                  <thead className="bg-muted">
                    <tr>
                      {parsed.data.columns.map((c: any) => <th key={c.name} className="p-1 text-left font-medium">{c.name}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {parsed.data.rows.slice(0,10).map((r: any, i: number) => (
                      <tr key={i} className="odd:bg-muted/40">
                        {parsed.data.columns.map((c: any) => <td key={c.name} className="p-1 align-top">{String(r[c.name])}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {parsed.data.rows.length > 10 && <div className="text-[10px] p-1 text-muted-foreground">Showing first 10 of {parsed.data.rows.length} rows</div>}
              </div>
            )}
            <div className="text-[10px] text-muted-foreground flex gap-2">
              <span>conf: {parsed.confidence.level}</span>
              <span>src: {parsed.source}</span>
              {parsed.query_explainer?.sql && <span className="truncate max-w-[200px]" title={parsed.query_explainer.sql}>sql</span>}
            </div>
          </div>
        )
      }
    } catch {}
    return m.content
  }

  const send = async () => {
    if (!input.trim()) return
    const userMsg: Message = { role: 'user', content: input.trim() }
    setMessages((m) => [...m, userMsg])
    setInput('')
    
    chat.mutate(
      { prompt: userMsg.content },
      {
        onSuccess: (data) => {
          const packed = { ...data }
          setMessages(m => [...m, { role: 'assistant', content: '__JSON__' + JSON.stringify(packed) }])
        },
        onError: (err: any) => {
          setMessages(m => [...m, { role: 'assistant', content: err?.response?.data?.detail?.error || err.message }])
        }
      }
    )
  }

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Chat Assistant</h1>
        <p className="text-muted-foreground">Ask questions about inventory and sales</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5" />
            Assistant
          </CardTitle>
          <CardDescription>Lightweight demo chat</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-72 overflow-y-auto border rounded-md p-3 mb-4 bg-muted/30">
            <div className="space-y-3">
              {messages.map((m, i) => (
                <div key={i} className={`${m.role === 'user' ? 'text-right' : 'text-left'}`}>
                  <div className={`inline-block rounded-md px-3 py-2 text-sm max-w-[90%] whitespace-pre-wrap ${
                    m.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-background border'
                  }`}>
                    {renderStructured(m)}
                  </div>
                </div>
              ))}
              {chat.isPending && (
                <div className="text-left">
                  <div className="inline-block rounded-md px-3 py-2 text-xs bg-background border italic text-muted-foreground">Thinking...</div>
                </div>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Input
              placeholder="Ask about products, stockouts, etc."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              disabled={chat.isPending}
            />
            <Button onClick={send} disabled={chat.isPending || !input.trim()}>Send</Button>
          </div>
          {messages.length === 1 && (
            <div className="text-[10px] text-muted-foreground mt-2">
              Examples: "top products by margin", "stockout risk", "week in review", "reorder suggestions"
            </div>
          )}
        </CardContent>
      </Card>

      <div className="mt-8">
        <Button variant="ghost" asChild>
          <Link href="/dashboard">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Home
          </Link>
        </Button>
      </div>
    </div>
  )
}


