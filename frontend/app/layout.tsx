import type { Metadata } from "next";
import { Geist } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Document Intelligence Agent",
  description: "GitHub ドキュメント解析エージェント",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja" className={geist.className}>
      <body className="bg-gray-50 min-h-screen">
        <nav className="border-b border-gray-200 bg-white px-6 py-3">
          <div className="mx-auto max-w-5xl flex items-center justify-between">
            <Link href="/" className="text-sm font-semibold text-indigo-700">
              📄 Doc Intelligence
            </Link>
            <div className="flex gap-6 text-sm text-gray-600">
              <Link href="/" className="hover:text-indigo-600">Discovery</Link>
              <Link href="/catalog" className="hover:text-indigo-600">Catalog</Link>
            </div>
          </div>
        </nav>
        <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
