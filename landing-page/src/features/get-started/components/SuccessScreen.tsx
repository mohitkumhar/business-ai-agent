import { Button } from "@typebot.io/ui/components/Button";
import { dashboardUrl } from "@/constants";

type Props = {
  email: string;
};

export function SuccessScreen({ email }: Props) {
  return (
    <main className="dark w-full min-h-screen bg-[#0a0a0a] text-white flex flex-col pt-32 pb-24 px-4 m-0 overflow-x-hidden">
      <div className="max-w-2xl w-full mx-auto flex flex-col items-center gap-6 py-32 text-center animate-in fade-in duration-500">
        <h1 className="text-4xl md:text-5xl font-bold">
          Form Submitted Successfully!
        </h1>
        <p className="text-lg text-white/70">
          Welcome to ProfitPilot! We've received your business details and are setting up your workspace.
        </p>
        <Button
          onClick={() =>
            (window.location.href = `${dashboardUrl}?user_email=${encodeURIComponent(email)}`)
          }
          variant="outline"
          style={{ color: "black", backgroundColor: "white", borderColor: "white" }}
          className="mt-6 rounded-full font-medium"
        >
          Go to Dashboard
        </Button>
      </div>
    </main>
  );
}