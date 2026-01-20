#!/bin/bash

# =============================================================================
# Multi-platform Docker Build and Push to Azure Container Registry
# =============================================================================
# This script builds Docker images for multiple platforms (Mac, Windows, Linux)
# and pushes them to Azure Container Registry using Docker Buildx
# =============================================================================

set -e  # Exit on error

# Configuration - Update these variables
ACR_NAME="${ACR_NAME:-trovesuitedevacr1}"  # Azure Container Registry name
IMAGE_NAME="${IMAGE_NAME:-mystoreguard}"  # Image name (e.g., core-platform, loandrift, mystoreguard)
IMAGE_TAG="${IMAGE_TAG:-latest}"           # Image tag
DOCKERFILE_PATH="${DOCKERFILE_PATH:-./app/Dockerfile}"  # Path to Dockerfile
BUILD_CONTEXT="${BUILD_CONTEXT:-.}"    # Build context directory (root to match Azure Pipelines)

# Platforms: linux/amd64 (Intel/Windows), linux/arm64 (Apple Silicon)
PLATFORMS="linux/amd64,linux/arm64"

# Full image reference
FULL_IMAGE_NAME="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"

echo "=========================================="
echo "Docker Multi-Platform Build & Push"
echo "=========================================="
echo "ACR Name:      ${ACR_NAME}"
echo "Image Name:    ${IMAGE_NAME}"
echo "Image Tag:     ${IMAGE_TAG}"
echo "Full Image:    ${FULL_IMAGE_NAME}"
echo "Platforms:     ${PLATFORMS}"
echo "Dockerfile:    ${DOCKERFILE_PATH}"
echo "Context:       ${BUILD_CONTEXT}"
echo "=========================================="
echo ""

# Step 1: Login to Azure Container Registry
echo "🔐 Logging into Azure Container Registry..."
az acr login --name "${ACR_NAME}"

if [ $? -ne 0 ]; then
    echo "❌ Failed to login to ACR. Please ensure:"
    echo "   1. You are logged into Azure CLI (az login)"
    echo "   2. You have permissions to access the ACR"
    echo "   3. The ACR name is correct: ${ACR_NAME}"
    exit 1
fi

echo "✅ Successfully logged into ACR"
echo ""

# Step 2: Create and use buildx builder (if it doesn't exist)
echo "🔧 Setting up Docker Buildx..."
BUILDER_NAME="multiarch-builder"

# Check if builder exists
if ! docker buildx inspect "${BUILDER_NAME}" >/dev/null 2>&1; then
    echo "   Creating new buildx builder: ${BUILDER_NAME}"
    docker buildx create --name "${BUILDER_NAME}" --driver docker-container --use
    docker buildx inspect --bootstrap
else
    echo "   Using existing buildx builder: ${BUILDER_NAME}"
    docker buildx use "${BUILDER_NAME}"
    docker buildx inspect --bootstrap
fi

echo "✅ Buildx builder ready"
echo ""

# Step 3: Build and push multi-platform image
echo "🏗️  Building multi-platform image..."
echo "   This may take several minutes..."
echo ""

docker buildx build \
    --platform "${PLATFORMS}" \
    --file "${DOCKERFILE_PATH}" \
    --tag "${FULL_IMAGE_NAME}" \
    --push \
    --progress=plain \
    "${BUILD_CONTEXT}"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully built and pushed multi-platform image!"
    echo ""
    echo "📦 Image Details:"
    echo "   Registry: ${ACR_NAME}.azurecr.io"
    echo "   Image:    ${IMAGE_NAME}:${IMAGE_TAG}"
    echo "   Platforms: ${PLATFORMS}"
    echo ""
    echo "🚀 You can now pull this image on:"
    echo "   - Mac (Intel): docker pull ${FULL_IMAGE_NAME}"
    echo "   - Mac (M1/M2): docker pull ${FULL_IMAGE_NAME}"
    echo "   - Windows:     docker pull ${FULL_IMAGE_NAME}"
    echo "   - Linux:       docker pull ${FULL_IMAGE_NAME}"
else
    echo ""
    echo "❌ Build failed. Please check the error messages above."
    exit 1
fi

