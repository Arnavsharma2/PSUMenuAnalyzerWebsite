#!/bin/bash

# Build script for Vercel deployment
echo "Building PSU Menu Analyzer for Vercel..."

# Create public directory
mkdir -p public

# Copy static files
cp index.html public/
cp sw.js public/ 2>/dev/null || echo "sw.js not found, skipping..."

echo "Build complete! Static files copied to public directory."
