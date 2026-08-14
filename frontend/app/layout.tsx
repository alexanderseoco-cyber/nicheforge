import "./globals.css";
import "./research/search-volume/search-volume.css";
import "./research/search-volume/search-volume-overrides.css";
import React from "react";
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
