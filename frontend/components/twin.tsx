'use client';

import { useState, useEffect, useRef } from 'react';
import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { authFetch } from '../lib/api';
import BubblingLoader from './BubblingLoader';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    options?: string[];
}

export default function Twin() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string>('');
    const loadingMsgId = 'loading-bubble';
    const messagesEndRef = useRef<HTMLDivElement>(null);
    // Scroll to bottom when messages change
    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    const sendMessage = async (messageText?: string) => {
        const text = (messageText ?? input).trim();
        if (!text || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: text,
        };

        setMessages(prev => [...prev, userMessage, {
            id: loadingMsgId,
            role: 'assistant',
            content: '', // Will show animated dots
        }]);
        if (!messageText) setInput('');
        setIsLoading(true);

        try {
            const response = await authFetch(`${process.env.NEXT_PUBLIC_TWIN_API_URL || 'http://localhost:8000'}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: text,
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
                options: data.options ?? undefined,
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
        <div className="w-full flex-1 flex flex-col">
            {/* Conversation Section */}
            <div className="p-0 flex-1 flex flex-col">
                <div className="w-full flex-1 lg:flex-none lg:h-[540px] rounded-xl border border-[#3a4a5f] overflow-y-auto flex flex-col gap-4 p-3 lg:p-6">
                    {/* Messages */}
                    {messages.length === 0 ? (
                        <div className="text-[#b0b8c1] text-center my-auto">No messages yet. Start the conversation below.</div>
                    ) : (
                        <>
                            {messages.map((msg) => (
                                msg.role === 'user' ? (
                                    <div key={msg.id} className="flex justify-end">
                                        <div className="relative max-w-[85%] sm:max-w-[70%] px-4 py-2 rounded-lg bg-[#243244] text-white">
                                            {msg.content}
                                        </div>
                                    </div>
                                ) : (
                                    <div key={msg.id} className="w-full px-1 text-[#b0b8c1]">
                                        {msg.id === loadingMsgId ? (
                                            <BubblingLoader />
                                        ) : (
                                            <>
                                            <div className="prose prose-invert prose-base max-w-none">
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                    {msg.content}
                                                </ReactMarkdown>
                                            </div>
                                            {msg.options && msg.options.length > 0 && (
                                                <div className="mt-3 flex flex-wrap gap-2">
                                                    {msg.options.map((option, i) => (
                                                        <button
                                                            key={i}
                                                            onClick={() => sendMessage(option)}
                                                            disabled={isLoading}
                                                            className="text-sm px-3 py-1.5 rounded-full border border-[#3a4a5f] text-[#8899aa] hover:text-white hover:border-[#4a6a8f] hover:bg-[#243244] transition-colors disabled:opacity-50 text-left"
                                                        >
                                                            {option}
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                            </>
                                        )}
                                    </div>
                                )
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
                    className="w-full h-[70px] rounded-lg border border-[#3a4a5f] flex items-center px-2 sm:px-4 gap-2 sm:gap-4"
                    onSubmit={e => { e.preventDefault(); sendMessage(); }}
                >
                    <input
                        type="text"
                        className="flex-1 min-w-0 bg-transparent text-white placeholder-[#b0b8c1] outline-none border-none"
                        placeholder="Type your message..."
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={handleKeyPress}
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        className="shrink-0 bg-[#243244] text-white px-2 sm:px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50"
                        disabled={isLoading || !input.trim()}
                    >
                        <Send size={20} />
                        <span className="hidden sm:inline">Send</span>
                    </button>
                </form>
            </div>
        </div>
    );
}