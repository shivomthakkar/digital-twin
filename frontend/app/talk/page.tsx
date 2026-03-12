
import Twin from '@/components/twin';

export default function Talk() {
  return (
    <main className="mx-auto bg-[#0b1726] flex items-center justify-center p-8">
      <div className="mx-auto bg-[#0b1726] flex items-center justify-center p-8">
        <div className="w-[1200px] rounded-2xl border border-[#243244] bg-[#0f1c2e] shadow-inner">
          {/* Header */}
          <div className="p-10">
            <h1 className="text-3xl font-bold text-white mb-2">Chatbot</h1>
            <p className="text-[#b0b8c1] text-base">Start a conversation below.</p>
          </div>
          {/* Divider */}
          <div className="border-t border-[#243244]"></div>
          {/* Chatbot Card */}
          <Twin />
        </div>
      </div>
    </main>
  );
}
