import { Link, useLocation, useRouter } from "@tanstack/react-router";
import { Button, buttonVariants } from "@typebot.io/ui/components/Button";
import { Cancel01Icon } from "@typebot.io/ui/icons/Cancel01Icon";
import { Menu01Icon } from "@typebot.io/ui/icons/Menu01Icon";
import { cn } from "@typebot.io/ui/lib/cn";
import { cx } from "@typebot.io/ui/lib/cva";
import { AnimatePresence, motion } from "motion/react";
import React, { useEffect, useRef, useState } from "react";
import { TypebotLogoFull } from "@/components/TypebotLogo";
import {
  breakpoints,
  dashboardUrl,
  discordUrl,
  docsUrl,
  githubRepoUrl,
  registerUrl,
  signinUrl,
} from "@/constants";
import { useWindowSize } from "@/features/homepage/hooks/useWindowSize";
import { useIsAuthenticated } from "@/hooks/useIsAuthenticated";
import { ButtonLink, CtaButtonLink, TextLink } from "./link";

const links = [
  {
    label: "Documentation",
    href: docsUrl,
  },
  {
    label: "GitHub",
    href: githubRepoUrl,
  },
  {
    label: "Community",
    href: discordUrl,
  },
  {
    label: "About",
    to: "/",
  },
] as const;

type HeaderProps = {
  isOpened?: boolean;
  onOpen: () => void;
  onClose: () => void;
};

export const Header = ({ isOpened = false, onOpen, onClose }: HeaderProps) => {
  const headerRef = useRef<HTMLDivElement>(null);
  const [appearance, setAppearance] = useState<"light" | "dark">("dark");
  const { width: windowWidth, height: windowHeight } = useWindowSize();
  const router = useRouter();
  const isAuthenticated = useIsAuthenticated();

  useEffect(() => {
    if (!windowWidth || !windowHeight) return;
    const isMobile = windowWidth < breakpoints.md;
    const options = {
      rootMargin: `0px 0px ${isMobile ? -(windowHeight - 50) : -70}px 0px`,
      threshold: 0,
    };

    const initializeObserver = () => {
      const observer = new IntersectionObserver(([entry]) => {
        entry.target.classList.contains("dark")
          ? setAppearance(entry.isIntersecting ? "dark" : "light")
          : setAppearance(entry.isIntersecting ? "light" : "dark");
      }, options);

      const elementsToObserve = [
        ...document.getElementsByTagName("section"),
        ...document.getElementsByTagName("footer"),
      ];

      elementsToObserve.forEach((element) => {
        observer.observe(element);
      });

      return observer;
    };

    let observer = initializeObserver();

    const routerSubscription = router.subscribe("onResolved", () => {
      observer.disconnect();
      observer = initializeObserver();
    });

    return () => {
      observer.disconnect();
      routerSubscription();
    };
  }, [windowWidth, windowHeight, setAppearance, router]);

  const toggleHeaderExpansion = () => {
    if (isOpened) {
      onClose();
    } else {
      onOpen();
    }
  };

  return (
    <header className="flex justify-center">
      <Mobile
        ref={headerRef}
        appearance={appearance}
        isOpened={isOpened}
        toggleHeaderExpansion={toggleHeaderExpansion}
        className="md:hidden"
        aria-label="Mobile header navigation"
        isAuthenticated={isAuthenticated}
      />
      <Desktop
        ref={headerRef}
        appearance={appearance}
        className="hidden md:flex"
        aria-label="Mobile header navigation"
        isAuthenticated={isAuthenticated}
      />
    </header>
  );
};

type Props = {
  appearance: "light" | "dark";
  isOpened: boolean;
  toggleHeaderExpansion: () => void;
  className: string;
  isAuthenticated: boolean;
};

const Mobile = React.forwardRef<HTMLElement, Props>(function Mobile(
  { appearance, isOpened, toggleHeaderExpansion, className, isAuthenticated },
  ref,
) {
  return (
    <motion.nav
      ref={ref}
      className={cn(
        "flex flex-col gap-8 justify-start backdrop-blur-md rounded-lg border-2 w-[calc(100%-2rem)] will-change-transform duration-300 transition-colors overflow-hidden",
        appearance === "light"
          ? "bg-white/50"
          : isOpened
            ? "dark bg-black/90 text-foreground"
            : "dark bg-black/60 text-foreground",
        className,
      )}
      transition={{ duration: 0.4, type: "spring", bounce: 0.15 }}
      animate={{ height: isOpened ? "calc(100dvh - 2rem)" : "auto" }}
    >
      <div className="flex items-center justify-between px-4 py-2 shrink-0">
        <Link to="/">
          <TypebotLogoFull />
        </Link>
        <Button
          aria-label={isOpened ? "Close menu" : "Open menu"}
          onClick={toggleHeaderExpansion}
          className="transition-none bg-transparent hover:bg-white/5"
        >
          {isOpened ? <Cancel01Icon /> : <Menu01Icon />}
        </Button>
      </div>
      <AnimatePresence mode="popLayout">
        {isOpened && (
          <motion.nav
            className="flex flex-col justify-between flex-1 min-h-0 gap-6 px-4 pb-4 overflow-y-auto"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="flex flex-col gap-6">
              {links.map((link) => (
                <TextLink
                  key={link.label}
                  className="no-underline text-xl font-normal"
                  href={"href" in link ? link.href : undefined}
                  target={"href" in link ? "_blank" : undefined}
                  to={"to" in link ? link.to : undefined}
                >
                  {link.label}
                </TextLink>
              ))}
            </div>
            <div className="flex flex-col gap-3 pb-2">
              {isAuthenticated ? (
                <>
                  <CtaButtonLink
                    href={dashboardUrl}
                    className="w-full py-5 rounded-2xl bg-[#FF5A25] text-white font-bold text-center"
                  >
                    Go to Dashboard
                  </CtaButtonLink>
                  <button
                    onClick={() => {
                      localStorage.removeItem('profit_pilot_user');
                      window.location.href = "/";
                    }}
                    className="w-full py-4 text-white/50 font-bold hover:text-white transition-colors"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <CtaButtonLink
                  href={signinUrl}
                  className="w-full py-5 rounded-2xl border border-white/20 text-white font-bold text-center"
                >
                  Sign in
                </CtaButtonLink>
              )}
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </motion.nav>
  );
});

const desktopLinks = [
  {
    label: "Community",
    href: discordUrl,
  },
  {
    label: "Documentation",
    href: docsUrl,
  },
  {
    label: "GitHub",
    href: githubRepoUrl,
  },
] as const;

const Desktop = React.forwardRef<
  HTMLElement,
  Pick<Props, "appearance" | "className" | "isAuthenticated">
>(function Desktop({ appearance, className, isAuthenticated }, ref) {
  const { pathname } = useLocation();
  const [isScrolled, setIsScrolled] = useState(false);

  const [isIntersecting, setIsIntersecting] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY < 50) setIsIntersecting(false);
      setIsScrolled(window.scrollY > 50);

    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    const separator = document.getElementById("magic-animation-separator");
    if (!separator) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.boundingClientRect.bottom < 0) return;
        setIsIntersecting(entry.isIntersecting);
      },
      { threshold: 0.1 },
    );

    observer.observe(separator);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      className={cx(
        "flex gap-2 items-center transition-opacity",
        pathname === "/" && isScrolled && !isIntersecting
          ? "opacity-0 pointer-events-none"
          : "opacity-100",
        className,
      )}
    >
      <nav
        ref={ref}
        className={cx(
          "flex rounded-2xl border px-2 py-2 bg-linear-to-b transition-colors gap-2 items-center",
          appearance === "dark"
            ? "dark from-[#393939] to-[#121212]"
            : "from-white to-[#DEDEDE]",
        )}
      >
        {desktopLinks.map((link) => (
          <ButtonLink
            key={link.label}
            variant="ghost"
            size="sm"
            className="font-normal"
            href={"href" in link ? link.href : undefined}
            to={"to" in link ? link.to : undefined}
            activeProps={{
              className: "font-medium",
            }}
          >
            {link.label}
          </ButtonLink>
        ))}
        {pathname !== "/get-started" && pathname !== "/login" && (
          isAuthenticated ? (
            <div className="flex items-center gap-2">
              <CtaButtonLink size="sm" href={dashboardUrl}>
                Go to dashboard
              </CtaButtonLink>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  localStorage.removeItem('profit_pilot_user');
                  window.location.href = "/";
                }}
                className="text-white/60 hover:text-white"
              >
                Logout
              </Button>
            </div>
          ) : (
            <CtaButtonLink size="sm" href={registerUrl}>
              Get started free
            </CtaButtonLink>
          )
        )}
      </nav>

    </div>
  );
});
