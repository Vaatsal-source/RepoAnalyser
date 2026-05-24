/** @type {import('next').NextConfig} */
const nextConfig = {
  reactCompiler: true,
  // Move turbo to the root object layer out of experimental
  turbo: {
    root: '../../..' 
  }
};

export default nextConfig;