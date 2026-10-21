import React, { useState, useEffect, useRef } from 'react';
import { Message } from '../../types';
import { api } from '../../services/api';
import { Send, MessageSquare } from 'lucide-react';

interface RealtimeChatProps {
  collaborationId: string;
  recipientId: string;
  currentUserId: string;
}

export const RealtimeChat: React.FC<RealtimeChatProps> = ({
  collaborationId,
  recipientId,
  currentUserId
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load chat history
  useEffect(() => {
    api.request<Message[]>(`/messages/${collaborationId}`)
      .then(({ data }) => setMessages(data))
      .catch((e) => console.error('Error fetching messages:', e));
  }, [collaborationId]);

  // Connect WebSocket for real-time live events
  useEffect(() => {
    const wsUrl = `ws://localhost:8080/ws/collaboration/${collaborationId}`;
    let socket: WebSocket | null = null;
    try {
      socket = new WebSocket(wsUrl);
      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.event === 'new_message' && parsed.data) {
            setMessages((prev) => [...prev, parsed.data]);
          }
        } catch (_) {}
      };
    } catch (e) {
      console.warn('WebSocket connection error:', e);
    }

    return () => {
      if (socket) socket.close();
    };
  }, [collaborationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isSending) return;

    const text = inputText.trim();
    setInputText('');
    setIsSending(true);

    try {
      const { data } = await api.request<Message>('/messages', {
        method: 'POST',
        body: {
          collaboration_id: collaborationId,
          recipient_id: recipientId,
          content: text
        }
      });
      // Optimistic append if not duplicated by WS
      setMessages((prev) => (prev.some(m => m.id === data.id) ? prev : [...prev, data]));
    } catch (e) {
      console.error('Error sending message:', e);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl flex flex-col h-[400px] shadow-xl overflow-hidden">
      {/* Chat Header */}
      <div className="p-3.5 bg-slate-950 border-b border-slate-800 flex items-center gap-2 text-white">
        <MessageSquare className="w-4 h-4 text-brand-400" />
        <h4 className="text-xs font-bold uppercase tracking-wider">Chat Contextual de Campaña</h4>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-3">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-slate-500">
            Inicia la conversación para coordinar los entregables.
          </div>
        ) : (
          messages.map((m) => {
            const isMe = m.sender_id === currentUserId;
            return (
              <div
                key={m.id}
                className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-xs ${
                    isMe
                      ? 'bg-brand-600 text-white rounded-br-none'
                      : 'bg-slate-800 text-slate-200 rounded-bl-none'
                  }`}
                >
                  <p>{m.content}</p>
                </div>
                <span className="text-[10px] text-slate-500 mt-1 px-1">
                  {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input Form */}
      <form onSubmit={handleSend} className="p-3 bg-slate-950 border-t border-slate-800 flex items-center gap-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Escribe un mensaje de coordinación..."
          className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500 min-h-touch"
        />
        <button
          type="submit"
          disabled={!inputText.trim() || isSending}
          className="bg-brand-600 hover:bg-brand-500 disabled:opacity-40 text-white p-2.5 rounded-xl min-w-touch min-h-touch flex items-center justify-center transition-colors"
          aria-label="Enviar mensaje"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
