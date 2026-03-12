export default function Contact() {
  return (
    <main>
      <div className="relative isolate bg-gray-900 px-6 py-24 sm:py-32 lg:px-8">
        <div aria-hidden="true" className="absolute inset-x-0 -z-10 transform-gpu overflow-hidden blur-3xl">
          <div style={{clipPath: 'polygon(74.1% 44.1%, 100% 61.6%, 97.5% 26.9%, 85.5% 0.1%, 80.7% 2%, 72.5% 32.5%, 60.2% 62.4%, 52.4% 68.1%, 47.5% 58.3%, 45.2% 34.5%, 27.5% 76.7%, 0.1% 64.9%, 17.9% 100%, 27.6% 76.8%, 76.1% 97.7%, 74.1% 44.1%)'}} className="relative left-1/2 -z-10 aspect-[1155/678] w-[144.5rem] max-w-none -translate-x-1/2 rotate-[30deg] bg-gradient-to-tr from-[#ff80b5] to-[#9089fc] opacity-20 sm:left-[calc(50%-40rem)] sm:w-[288.75rem]" />
        </div>
        <div className="mx-auto max-w-2xl text-center">
          <h1 className="text-4xl font-semibold tracking-tight text-balance text-white sm:text-5xl mb-4">Contact Me</h1>
          <p className="mt-2 text-lg/8 text-gray-300">Have a conversation with me by heading over to my bot in the <a href="/talk" className="text-blue-500 underline">Talk</a> tab now!</p>
          <p className="mt-2 text-lg/8 text-gray-300">Or you can reach me the traditional way at shivomthakkar15@gmail.com or via the contact form (coming soon).</p>
        </div>
      </div>
    </main>
  );
}
