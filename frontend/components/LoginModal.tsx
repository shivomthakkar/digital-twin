'use client';

import { useState, useEffect, useRef } from 'react';
import { generateToken } from '../lib/trading';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function LoginModal({ isOpen, onClose, onSuccess }: Props) {
  const [clientId, setClientId] = useState('');
  const [pin, setPin] = useState('');
  const [totp, setTotp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await generateToken(clientId, pin, totp);
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
    >
      <div className="w-full max-w-sm rounded-xl border border-[#3a4a5f] bg-[#1a2535] p-8 shadow-2xl">
        <h2 className="mb-6 text-xl font-semibold text-white">Broker Login</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label className="text-sm text-[#b0b8c1]">Client ID</label>
            <input
              type="text"
              required
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              className="rounded-lg border border-[#3a4a5f] bg-[#243244] px-3 py-2 text-white placeholder-[#b0b8c1] outline-none focus:border-indigo-400"
              placeholder="Enter client ID"
              disabled={loading}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-sm text-[#b0b8c1]">PIN</label>
            <input
              type="password"
              required
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              className="rounded-lg border border-[#3a4a5f] bg-[#243244] px-3 py-2 text-white placeholder-[#b0b8c1] outline-none focus:border-indigo-400"
              placeholder="Enter PIN"
              disabled={loading}
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-sm text-[#b0b8c1]">TOTP</label>
            <input
              type="text"
              required
              inputMode="numeric"
              value={totp}
              onChange={(e) => setTotp(e.target.value)}
              className="rounded-lg border border-[#3a4a5f] bg-[#243244] px-3 py-2 text-white placeholder-[#b0b8c1] outline-none focus:border-indigo-400"
              placeholder="6-digit code"
              disabled={loading}
            />
          </div>

          {error && (
            <p className="rounded border border-red-500 bg-red-500/10 px-3 py-2 text-sm text-red-400">
              {error}
            </p>
          )}

          <div className="mt-2 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="flex-1 rounded-lg border border-[#3a4a5f] py-2 text-[#b0b8c1] hover:bg-[#243244] disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-lg bg-indigo-600 py-2 font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {loading ? 'Connecting…' : 'Login'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
