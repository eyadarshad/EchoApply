import type { Metadata } from "next";
import "./globals.css";
import Providers from "./Providers";

export const metadata: Metadata = {
  metadataBase: new URL("https://echoapply.ai"),
  title: {
    default: "Echo Apply",
    template: "%s | Echo Apply",
  },
  description: "Free 25-criteria ATS CV audit, LinkedIn profile SEO optimizer, AI resume tailoring, tailored cover letter generator, and mock interview practice.",
  keywords: [
    "Echo Apply",
    "CV audit",
    "resume audit",
    "LinkedIn audit",
    "ATS resume checker",
    "AI resume tailor",
    "cover letter generator",
    "mock interview prep",
    "recruiter SEO",
    "job search automation",
  ],
  authors: [{ name: "Echo Apply" }],
  openGraph: {
    title: "Echo Apply",
    description: "Free 25-criteria ATS CV audit, LinkedIn profile SEO optimizer, AI resume tailoring, and interview practice.",
    url: "https://echoapply.ai",
    siteName: "Echo Apply",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Echo Apply",
    description: "Free 25-criteria ATS CV audit, LinkedIn profile SEO optimizer, and AI resume tailoring.",
  },
  icons: {
    icon: "/logo.png",
    shortcut: "/logo.png",
    apple: "/logo.png",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
