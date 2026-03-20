export default function BubblingLoader() {
  return (
    <div className="flex items-center gap-1 py-2">
      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
    </div>
  );
}
