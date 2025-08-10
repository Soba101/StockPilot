'use client'

import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { MessageCircle, ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { Input } from '@/components/ui/input'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hi! Ask me about inventory, sales, or purchasing.' },
  ])
  const [input, setInput] = useState('')

  const send = async () => {
    if (!input.trim()) return
    const userMsg: Message = { role: 'user', content: input.trim() }
    setMessages((m) => [...m, userMsg])
    setInput('')
    // Demo assistant response
    setTimeout(() => {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: `You said: "${userMsg.content}". Insight: Blue Widget is trending.` },
      ])
    }, 400)
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
                  <div className={`inline-block rounded-md px-3 py-2 text-sm ${
                    m.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-background border'
                  }`}>
                    {m.content}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <Input
              placeholder="Ask about products, stockouts, etc."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
            />
            <Button onClick={send}>Send</Button>
          </div>
        </CardContent>
      </Card>

      <div className="mt-8">
        <Button variant="ghost" asChild>
          <Link href="/">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Home
          </Link>
        </Button>
      </div>
    </div>
  )
}


