#!/bin/bash
echo "Installing npm dependencies..."
npm install

echo "Starting the React development server (fixed router nesting issue)..."
npm start

echo "Frontend running at http://localhost:3000"
