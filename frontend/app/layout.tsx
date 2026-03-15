"use client";

// import { Geist, Geist_Mono } from "next/font/google";
import { Amplify } from 'aws-amplify';
import { amplifyConfig } from '../amplifyConfig';
import { signInWithRedirect } from '@aws-amplify/auth';
import { fetchUserAttributes } from 'aws-amplify/auth';
import LockOutlineIcon from '@mui/icons-material/LockOutline';
import { usePathname, useRouter } from 'next/navigation';

import "./globals.css";
import React from "react";
import Head from "next/head";
import Link from "next/link";

// Initialize Amplify once
Amplify.configure({ Auth: amplifyConfig.Auth });

type UserMode = 'null' | 'user' | 'admin_user';
const MODE_HIERARCHY: UserMode[] = ['null', 'user', 'admin_user'];

function getUserMode(user: any | null): UserMode {
  if (!user) return 'null';
  if (user['custom:is_admin'] === 'true') return 'admin_user';
  return 'user';
}

function canAccess(required: UserMode, current: UserMode): boolean {
  return MODE_HIERARCHY.indexOf(current) >= MODE_HIERARCHY.indexOf(required);
}

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
  const tabs: Array<{ name: string; url: string; visibility?: UserMode; options?: Array<{ name: string; url: string; description: string; icon: React.ReactNode }> }> = [
    { name: "Home", url: "/" },
    { name: "Blogs", url: "/blogs" },
    // { name: "Certifications", url: "/certifications" },
    { name: "Contact", url: "/contact" },
    { name: "Chat", url: "/talk", visibility: 'user' },
    { name: "Trading", url: "/trading", visibility: 'admin_user' },
  ];

  const router = useRouter();
  const pathname = usePathname();
  const currentMode = getUserMode(user);
  const restrictedTab = tabs.find(t => t.visibility && pathname?.startsWith(t.url));
  const isRestrictedPage = !!restrictedTab;
  const canAccessPage = !restrictedTab || canAccess(restrictedTab.visibility!, currentMode);

  React.useEffect(() => {
    if (!loadingUser && isRestrictedPage && !canAccessPage) {
      router.replace('/');
    }
  }, [loadingUser, isRestrictedPage, canAccessPage, router]);

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
            <div className="flex md:flex-1 items-center">
              <Link href="/" className="-m-1.5 p-1.5">
                <span className="sr-only">Shivom Thakkar</span>
              </Link>
              {/* Mobile greeting */}
              <div className="flex md:hidden items-center">
                {loadingUser ? (
                  <div className="animate-pulse h-4 w-24 rounded bg-gray-700" />
                ) : user ? (
                  <span className="text-lg font-normal text-white">
                    Hi <span className="font-bold">{user?.given_name}</span>!
                  </span>
                ) : (
                  <span className="text-lg font-normal text-white">Hello There!</span>
                )}
              </div>
            </div>
            <div className="flex md:hidden">
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
            <div className="hidden md:flex items-center space-x-8">
              {tabs.map((tab, idx) => {
                // Admin+ tabs: hide entirely when loading or inaccessible
                if (tab.visibility && tab.visibility !== MODE_HIERARCHY[1] && (loadingUser || !canAccess(tab.visibility, currentMode))) {
                  return null;
                }
                return (
                <div key={tab.name} className="relative">
                  {tab.visibility === MODE_HIERARCHY[1] && loadingUser ? (
                    <div className="animate-pulse h-4 w-10 rounded bg-gray-700" />
                  ) : tab.options ? (
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
                                  <Link href={opt.url ? `/${opt.url}` : "/"} className="block font-semibold text-white">{opt.name}</Link>
                                  <p className="mt-1 text-gray-400">{opt.description}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    tab.visibility ? (
                      canAccess(tab.visibility, currentMode) ? (
                        <Link
                          href={tab.url}
                          className="flex items-center gap-x-1 text-sm font-semibold text-white cursor-pointer transition-transform duration-150 hover:scale-105"
                        >
                          {tab.name}
                        </Link>
                      ) : (
                        <span
                          className="flex items-center gap-x-1 text-sm font-semibold text-white opacity-50 cursor-not-allowed pointer-events-none"
                          aria-disabled={true}
                          tabIndex={-1}
                        >
                          {tab.name}
                          <LockOutlineIcon aria-label="Login required" className="ml-1 text-gray-400" style={{ fontSize: '0.75rem' }} />
                        </span>
                      )
                    ) : (
                      <Link href={tab.url ? `${tab.url}` : "/"} className="flex items-center gap-x-1 text-sm font-semibold text-white cursor-pointer transition-transform duration-150 hover:scale-105">{tab.name}</Link>
                    )
                  )}
                </div>
                );
              })}
            </div>
            <div className="hidden md:flex md:flex-1 md:justify-end">
              {loadingUser ? (
                <div className="animate-pulse h-4 w-28 rounded bg-gray-700" />
              ) : user ? (
                <span className="text-sm font-semibold text-white">
                  {(user?.["custom:is_admin"] == "true") && <span className="mr-1 text-xs text-gray-400">(Admin)</span>}
                  {user?.given_name} {user?.family_name}
                </span>
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
                    {tabs.map((tab) => {
                      // Admin+ tabs: hide entirely when loading or inaccessible
                      if (tab.visibility && tab.visibility !== MODE_HIERARCHY[1] && (loadingUser || !canAccess(tab.visibility, currentMode))) {
                        return null;
                      }
                      const accessible = !tab.visibility || canAccess(tab.visibility, currentMode);
                      return loadingUser ? (
                        <div key={tab.name} className="animate-pulse h-8 w-3/4 rounded-lg bg-gray-700 mx-3" />
                      ) : accessible ? (
                        <Link
                          key={tab.name}
                          href={tab.url ? `${tab.url}` : "/"}
                          className="block rounded-lg px-3 py-2 text-lg font-semibold text-white hover:bg-white/5"
                          onClick={() => setMobileMenuOpen(false)}
                        >
                          {tab.name}
                        </Link>
                      ) : (
                        <span
                          key={tab.name}
                          className="flex items-center gap-x-1 rounded-lg px-3 py-2 text-lg font-semibold text-white opacity-50 cursor-not-allowed"
                        >
                          {tab.name}
                          <LockOutlineIcon aria-label="Login required" className="ml-1 text-gray-400" style={{ fontSize: '0.75rem' }} />
                        </span>
                      );
                    })}
                  </div>
                  <div className="py-6">
                    {loadingUser ? (
                      <div className="animate-pulse h-10 w-full rounded-lg bg-gray-700" />
                    ) : user ? (
                      <span className="block w-full rounded-lg px-3 py-2.5 text-lg font-semibold text-white">{user?.signInDetails?.loginId || user?.username || user?.attributes?.name || user?.attributes?.email}</span>
                    ) : (
                      <button
                        onClick={handleLogin}
                        className="block w-full rounded-lg px-3 py-2.5 text-lg font-semibold text-white bg-blue-600 hover:bg-blue-700 transition-colors cursor-pointer"
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
        {isRestrictedPage && loadingUser ? (
          <main className="mx-auto bg-[#0b1726] flex items-center justify-center p-8 min-h-[calc(100vh-88px)]">
            <div className="w-[1200px] animate-pulse space-y-4 p-10">
              <div className="h-8 bg-[#1e2e42] rounded w-1/4" />
              <div className="h-4 bg-[#1e2e42] rounded w-1/3" />
              <div className="pt-4 space-y-3">
                <div className="h-4 bg-[#1e2e42] rounded w-full" />
                <div className="h-4 bg-[#1e2e42] rounded w-5/6" />
                <div className="h-4 bg-[#1e2e42] rounded w-4/6" />
              </div>
            </div>
          </main>
        ) : isRestrictedPage && !canAccessPage ? null : (
          children
        )}
      </body>
    </html>
  );
}
