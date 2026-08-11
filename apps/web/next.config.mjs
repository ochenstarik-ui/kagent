/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  eslint: { ignoreDuringBuilds: true },
  async rewrites() {
    return [
      {
        source: '/api/control-plane/:path*',
        destination: `${process.env.GATEWAY_URL || 'http://localhost:8080'}/api/control-plane/:path*`,
      },
      {
        source: '/api/observability/:path*',
        destination: `${process.env.GATEWAY_URL || 'http://localhost:8080'}/api/observability/:path*`,
      },
    ]
  },
}
export default nextConfig;
