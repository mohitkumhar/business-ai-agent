import { inputClasses, CHALLENGES, FINANCE_TRACKING_METHODS } from "../constants";
import { UploadPanel } from "./UploadPanel";
import type { FormData } from "../types";

type Props = {
  formData: Pick<FormData, "challenges" | "finance_tracking_method" | "onboarding_notes">;
  onChange: (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => void;
  onChallengeChange: (challenge: string) => void;
};

export function StepThreeSituation({ formData, onChange, onChallengeChange }: Props) {
  const showDigitalUpload =
    formData.finance_tracking_method === "Excel/Sheets" ||
    formData.finance_tracking_method === "App like Tally/Zoho";
  const showNotebookUpload = formData.finance_tracking_method === "Notebook/Manual";

  return (
    <div className="p-6 md:p-10 md:rounded-3xl rounded-2xl border border-white/10 bg-white/[0.02] shadow-xl flex flex-col gap-8">
      <h2 className="text-2xl font-medium text-white/90 border-b border-white/5 pb-4">
        Step 3 — Your Current Situation
      </h2>

      <div className="flex flex-col gap-5">
        <label className="text-sm font-medium text-white/80">
          Biggest Challenges <span className="text-red-400">*</span>
        </label>
        <div className="flex flex-wrap gap-3">
          {CHALLENGES.map((challenge) => (
            <label
              key={challenge}
              className={`cursor-pointer border rounded-full px-5 py-2.5 text-sm transition-all relative ${
                formData.challenges.includes(challenge)
                  ? "bg-white border-white text-black font-medium"
                  : "border-white/20 bg-white/5 hover:bg-white/10 text-white"
              }`}
            >
              <input
                type="checkbox"
                checked={formData.challenges.includes(challenge)}
                onChange={() => onChallengeChange(challenge)}
                className="absolute opacity-0 w-0 h-0"
              />
              {challenge}
            </label>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-5">
        <label className="text-sm font-medium text-white/80">Finance Tracking Method</label>
        <div className="flex flex-wrap gap-3">
          {FINANCE_TRACKING_METHODS.map((method) => (
            <label
              key={method}
              className={`cursor-pointer border rounded-full px-5 py-2.5 text-sm transition-all relative ${
                formData.finance_tracking_method === method
                  ? "bg-white border-white text-black font-medium"
                  : "border-white/20 bg-white/5 hover:bg-white/10 text-white"
              }`}
            >
              <input
                type="radio"
                name="finance_tracking_method"
                value={method}
                checked={formData.finance_tracking_method === method}
                onChange={onChange}
                className="absolute opacity-0 w-0 h-0"
              />
              {method}
            </label>
          ))}
        </div>
        {showDigitalUpload && <UploadPanel method="digital" />}
        {showNotebookUpload && <UploadPanel method="notebook" />}
      </div>

      <div className="flex flex-col gap-3">
        <label className="text-sm font-medium text-white/80">
          Anything else AI should know (optional)
        </label>
        <textarea
          name="onboarding_notes"
          className={`${inputClasses} min-h-[120px] resize-y leading-relaxed`}
          placeholder="Tell us more about your specific needs or pain points..."
          value={formData.onboarding_notes}
          onChange={onChange}
        />
      </div>
    </div>
  );
}