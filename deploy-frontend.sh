#!/bin/bash

# MintFlow Frontend Deployment Script
# Builds and deploys web application and mobile apps

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-development}
PLATFORM=${2:-all} # web, ios, android, or all
BUILD_NUMBER=${3:-$(date +%Y%m%d%H%M)}

echo -e "${GREEN}🚀 Starting MintFlow Frontend Deployment${NC}"
echo -e "${BLUE}Environment: $ENVIRONMENT${NC}"
echo -e "${BLUE}Platform: $PLATFORM${NC}"
echo -e "${BLUE}Build Number: $BUILD_NUMBER${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    echo -e "${YELLOW}➤ $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Check prerequisites
print_status "Checking prerequisites..."

if [ "$PLATFORM" = "web" ] || [ "$PLATFORM" = "all" ]; then
    if ! command_exists node; then
        print_error "Node.js is not installed"
    fi
    
    if ! command_exists npm; then
        print_error "npm is not installed"
    fi
fi

if [ "$PLATFORM" = "ios" ] || [ "$PLATFORM" = "all" ]; then
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_error "iOS build requires macOS"
    fi
    
    if ! command_exists xcodebuild; then
        print_error "Xcode is not installed"
    fi
    
    if ! command_exists pod; then
        print_error "CocoaPods is not installed"
    fi
fi

if [ "$PLATFORM" = "android" ] || [ "$PLATFORM" = "all" ]; then
    if ! command_exists gradle; then
        print_error "Gradle is not installed"
    fi
    
    if [ -z "$ANDROID_HOME" ]; then
        print_error "ANDROID_HOME environment variable is not set"
    fi
fi

print_success "Prerequisites check passed"

# Set environment variables based on deployment environment
print_status "Setting up environment configuration..."

case $ENVIRONMENT in
    "development")
        API_URL="http://localhost:8000"
        WEB_URL="http://localhost:3000"
        SENTRY_ENV="development"
        ;;
    "staging")
        API_URL="https://api-staging.mintflow.com"
        WEB_URL="https://staging.mintflow.com"
        SENTRY_ENV="staging"
        ;;
    "production")
        API_URL="https://api.mintflow.com"
        WEB_URL="https://app.mintflow.com"
        SENTRY_ENV="production"
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        ;;
esac

# Deploy Web Application
if [ "$PLATFORM" = "web" ] || [ "$PLATFORM" = "all" ]; then
    print_status "Building web application..."
    
    cd frontend/web
    
    # Install dependencies
    print_status "Installing dependencies..."
    npm ci
    
    # Create environment file
    cat > .env.production << EOF
REACT_APP_API_URL=$API_URL
REACT_APP_ENVIRONMENT=$ENVIRONMENT
REACT_APP_VERSION=1.0.0
REACT_APP_BUILD_NUMBER=$BUILD_NUMBER
REACT_APP_SENTRY_DSN=$SENTRY_DSN
REACT_APP_SENTRY_ENVIRONMENT=$SENTRY_ENV
REACT_APP_PLAID_ENV=$ENVIRONMENT
EOF

    # Build application
    print_status "Building React application..."
    npm run build
    
    # Build Docker image
    if command_exists docker; then
        print_status "Building Docker image..."
        docker build -t mintflow/web:$BUILD_NUMBER .
        docker tag mintflow/web:$BUILD_NUMBER mintflow/web:latest
        
        if [ "$ENVIRONMENT" = "production" ]; then
            # Push to registry
            print_status "Pushing to Docker registry..."
            docker push mintflow/web:$BUILD_NUMBER
            docker push mintflow/web:latest
        fi
    fi
    
    print_success "Web application built successfully"
    cd ../..
fi

# Deploy Mobile Application
if [ "$PLATFORM" = "ios" ] || [ "$PLATFORM" = "android" ] || [ "$PLATFORM" = "all" ]; then
    print_status "Setting up mobile application..."
    
    cd mobile
    
    # Install dependencies
    print_status "Installing React Native dependencies..."
    npm ci
    
    # Create environment file
    cat > .env << EOF
API_URL=$API_URL
ENVIRONMENT=$ENVIRONMENT
VERSION=1.0.0
BUILD_NUMBER=$BUILD_NUMBER
SENTRY_DSN=$SENTRY_DSN
PLAID_ENV=$ENVIRONMENT
EOF

    # Install iOS dependencies
    if [ "$PLATFORM" = "ios" ] || [ "$PLATFORM" = "all" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            print_status "Installing iOS dependencies..."
            cd ios && pod install && cd ..
        fi
    fi
fi

# Build iOS App
if [ "$PLATFORM" = "ios" ] || [ "$PLATFORM" = "all" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_status "Building iOS application..."
        
        cd mobile
        
        # Update version and build number
        /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString 1.0.0" ios/MintFlowMobile/Info.plist
        /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $BUILD_NUMBER" ios/MintFlowMobile/Info.plist
        
        # Build for different environments
        case $ENVIRONMENT in
            "development")
                print_status "Building iOS development version..."
                npx react-native run-ios --configuration Debug
                ;;
            "staging")
                print_status "Building iOS staging version..."
                cd ios
                xcodebuild -workspace MintFlowMobile.xcworkspace \
                          -scheme MintFlowMobile \
                          -configuration Release \
                          -destination generic/platform=iOS \
                          -archivePath MintFlowMobile.xcarchive \
                          archive
                cd ..
                ;;
            "production")
                print_status "Building iOS production version..."
                cd ios
                xcodebuild -workspace MintFlowMobile.xcworkspace \
                          -scheme MintFlowMobile \
                          -configuration Release \
                          -destination generic/platform=iOS \
                          -archivePath MintFlowMobile.xcarchive \
                          archive
                
                # Export IPA
                xcodebuild -exportArchive \
                          -archivePath MintFlowMobile.xcarchive \
                          -exportPath ./build \
                          -exportOptionsPlist ExportOptions.plist
                cd ..
                ;;
        esac
        
        print_success "iOS application built successfully"
        cd ..
    else
        print_status "Skipping iOS build (requires macOS)"
    fi
fi

# Build Android App
if [ "$PLATFORM" = "android" ] || [ "$PLATFORM" = "all" ]; then
    print_status "Building Android application..."
    
    cd mobile
    
    # Update version and build number
    sed -i.bak "s/versionCode .*/versionCode $BUILD_NUMBER/" android/app/build.gradle
    sed -i.bak "s/versionName .*/versionName \"1.0.0\"/" android/app/build.gradle
    
    case $ENVIRONMENT in
        "development")
            print_status "Building Android development version..."
            npx react-native run-android --variant=debug
            ;;
        "staging"|"production")
            print_status "Building Android release version..."
            cd android
            ./gradlew assembleRelease
            
            # Sign APK if keystore is available
            if [ -f "app/mintflow-release-key.keystore" ]; then
                print_status "Signing APK..."
                jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 \
                         -keystore app/mintflow-release-key.keystore \
                         app/build/outputs/apk/release/app-release-unsigned.apk \
                         mintflow-release-key
                
                # Align APK
                zipalign -v 4 app/build/outputs/apk/release/app-release-unsigned.apk \
                            app/build/outputs/apk/release/mintflow-$BUILD_NUMBER.apk
            fi
            cd ..
            ;;
    esac
    
    print_success "Android application built successfully"
    cd ..
fi

# Deploy to servers/stores
if [ "$ENVIRONMENT" = "production" ]; then
    print_status "Deploying to production..."
    
    # Deploy web app
    if [ "$PLATFORM" = "web" ] || [ "$PLATFORM" = "all" ]; then
        if command_exists kubectl; then
            print_status "Deploying web app to Kubernetes..."
            # Update image in deployment
            kubectl set image deployment/frontend frontend=mintflow/web:$BUILD_NUMBER -n mintflow
            kubectl rollout status deployment/frontend -n mintflow
        fi
    fi
    
    # Upload mobile apps
    if [ "$PLATFORM" = "ios" ] || [ "$PLATFORM" = "all" ]; then
        if [[ "$OSTYPE" == "darwin"* ]] && command_exists xcrun; then
            print_status "Uploading iOS app to App Store Connect..."
            # This would typically use altool or Transporter
            # xcrun altool --upload-app -f mobile/ios/build/MintFlowMobile.ipa -u $APPSTORE_USERNAME -p $APPSTORE_PASSWORD
            print_status "iOS app ready for App Store submission"
        fi
    fi
    
    if [ "$PLATFORM" = "android" ] || [ "$PLATFORM" = "all" ]; then
        print_status "Android app ready for Google Play submission"
        # This would typically use Google Play Console API
    fi
fi

# Generate deployment report
print_status "Generating deployment report..."

REPORT_FILE="deployment-report-$BUILD_NUMBER.json"
cat > $REPORT_FILE << EOF
{
  "deployment": {
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "environment": "$ENVIRONMENT",
    "platform": "$PLATFORM",
    "buildNumber": "$BUILD_NUMBER",
    "version": "1.0.0",
    "apiUrl": "$API_URL",
    "webUrl": "$WEB_URL"
  },
  "artifacts": {
    "web": {
      "dockerImage": "mintflow/web:$BUILD_NUMBER",
      "built": $([ "$PLATFORM" = "web" ] || [ "$PLATFORM" = "all" ] && echo "true" || echo "false")
    },
    "ios": {
      "archive": "mobile/ios/MintFlowMobile.xcarchive",
      "ipa": "mobile/ios/build/MintFlowMobile.ipa",
      "built": $([ "$PLATFORM" = "ios" ] || [ "$PLATFORM" = "all" ] && [[ "$OSTYPE" == "darwin"* ]] && echo "true" || echo "false")
    },
    "android": {
      "apk": "mobile/android/app/build/outputs/apk/release/mintflow-$BUILD_NUMBER.apk",
      "built": $([ "$PLATFORM" = "android" ] || [ "$PLATFORM" = "all" ] && echo "true" || echo "false")
    }
  }
}
EOF

print_success "Deployment report generated: $REPORT_FILE"

# Summary
echo ""
echo -e "${GREEN}🎉 Frontend deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Deployment Summary:${NC}"
echo -e "  Environment: $ENVIRONMENT"
echo -e "  Platform: $PLATFORM"
echo -e "  Build Number: $BUILD_NUMBER"
echo -e "  API URL: $API_URL"
if [ "$PLATFORM" = "web" ] || [ "$PLATFORM" = "all" ]; then
    echo -e "  Web URL: $WEB_URL"
fi
echo ""

if [ "$ENVIRONMENT" = "development" ]; then
    echo -e "${YELLOW}📱 Next Steps for Development:${NC}"
    echo -e "  • Web: Open $WEB_URL in your browser"
    echo -e "  • iOS: Open ios/MintFlowMobile.xcworkspace in Xcode"
    echo -e "  • Android: Run 'npx react-native run-android' in mobile directory"
elif [ "$ENVIRONMENT" = "production" ]; then
    echo -e "${YELLOW}🚀 Next Steps for Production:${NC}"
    echo -e "  • Web: Application deployed to Kubernetes cluster"
    echo -e "  • iOS: Submit IPA to App Store Connect"
    echo -e "  • Android: Upload APK to Google Play Console"
fi

echo ""
print_success "Frontend deployment script completed!"