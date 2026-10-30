import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Static HTML export, served at "/" next to the Flask app (see ../vercel.json).
  output: "export",
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
