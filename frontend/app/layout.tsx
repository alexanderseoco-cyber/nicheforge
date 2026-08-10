import React from "react";
export default function RootLayout({children}:{children:React.ReactNode}) {
  return <html lang="en"><body style={{fontFamily:"system-ui",margin:0,background:"#f5f7fb",color:"#14213d"}}>{children}</body></html>;
}
