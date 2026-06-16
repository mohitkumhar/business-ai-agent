export function LoadingScreen() {
  return (
    <main className="dark w-full min-h-screen bg-[#0a0a0a] text-white flex items-center justify-center m-0">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-2 border-white/20 border-t-white rounded-full animate-spin" />
        <p className="text-white/50 text-sm">Loading…</p>
      </div>
    </main>
  );
}