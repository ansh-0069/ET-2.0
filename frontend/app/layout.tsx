import type { Metadata } from "next";
import "./styles.css";
import "./premium.css";

export const metadata: Metadata = {
  title: "PetraVigil | Supply Intelligence",
  description: "Evidence-first energy supply resilience workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="app-shell">{children}</body>
    </html>
  );
}
