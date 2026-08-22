import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, Source_Sans_3 } from "next/font/google";
import "./globals.css";
import BioField from "@/components/BioField";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";
import { ThemeProvider } from "@/lib/theme";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

const sans = Source_Sans_3({
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  variable: "--font-sans",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "AMPscan - Binary antimicrobial peptide classifier",
  description:
    "Homology-aware AMP vs non-AMP scores for peptides of length 5-100. Calibrated Random Forest.",
};

const themeBoot = `
try {
  var t = localStorage.getItem('ampscan-theme');
  if (t === 'light') document.documentElement.classList.remove('dark');
  else document.documentElement.classList.add('dark');
  document.documentElement.classList.remove('reduce-motion');
} catch (e) {}
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${display.variable} ${sans.variable} ${mono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBoot }} />
      </head>
      <body className="flex min-h-screen flex-col antialiased">
        <ThemeProvider>
          <BioField />
          <Nav />
          <main className="relative mx-auto w-full max-w-7xl flex-1 px-4 py-10">{children}</main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
