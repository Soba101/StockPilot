/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep it simple: just localhost and the primary LAN IP you asked for.
  allowedDevOrigins: ['localhost', '192.168.18.70'],
  async rewrites() {
    // Try to determine if we should use localhost or LAN IP for backend
    // In development, support both localhost and LAN access
    const backendHost = process.env.BACKEND_HOST || 'localhost';
    
    return [
      {
        source: '/api/:path*',
        destination: `http://${backendHost}:8000/api/v1/:path*`
      }
    ];
  }
};

module.exports = nextConfig;