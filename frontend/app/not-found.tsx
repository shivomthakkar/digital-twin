"use client"
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function NotFound() {
  const router = useRouter();
  return (
    <div className="min-h-screen w-full bg-[#050b18] flex flex-col md:flex-row items-stretch">
      {/* LEFT SIDE FULL SCREEN */}
      <div className="flex-1 flex flex-col justify-between p-10 md:p-20 bg-[#0b1627]">
        <div>
          {/* 404 */}
          <p className="text-indigo-400 text-lg font-medium mb-6">404</p>
          {/* Heading */}
          <h1 className="text-6xl font-semibold text-white mb-6 leading-tight">
            Page not found
          </h1>
          {/* Description */}
          <p className="text-gray-400 text-lg mb-10">
            Sorry, we couldn’t find the page you’re looking for.
          </p>
          {/* Back Link */}
          <button
            type="button"
            onClick={() => router.back()}
            className="text-indigo-400 hover:text-indigo-300 transition flex items-center gap-2"
          >
            <span className="text-xl">←</span>
            Go back
          </button>
        </div>
        {/* <div className="pt-8 border-t border-[#1f2a3a] text-gray-500 text-sm flex gap-6">
          <Link href="/contact" className="hover:text-gray-300 transition">Contact support</Link>
          <span>•</span>
          <a href="#" className="hover:text-gray-300 transition">Status</a>
        </div> */}
      </div>
      {/* RIGHT SIDE IMAGE FULL SCREEN */}
      <div className="flex-1 relative hidden md:block">
        <img 
          src="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?q=80&w=2000&auto=format&fit=crop"
          alt="Desert night"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-l from-transparent via-transparent to-[#0b1627]/60"></div>
      </div>
    </div>
  );
}
