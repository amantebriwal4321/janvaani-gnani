import type { Metadata } from "next";
import {
  Fraunces,
  Noto_Sans,
  Noto_Sans_Bengali,
  Noto_Sans_Devanagari,
  Noto_Sans_Kannada,
  Noto_Sans_Malayalam,
  Noto_Sans_Tamil,
  Noto_Sans_Telugu,
} from "next/font/google";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
});

const noto = Noto_Sans({
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  variable: "--font-noto",
});

const deva = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "600", "700"],
  variable: "--font-deva",
});

const kannada = Noto_Sans_Kannada({
  subsets: ["kannada"],
  weight: ["400", "600", "700"],
  variable: "--font-knda",
});

const telugu = Noto_Sans_Telugu({
  subsets: ["telugu"],
  weight: ["400", "600", "700"],
  variable: "--font-telu",
});

const tamil = Noto_Sans_Tamil({
  subsets: ["tamil"],
  weight: ["400", "600", "700"],
  variable: "--font-taml",
});

const bengali = Noto_Sans_Bengali({
  subsets: ["bengali"],
  weight: ["400", "600", "700"],
  variable: "--font-beng",
});

const malayalam = Noto_Sans_Malayalam({
  subsets: ["malayalam"],
  weight: ["400", "600", "700"],
  variable: "--font-mlym",
});

export const metadata: Metadata = {
  title: "JanVaani — speak, match, leave with a slip",
  description:
    "Speak in your language, get matched to welfare schemes, and leave with a ready-to-submit slip. Powered by Gnani.ai.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="hi"
      className={`${fraunces.variable} ${noto.variable} ${deva.variable} ${kannada.variable} ${telugu.variable} ${tamil.variable} ${bengali.variable} ${malayalam.variable}`}
    >
      <body className="antialiased">{children}</body>
    </html>
  );
}
