import { inputClasses } from "../constants";
import type { FormData } from "../types";

type Props = {
  formData: Pick<FormData, "full_name" | "email">;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
};

export function StepOneDetails({ formData, onChange }: Props) {
  return (
    <div className="p-6 md:p-10 md:rounded-3xl rounded-2xl border border-white/10 bg-white/[0.02] shadow-xl flex flex-col gap-6">
      <h2 className="text-2xl font-medium text-white/90 border-b border-white/5 pb-4">
        Step 1 — Your Details
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="flex flex-col gap-3">
          <label className="text-sm font-medium text-white/80">
            Your Full Name <span className="text-red-400">*</span>
          </label>
          <input
            required
            type="text"
            name="full_name"
            className={inputClasses}
            placeholder="Jane Doe"
            value={formData.full_name}
            onChange={onChange}
          />
        </div>
        <div className="flex flex-col gap-3">
          <label className="text-sm font-medium text-white/80">
            Work Email <span className="text-red-400">*</span>
          </label>
          <input
            required
            type="email"
            name="email"
            className={inputClasses}
            placeholder="name@company.com"
            value={formData.email}
            onChange={onChange}
          />
        </div>
      </div>
    </div>
  );
}