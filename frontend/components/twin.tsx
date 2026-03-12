'use client';

import { useState, useEffect, useRef } from 'react';
import { Send } from 'lucide-react';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
}

export default function Twin() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string>('');
    const [loadingDots, setLoadingDots] = useState('');
    const loadingMsgId = 'loading-bubble';
    const messagesEndRef = useRef<HTMLDivElement>(null);
    // Scroll to bottom when messages change
    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    // Animate loading dots
    useEffect(() => {
        if (!isLoading) {
            setLoadingDots('');
            return;
        }
        let i = 0;
        const interval = setInterval(() => {
            setLoadingDots('.'.repeat((i % 3) + 1));
            i++;
        }, 400);
        return () => clearInterval(interval);
    }, [isLoading]);

    const sendMessage = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input,
        };

        setMessages(prev => [...prev, userMessage, {
            id: loadingMsgId,
            role: 'assistant',
            content: '', // Will show animated dots
        }]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: input,
                    session_id: sessionId || undefined,
                }),
            });

            if (!response.ok) throw new Error('Failed to send message');
            const data = await response.json();
            if (!sessionId) setSessionId(data.session_id);
            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: data.response,
            };
            setMessages(prev => [
                ...prev.filter(m => m.id !== loadingMsgId),
                assistantMessage
            ]);
        } catch (error) {
            setMessages(prev => [
                ...prev.filter(m => m.id !== loadingMsgId),
                {
                    id: (Date.now() + 1).toString(),
                    role: 'assistant',
                    content: 'Sorry, I encountered an error. Please try again.',
                }
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div className="w-full">
            {/* Conversation Section */}
            <div className="p-0">
                <div className="w-full h-[380px] rounded-xl border border-[#3a4a5f] overflow-y-auto flex flex-col gap-4 p-6">
                    {/* Messages */}
                    {messages.length === 0 ? (
                        <div className="text-[#b0b8c1] text-center my-auto">No messages yet. Start the conversation below.</div>
                    ) : (
                        <>
                            {messages.map((msg) => (
                                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`relative max-w-[70%] px-4 py-2 rounded-lg ${msg.role === 'user' ? 'bg-[#243244] text-white' : 'bg-[#162335] text-[#b0b8c1]'}
                                        ${msg.id === loadingMsgId ? 'animate-pulse' : ''}
                                    `}>
                                        {/* Message content or loading dots */}
                                        {msg.id === loadingMsgId ? (
                                            <span className="inline-block min-w-[24px]">{loadingDots || '.'}</span>
                                        ) : (
                                            msg.content
                                        )}
                                    </div>
                                </div>
                            ))}
                            <div ref={messagesEndRef} />
                        </>
                    )}
                </div>
            </div>
            {/* Divider */}
            <div className="border-t border-[#243244]"></div>
            {/* Footer Section (Input) */}
            <div className="p-0">
                <form
                    className="w-full h-[70px] rounded-lg border border-[#3a4a5f] flex items-center px-4 gap-4"
                    onSubmit={e => { e.preventDefault(); sendMessage(); }}
                >
                    <input
                        type="text"
                        className="flex-1 bg-transparent text-white placeholder-[#b0b8c1] outline-none border-none"
                        placeholder="Type your message..."
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={handleKeyPress}
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        className="bg-[#243244] text-white px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50"
                        disabled={isLoading || !input.trim()}
                    >
                        <Send size={20} />
                        Send
                    </button>
                </form>
            </div>
        </div>
    );
}