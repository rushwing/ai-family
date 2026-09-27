import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "知微 · Home Intelligence",
  description: "知微家庭智能设备控制与状态中心。",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
