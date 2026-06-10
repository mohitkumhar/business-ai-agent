import {
  createRootRoute,
  HeadContent,
  Outlet,
  Scripts,
  useNavigate,
} from "@tanstack/react-router";
import { z } from "zod";
import css from "@/assets/globals.css?url";

import { Footer } from "@/components/footer/Footer";
import { Header } from "@/components/Header";
import { NotFound } from "@/components/NotFound";
import { FloatingChatbot } from "@/components/FloatingChatbot";


import { GoogleOAuthProvider } from "@react-oauth/google";

const HERO_ANIMATION_DELAY = 1800;

const GOOGLE_CLIENT_ID = typeof window !== 'undefined' ? (import.meta.env.VITE_GOOGLE_CLIENT_ID || "") : "";

export const Route = createRootRoute({
  head: () => ({
    links: [
      { rel: "stylesheet", href: css },
      {
        rel: "icon",
        type: "images/svg+xml",
        href: "/images/favicon.svg",
      },
      // Pre-connect for Google Auth performance
      { rel: "preconnect", href: "https://accounts.google.com" },
    ],
    meta: [
      {
        charSet: "utf-8",
      },
      {
        name: "viewport",
        content: "width=device-width, initial-scale=1",
      },
      {
        title: "ProfitPilot | Your AI Business Partner",
      },
    ],
  }),
  component: RootComponent,
  notFoundComponent: () => <NotFound />,
  validateSearch: z.object({
    isHeaderOpened: z.boolean().optional(),
  }),
});

import { ErrorBoundary } from "@/components/ErrorBoundary";

function RootComponent() {
  const { isHeaderOpened } = Route.useSearch();
  const navigate = useNavigate({ from: Route.fullPath });


  const openHeader = () => {
    navigate({
      search: { isHeaderOpened: true },
      resetScroll: false,
    });
  };
  const closeHeader = () => {
    navigate({
      search: { isHeaderOpened: undefined },
      resetScroll: false,
    });
  };

  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        <ErrorBoundary label="Landing Page">
          <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
            <div className="isolate flex flex-col items-stretch">
              <div className="fixed z-10 top-4 md:bottom-12 md:top-auto w-full">
                <Header
                  onOpen={openHeader}
                  onClose={closeHeader}
                  isOpened={isHeaderOpened}
                />
              </div>
              <Outlet />

              <Footer />
            </div>
            <FloatingChatbot />
            <Scripts />
          </GoogleOAuthProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
