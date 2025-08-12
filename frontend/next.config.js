/** @type {import('next').NextConfig} */
const os = require('os');

// Next.js expects hostnames (optionally with wildcards), not full protocol URLs, for allowedDevOrigins.
function discoverLanHosts() {
  const nets = os.networkInterfaces();
  const hosts = new Set([
    'localhost',
    '127.0.0.1'
  ]);
  for (const name of Object.keys(nets)) {
    for (const net of nets[name] || []) {
      if (!net.internal && net.family === 'IPv4') {
        if (net.address.startsWith('192.168.') || net.address.startsWith('10.') || net.address.startsWith('172.')) {
          hosts.add(net.address);
        }
      }
    }
  }
  // Allow manual additional hosts (comma separated) via env
  if (process.env.ALLOWED_DEV_ORIGINS) {
    process.env.ALLOWED_DEV_ORIGINS.split(',').map(s => s.trim()).filter(Boolean).forEach(h => hosts.add(h));
  }
  return Array.from(hosts);
}

const nextConfig = {
  // Explicitly allow dev overlay / HMR from LAN IPs to silence future Next.js warnings
  // Include dynamically discovered hosts plus explicit LAN IPs / wildcard subnet.
  allowedDevOrigins: Array.from(new Set([
    ...discoverLanHosts(),
    '192.168.18.70',
    '192.168.18.107', // already auto-discovered but kept explicit
    '192.168.18.130', // client device you requested
    '192.168.18.*'    // wildcard for rest of subnet (Next.js supports simple wildcards)
  ])),
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/v1/:path*'
      }
    ]
  }
}

// Debug log (dev only). Remove if noisy.
if (process.env.NODE_ENV !== 'production') {
  // eslint-disable-next-line no-console
  console.log('[next.config] allowedDevOrigins =', nextConfig.allowedDevOrigins);
}

module.exports = nextConfig