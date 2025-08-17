'use client'

import Link from 'next/link'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { useChatQuery } from '@/hooks/use-chat'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface ChatColumn {
  name: string
  type: string
}

interface ChatData {
  columns: ChatColumn[]
  rows: Record<string, unknown>[]
}

interface ChatResponse {
  title: string
  answer_summary: string
  data?: ChatData
  confidence: { level: string }
  source: string
  query_explainer?: { sql?: string }
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hi! Ask me about inventory, sales, purchasing, or type a question.' },
  ])
  const [input, setInput] = useState('')
  const chat = useChatQuery()

  const renderStructured = (m: Message) => {
    try {
      const marker = '__JSON__'
      if (m.content.startsWith(marker)) {
        const parsed: ChatResponse = JSON.parse(m.content.slice(marker.length))
        return (
          <div className="space-y-2">
            <div className="font-medium">{parsed.title}</div>
            <div className="text-sm text-muted-foreground">{parsed.answer_summary}</div>
            {parsed.data?.rows?.length > 0 && (
              <div className="overflow-auto border rounded-md">
                <table className="text-xs w-full">
                  <thead className="bg-muted">
                    <tr>
                      {parsed.data.columns.map((c) => <th key={c.name} className="p-1 text-left font-medium">{c.name}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {parsed.data.rows.slice(0,10).map((r, i: number) => (
                      <tr key={i} className="odd:bg-muted/40">
                        {parsed.data.columns.map((c) => <td key={c.name} className="p-1 align-top">{String(r[c.name])}</td>)}
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
    
    // For non-JSON responses, render as markdown
    return (
      <div className="prose prose-sm max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            // Custom styling for markdown elements
            p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
            strong: ({ children }) => <strong className="font-bold text-foreground">{children}</strong>,
            em: ({ children }) => <em className="italic">{children}</em>,
            ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1 ml-4">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1 ml-4">{children}</ol>,
            li: ({ children }) => <li className="text-sm leading-relaxed">{children}</li>,
            h1: ({ children }) => <h1 className="text-xl font-bold mb-3 text-foreground">{children}</h1>,
            h2: ({ children }) => <h2 className="text-lg font-bold mb-3 text-foreground">{children}</h2>,
            h3: ({ children }) => <h3 className="text-base font-bold mb-2 text-foreground">{children}</h3>,
            h4: ({ children }) => <h4 className="text-sm font-bold mb-2 text-foreground">{children}</h4>,
            code: ({ children }) => <code className="bg-muted px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>,
            pre: ({ children }) => <pre className="bg-muted p-3 rounded text-xs overflow-x-auto font-mono">{children}</pre>,
            table: ({ children }) => (
              <div className="overflow-x-auto my-4">
                <table className="w-full border-collapse border border-border text-sm">
                  {children}
                </table>
              </div>
            ),
            thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
            th: ({ children }) => <th className="border border-border p-2 font-semibold text-left">{children}</th>,
            td: ({ children }) => <td className="border border-border p-2">{children}</td>,
            tr: ({ children }) => <tr className="even:bg-muted/20">{children}</tr>,
            blockquote: ({ children }) => <blockquote className="border-l-4 border-primary pl-4 py-2 my-3 bg-muted/30 italic">{children}</blockquote>,
          }}
        >
          {m.content}
        </ReactMarkdown>
      </div>
    )
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
        onError: (err: Error) => {
          setMessages(m => [...m, { role: 'assistant', content: (err as Error & { response?: { data?: { detail?: { error?: string } } } })?.response?.data?.detail?.error || err.message }])
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
        <h1 className="text-3xl font-bold">StockPilot Assistant</h1>
        <p className="text-muted-foreground">Ask questions about inventory and sales</p>
      </div>

      <Card>
        <CardHeader>
        </CardHeader>
        <CardContent>
          <div className="h-[520px] md:h-[1000px] overflow-y-auto border rounded-md p-3 mb-4 bg-muted/30">
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
              Examples: &ldquo;top products by margin&rdquo;, &ldquo;stockout risk&rdquo;, &ldquo;week in review&rdquo;, &ldquo;reorder suggestions&rdquo;
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


