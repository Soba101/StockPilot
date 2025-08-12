/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep it simple: just localhost and the primary LAN IP you asked for.
  allowedDevOrigins: ['localhost', '192.168.18.70'],
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/v1/:path*'
      }
    ];
  }
};

module.exports = nextConfig;