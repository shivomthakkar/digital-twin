'use client';

import { useState, useRef, useImperativeHandle, forwardRef, useEffect } from 'react';
import { ChevronDown, Send, X } from 'lucide-react';
import BubblingLoader from './BubblingLoader';

export interface ChatWindowRef {
  addMessage: (message: string) => void;
  addLoadingMessage: () => void;
}

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'system' | 'loading';
  timestamp: number;
}

export interface ChatMessage {
  text: string;
  sender: 'user' | 'system';
}

interface ChatWindowProps {
  onSendMessage: (history: ChatMessage[]) => Promise<void>;
  title?: string;
}

const ChatWindow = forwardRef<ChatWindowRef, ChatWindowProps>(({ onSendMessage, title = 'Chat' }, ref) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useImperativeHandle(ref, () => ({
    addMessage: (text: string) => {
      setMessages((prev) => [
        ...prev.filter((msg) => msg.sender !== 'loading'),
        {
          id: `${Date.now()}-${Math.random()}`,
          text,
          sender: 'system',
          timestamp: Date.now(),
        },
      ]);
    },
    addLoadingMessage: () => {
      setMessages((prev) => [
        ...prev,
        {
          id: `loading-${Date.now()}`,
          text: '',
          sender: 'loading',
          timestamp: Date.now(),
        },
      ]);
    },
  }));

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage = inputValue.trim();
    setInputValue('');

    // Add user message immediately
    setMessages((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        text: userMessage,
        sender: 'user',
        timestamp: Date.now(),
      },
    ]);

    // Kick off the request before showing the loader, passing full conversation history
    setIsSending(true);
    const history: ChatMessage[] = [
      ...messages
        .filter((m): m is Message & { sender: 'user' | 'system' } => m.sender !== 'loading')
        .map(({ text, sender }) => ({ text, sender })),
      { text: userMessage, sender: 'user' },
    ];
    const sendPromise = onSendMessage(history);

    // Add loading message after send is already in-flight
    setMessages((prev) => [
      ...prev,
      {
        id: `loading-${Date.now()}`,
        text: '',
        sender: 'loading',
        timestamp: Date.now(),
      },
    ]);

    try {
      await sendPromise;
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Single element owns both width and max-height so they transition in lockstep */}
      <div
        className={`overflow-hidden rounded-lg shadow-2xl transition-[width,max-height] duration-300 ease-in-out max-w-[calc(100vw-3rem)] ${
          isExpanded ? 'w-[30rem] max-h-[27rem]' : 'w-80 max-h-12'
        }`}
      >
        {/* Header — h-12 (3rem) when collapsed, same height in both states */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold flex items-center justify-between"
        >
          <span>{title}</span>
          <ChevronDown
            size={20}
            className={`transition-transform duration-300 ${isExpanded ? '' : 'rotate-180'}`}
          />
        </button>

        {/* Panel — h-96 (24rem); clipped by parent overflow-hidden during animation */}
        <div className="bg-gray-800 flex flex-col h-96">
          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-400 text-sm">No messages yet. Start a conversation!</p>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.sender === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    {message.sender === 'loading' ? (
                      <div className="bg-gray-700 rounded-lg px-3 py-2">
                        <BubblingLoader />
                      </div>
                    ) : (
                      <div
                        className={`px-3 py-2 rounded-lg max-w-xs break-words ${
                          message.sender === 'user'
                            ? 'bg-indigo-600 text-white'
                            : 'bg-gray-700 text-gray-100'
                        }`}
                      >
                        {message.text}
                      </div>
                    )}
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-700 bg-gray-800 p-3 flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type a message..."
              disabled={isSending}
              className="flex-1 bg-gray-700 text-white rounded px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-600 border border-gray-600 disabled:opacity-50"
            />
            <button
              onClick={handleSendMessage}
              disabled={isSending || !inputValue.trim()}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded px-3 py-2 flex items-center justify-center transition-colors"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});

ChatWindow.displayName = 'ChatWindow';

export default ChatWindow;
