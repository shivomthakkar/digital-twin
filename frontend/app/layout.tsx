"use client";

// import { Geist, Geist_Mono } from "next/font/google";
import { Amplify } from 'aws-amplify';
import { amplifyConfig } from '../amplifyConfig';
import { signInWithRedirect } from '@aws-amplify/auth';
import { getCurrentUser } from '@aws-amplify/auth';
import { fetchUserAttributes } from 'aws-amplify/auth';

import "./globals.css";
import React from "react";
import Head from "next/head";

// Initialize Amplify once
Amplify.configure({ Auth: amplifyConfig.Auth });

// const geistSans = Geist({
//   variable: "--font-geist-sans",
//   subsets: ["latin"],
// });

// const geistMono = Geist_Mono({
//   variable: "--font-geist-mono",
//   subsets: ["latin"],
// });

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [popoverIndex, setPopoverIndex] = React.useState<number | null>(null);
  const [user, setUser] = React.useState<any | null>(null);
  const [loadingUser, setLoadingUser] = React.useState(true);


  React.useEffect(() => {
    async function fetchUser() {
      try {
        const currentUser = await fetchUserAttributes();
        setUser(currentUser);
      } catch {
        setUser(null);
      } finally {
        setLoadingUser(false);
      }
    }
    fetchUser();
  }, []);

  // Navigation tabs config
  const tabs: Array<{ name: string; url: string; protected?: boolean; options?: Array<{ name: string; url: string; description: string; icon: React.ReactNode }> }> = [
    { name: "Home", url: "/" },
    { name: "Blogs", url: "/blogs" },
    { name: "Certifications", url: "/certifications" },
    { name: "Contact", url: "/contact" },
    { name: "Talk", url: "/talk", protected: true },
    // { name: "Trading", url: "/trading", protected: true },
  ];

  // Login handler
  const handleLogin = async () => {
    try {
      await signInWithRedirect({ provider: 'Google' });
    } catch (error) {
      let message = 'Login failed.';
      if (error && typeof error === 'object' && 'message' in error) {
        message = (error as { message?: string }).message || message;
      }
      alert(message);
    }
  };

  return (
      <html lang="en" className={`antialiased bg-slate-50 dark:bg-slate-900 dark:text-white`}>
        <Head>
          <link className="rounded-md" rel="icon" type="image/png" href="/favicon.ico" />
        </Head>
      <body className={`antialiased bg-gradient-to-br from-slate-50 to-gray-100 dark:from-slate-900 dark:to-gray-950 dark:text-white`}>
        <header className="bg-gray-900">
          <nav aria-label="Global" className="mx-auto flex max-w-7xl items-center justify-between p-6 lg:px-8">
            <div className="flex lg:flex-1">
              <a href="/" className="-m-1.5 p-1.5">
                <span className="sr-only">Shivom Thakkar</span>
              </a>
            </div>
            <div className="flex lg:hidden">
              <button
                type="button"
                aria-label="Open main menu"
                className="-m-2.5 inline-flex items-center justify-center rounded-md p-2.5 text-gray-400"
                onClick={() => setMobileMenuOpen(true)}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true" className="size-6">
                  <path d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
            <div className="hidden lg:flex items-center space-x-8">
              {tabs.map((tab, idx) => (
                <div key={tab.name} className="relative">
                  {tab.options ? (
                    <>
                      <button
                        className="flex items-center gap-x-1 text-sm font-semibold text-white cursor-pointer transition-transform duration-150 hover:scale-105"
                        aria-haspopup="true"
                        aria-expanded={popoverIndex === idx}
                        onMouseEnter={() => setPopoverIndex(idx)}
                        onFocus={() => setPopoverIndex(idx)}
                        onMouseLeave={() => setPopoverIndex(null)}
                        onBlur={() => setPopoverIndex(null)}
                      >
                        {tab.name}
                        <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className={`size-5 flex-none text-gray-500 transition-transform duration-200 ${popoverIndex === idx ? 'rotate-180' : ''}`}> 
                          <path d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" />
                        </svg>
                      </button>
                      {popoverIndex === idx && (
                        <div
                          className="absolute left-0 top-full z-10 mt-2 w-max min-w-[16rem] min-h-32 rounded-3xl bg-gray-800 shadow-lg outline outline-1 outline-white/10 transition duration-200"
                          onMouseEnter={() => setPopoverIndex(idx)}
                          onMouseLeave={() => setPopoverIndex(null)}
                        >
                          <div className="p-4">
                            {tab.options.map((opt) => (
                              <div key={opt.name} className="group relative flex items-center gap-x-6 rounded-lg p-4 text-sm hover:bg-white/5 cursor-pointer">
                                <div className="flex size-11 flex-none items-center justify-center rounded-lg bg-gray-700/50 group-hover:bg-gray-700">
                                  {opt.icon}
                                </div>
                                <div className="flex-auto">
                                  <a href={opt.url} className="block font-semibold text-white">{opt.name}</a>
                                  <p className="mt-1 text-gray-400">{opt.description}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    tab.protected ? (
                      <a
                        href={user ? tab.url : undefined}
                        className={`flex items-center gap-x-1 text-sm font-semibold text-white transition-transform duration-150 ${!user ? 'opacity-50 cursor-not-allowed pointer-events-none' : 'cursor-pointer hover:scale-105'}`}
                        aria-disabled={!user}
                        tabIndex={!user ? -1 : 0}
                      >
                        {tab.name}
                        {!user && (
                          <span className="ml-1 text-xs text-gray-400">(Login required)</span>
                        )}
                      </a>
                    ) : (
                      <a href={tab.url} className="flex items-center gap-x-1 text-sm font-semibold text-white cursor-pointer transition-transform duration-150 hover:scale-105">{tab.name}</a>
                    )
                  )}
                </div>
              ))}
            </div>
            <div className="hidden lg:flex lg:flex-1 lg:justify-end">
              {loadingUser ? (
                <span className="text-sm font-semibold text-white">Loading...</span>
              ) : user ? (
                <span className="text-sm font-semibold text-white">{user?.given_name} {user?.family_name}</span>
              ) : (
                <button
                  onClick={handleLogin}
                  className="text-sm font-semibold text-white cursor-pointer"
                >
                  Log In <span aria-hidden="true">&rarr;</span>
                </button>
              )}
            </div>
          </nav>
          {/* Mobile menu dialog */}
          {mobileMenuOpen && (
            <div className="fixed inset-0 z-50 bg-gray-900 bg-opacity-95 flex flex-col">
              <div className="flex items-center justify-between p-6">
                <button
                  type="button"
                  aria-label="Close menu"
                  className="-m-2.5 rounded-md p-2.5 text-gray-400"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true" className="size-6">
                    <path d="M6 18 18 6M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              </div>
              <div className="mt-6 flex-1 overflow-y-auto">
                <div className="divide-y divide-white/10">
                  <div className="space-y-2 py-6">
                    {tabs.map((tab) => (
                      <a
                        key={tab.name}
                        href={tab.url}
                        className="block rounded-lg px-3 py-2 text-base font-semibold text-white hover:bg-white/5"
                      >
                        {tab.name}
                      </a>
                    ))}
                  </div>
                  <div className="py-6">
                    {loadingUser ? (
                      <span className="block w-full rounded-lg px-3 py-2.5 text-base font-semibold text-white">Loading...</span>
                    ) : user ? (
                      <span className="block w-full rounded-lg px-3 py-2.5 text-base font-semibold text-white">{user?.signInDetails?.loginId || user?.username || user?.attributes?.name || user?.attributes?.email}</span>
                    ) : (
                      <button
                        onClick={handleLogin}
                        className="block w-full rounded-lg px-3 py-2.5 text-base font-semibold text-white bg-blue-600 hover:bg-blue-700 transition-colors cursor-pointer"
                      >
                        Log In
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </header>
        {children}
      </body>
    </html>
  );
}
