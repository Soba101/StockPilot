/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep it simple: just localhost and the primary LAN IP you asked for.
  allowedDevOrigins: ['localhost', '192.168.18.70'],
  async rewrites() {
    // Always use localhost for backend since it's running locally
    // The Next.js rewrite will proxy requests regardless of how frontend is accessed
    const backendHost = 'localhost';
    
    console.log(`🔧 Next.js rewrite configured: /api/* -> http://${backendHost}:8000/api/v1/*`);
    
    return [
      {
        source: '/api/:path*',
        destination: `http://${backendHost}:8000/api/v1/:path*`
      }
    ];
  }
};

module.exports = nextConfig;