#!/bin/bash
# Package project for AWS Lambda deployment
# Output: lambda.zip

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="${SCRIPT_DIR}/.lambda_package"
ZIP_NAME="lambda.zip"

cd "$SCRIPT_DIR"

echo "Cleaning previous build..."
rm -rf "$PACKAGE_DIR"
rm -f "$ZIP_NAME"
mkdir -p "$PACKAGE_DIR"

echo "Installing dependencies..."
if command -v uv &> /dev/null; then
  uv pip install --target "$PACKAGE_DIR" fastapi mangum uvicorn
elif command -v pip &> /dev/null; then
  pip install --target "$PACKAGE_DIR" fastapi mangum uvicorn
else
  echo "Error: Neither uv nor pip found. Install one of them first."
  exit 1
fi

echo "Copying application files..."
cp main.py lambda_handler.py "$PACKAGE_DIR/"

echo "Creating zip archive..."
cd "$PACKAGE_DIR"
zip -r -q "../$ZIP_NAME" .
cd "$SCRIPT_DIR"

echo "Cleaning up..."
rm -rf "$PACKAGE_DIR"

echo "Done! Created $ZIP_NAME"
echo "Lambda handler: lambda_handler.handler"
