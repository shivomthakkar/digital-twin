
import Twin from '@/components/twin';

export default function Talk() {
  return (
    <main className="mx-auto bg-[#0b1726] flex flex-col h-[calc(100dvh-88px)] p-2 lg:h-auto lg:items-center lg:justify-center lg:p-8">
      <div className="flex-1 flex flex-col lg:flex-none mx-auto bg-[#0b1726] lg:flex lg:items-center lg:justify-center w-full lg:p-8">
        <div className="flex-1 flex flex-col w-full lg:max-w-[1200px] lg:rounded-2xl border border-[#243244] bg-[#0f1c2e] lg:shadow-inner">
          {/* Chatbot Card */}
          <Twin />
        </div>
      </div>
    </main>
  );
}
