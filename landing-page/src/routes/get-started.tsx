import { createFileRoute } from "@tanstack/react-router";
import { Button } from "@typebot.io/ui/components/Button";
import { createMetaTags } from "@/lib/createMetaTags";
import { useGetStartedForm } from "@/features/get-started/useGetStartedForm";
import { LoadingScreen } from "@/features/get-started/components/LoadingScreen";
import { SuccessScreen } from "@/features/get-started/components/SuccessScreen";
import { StepOneDetails } from "@/features/get-started/components/StepOneDetails";
import { StepTwoBusinessDetails } from "@/features/get-started/components/StepTwoBusinessDetails";
import { StepThreeSituation } from "@/features/get-started/components/StepThreeSituation";

export const Route = createFileRoute("/get-started")({
  head: () => ({
    meta: createMetaTags({
      title: "Get Started | ProfitPilot",
      description: "Get started with ProfitPilot by telling us about your business.",
      imagePath: "/images/default-og.png",
      path: "/get-started",
    }),
  }),
  component: GetStartedPage,
});

function GetStartedPage() {
  const {
    sessionReady,
    isSubmitted,
    isSubmitting,
    error,
    formData,
    handleChange,
    handleChallengeChange,
    handleSubmit,
  } = useGetStartedForm();

  if (!sessionReady) return <LoadingScreen />;
  if (isSubmitted) return <SuccessScreen email={formData.email} />;

  return (
    <main className="dark w-full min-h-screen bg-[#0a0a0a] text-white flex flex-col pt-24 md:pt-32 pb-32 px-4 m-0 overflow-x-hidden">
      <div className="max-w-3xl w-full mx-auto pb-24 mt-8 md:mt-16 animate-in slide-in-from-bottom-8 fade-in duration-700">
        <div className="mb-12 text-center flex flex-col gap-4 mx-auto w-full max-w-2xl">
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight">Business Profile</h1>
          <p className="text-lg text-white/60 mx-auto">
            Tell us about your company so we can tailor your dynamic AI dashboard.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-8 md:gap-12">
          <StepOneDetails formData={formData} onChange={handleChange} />
          <StepTwoBusinessDetails formData={formData} onChange={handleChange} />
          <StepThreeSituation
            formData={formData}
            onChange={handleChange}
            onChallengeChange={handleChallengeChange}
          />

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-500 px-6 py-4 rounded-2xl text-sm">
              {error}
            </div>
          )}

          <div className="flex justify-end pt-4">
            <Button
              disabled={isSubmitting}
              type="submit"
              size="lg"
              className="group relative overflow-hidden w-full md:w-auto px-12 py-8 text-xl font-bold rounded-full transition-all disabled:opacity-50 disabled:active:scale-100 shadow-[inset_0_3px_2px_0_rgba(255,255,255,0.25),0_10px_40px_rgba(255,90,37,0.2)] bg-linear-to-b border border-[#C4461D] from-[#FF8963] to-[#FF5A25] text-white active:shadow-[inset_0_-2px_2px_0_rgba(255,255,255,0.17)] flex items-center justify-center gap-3"
            >
              <div className="bg-transparent group-hover:bg-white/40 w-1/4 absolute -left-[40%] group-hover:left-[120%] transition-[left] duration-0 group-hover:duration-700 blur-md -rotate-45 aspect-square pointer-events-none" />
              {isSubmitting ? (
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin" />
                  Connecting...
                </div>
              ) : (
                "Launch My Dashboard"
              )}
            </Button>
          </div>
        </form>
      </div>
    </main>
  );
}
