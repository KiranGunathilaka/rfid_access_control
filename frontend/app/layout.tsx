import type React from "react"
import type { Metadata } from "next"
import "./globals.css"
import { Inter } from "next/font/google"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "SPOTSEEKER ACCESS PRO",
  description: "Admin Portal - User Management System",
  icons: {
    icon: "/images/logo.webp",
    apple: "/images/logo.webp",
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="no-scrollbar">
      <body suppressHydrationWarning className={`${inter.className} no-scrollbar`}>
        {children}
      </body>
    </html>
  )
}
