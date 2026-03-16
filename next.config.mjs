/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Allow images from Firebase Storage if needed
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
