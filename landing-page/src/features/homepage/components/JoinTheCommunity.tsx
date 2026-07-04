import { cx } from "@typebot.io/ui/lib/cva";
import { CtaButtonLink } from "@/components/link";
import { discordUrl } from "../../../constants";
import abhaySrc from "../testimonials/assets/anish.jpeg";
import barrettaSrc from "../testimonials/assets/barretta.jpeg";
import joshuaSrc from "../testimonials/assets/joshua.jpg";
import kurniaSrc from "../testimonials/assets/kurnia.jpeg";
import laszloSrc from "../testimonials/assets/laszlo.jpeg";
import lucasSrc from "../testimonials/assets/lucas.png";
import nicolaiSrc from "../testimonials/assets/nicolai.jpg";

const stats = [
  {
    stat: "15k+",
    label: "Monthly Insights Generated",
  },
  {
    stat: "400+",
    label: "Businesses Connected",
  },
  {
    stat: "30+",
    label: "Active Founders",
  },
];

const avatars = [
  {
    id: "avatar-1",
    src: abhaySrc,
    alt: "Community member 1 profile photo",
    position: "top-1 left-36",
  },
  {
    id: "avatar-2",
    src: laszloSrc,
    alt: "Community member 2 profile photo",
    position: "top-32 left-4 delay-500",
  },
  {
    id: "avatar-3",
    src: joshuaSrc,
    alt: "Community member 3 profile photo",
    position: "bottom-8 left-24 delay-300",
  },
  {
    id: "avatar-4",
    src: lucasSrc,
    alt: "Community member 4 profile photo",
    position: "-bottom-7 -left-7 delay-700",
  },
  {
    id: "avatar-5",
    src: kurniaSrc,
    alt: "Community member 5 profile photo",
    position: "top-1 right-36 delay-1000",
  },
  {
    id: "avatar-6",
    src: nicolaiSrc,
    alt: "Community member 6 profile photo",
    position: "top-28 right-4 delay-500",
  },
  {
    id: "avatar-7",
    src: barrettaSrc,
    alt: "Community member 7 profile photo",
    position: "bottom-12 right-32 delay-300",
  },
];

export const JoinTheCommunity = () => (
  <div className="flex flex-col rounded-2xl w-full max-w-7xl bg-card border">
    <div className="relative isolate flex dark rounded-2xl md:rounded-b-none p-6 pt-12 md:pb-12 justify-center overflow-hidden">
      <FloatingAvatars className="hidden md:block" />
      <div className="flex flex-col gap-12 md:items-center max-w-4xl">
        <div className="flex flex-col gap-6 text-balance md:text-center">
          <h2 className="text-gray-12">
            You don&apos;t have to grow your
            <br className="hidden md:block" />
            business alone.
          </h2>
          <p className="text-gray-11">
            Focus on peer support. Connect with like-minded entrepreneurs,
            share financial strategies, and get help when you're stuck.
          </p>
        </div>
        <CtaButtonLink size="lg" href={discordUrl} target="_blank">
          Join the community
        </CtaButtonLink>
      </div>
    </div>

    <div className="flex flex-col md:flex-row justify-evenly gap-6 p-6 md:p-8">
      {stats.map(({ stat, label }) => (
        <div key={label} className="flex flex-col items-center gap-2">
          <span className="text-4xl font-display font-medium">{stat}</span>
          <span className="text-gray-11">{label}</span>
        </div>
      ))}
    </div>
  </div>
);

const FloatingAvatars = ({ className }: { className?: string }) => (
  <div className={className}>
    {avatars.map(({ id, src, alt, position }) => (
      <img
        key={id}
        src={src}
        alt={alt}
        className={cx(
          "rounded-full w-16 h-16 border-4 absolute animate-float",
          position,
        )}
      />
    ))}
  </div>
);