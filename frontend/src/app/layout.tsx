import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "../components/ThemeContext";
import ThreeBackground from "../components/ThreeBackground";

export const metadata: Metadata = {
  title: "AI Resume Generator & Smart Apply",
  description: "Generate tailored ATS-friendly resumes and apply automatically.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <ThemeProvider>
          <ThreeBackground />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
