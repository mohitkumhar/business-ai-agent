import { motion } from "motion/react";

type Props = {
  method: "digital" | "notebook";
};

export function UploadPanel({ method }: Props) {
  if (method === "digital") {
    return (
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-4 p-6 rounded-2xl bg-white/5 border border-white/10 flex flex-col gap-4 animate-in fade-in"
      >
        <p className="text-sm text-white/70 italic">
          Almost ready! Would you like to upload your initial data now for instant analysis?
        </p>
        <div className="flex gap-4">
          <div className="flex-1 border-2 border-dashed border-white/10 rounded-xl p-8 hover:border-[#FF5A25]/50 transition-colors flex flex-col items-center justify-center gap-3 cursor-pointer group">
            <svg
              className="w-8 h-8 text-white/30 group-hover:text-[#FF5A25] transition-colors"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
              />
            </svg>
            <span className="text-sm font-medium">Upload File (.xlsx, .csv)</span>
            <input type="file" className="hidden" accept=".xlsx,.csv" />
          </div>
          <button
            type="button"
            className="px-6 py-2 text-sm font-medium text-white/40 hover:text-white transition-colors"
          >
            Skip for now
          </button>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4 p-6 rounded-2xl bg-white/5 border border-white/10 flex flex-col gap-4 animate-in fade-in"
    >
      <p className="text-sm text-white/70 italic">
        No problem! Take a photo of your latest ledger entries and our AI will extract the data for you.
      </p>
      <div className="border-2 border-dashed border-white/10 rounded-xl p-8 hover:border-[#FF5A25]/50 transition-colors flex flex-col items-center justify-center gap-3 cursor-pointer group">
        <svg
          className="w-8 h-8 text-white/30 group-hover:text-[#FF5A25] transition-colors"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
        <span className="text-sm font-medium">Upload Image of Notebook</span>
        <input type="file" className="hidden" accept="image/*" capture="environment" />
      </div>
    </motion.div>
  );
}