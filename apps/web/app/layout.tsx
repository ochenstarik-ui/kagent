import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "KAgent — Автономная инженерная система",
  description: "Мультиагентная платформа для автономной разработки ПО",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
