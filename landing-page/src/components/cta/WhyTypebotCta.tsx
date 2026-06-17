import { registerUrl } from "@/constants";
import { CtaButtonLink } from "../link";
import imgSrc from "./assets/3d-group.png";

export const WhyTypebotCta = () => (
  <div className="why-cta overflow-hidden relative isolate dark flex justify-between items-center p-4 rounded-3xl w-full">
    <div className="flex flex-col gap-6 flex-1 p-4 md:py-0 md:pl-16 md:pr-20 items-start">
      <h2>Why ProfitPilot?</h2>
      <p>
        ProfitPilot is built to empower business owners with AI-driven insights
        and risk analysis. We wanted to make business intelligence intuitive,
        proactive, and fair source. ProfitPilot is a project that truly
        empowers the user and never vendor-locks you in.
      </p>
      <CtaButtonLink size="lg" href={registerUrl}>
        Start for free
      </CtaButtonLink>
    </div>
    <img
      src={imgSrc}
      alt=""
      className="rounded-3xl max-w-md hidden md:block"
    />
  </div>
);
