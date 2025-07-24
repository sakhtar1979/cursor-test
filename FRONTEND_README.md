# MintFlow Frontend Applications

Complete frontend solution for the MintFlow Personal Finance System, featuring a responsive web application and native mobile apps for iOS and Android.

## 🚀 Overview

The MintFlow frontend consists of three main applications:

1. **Web Application** - React-based responsive web app
2. **iOS Mobile App** - React Native app for iPhone and iPad
3. **Android Mobile App** - React Native app for Android devices

All applications share common design principles, user experience patterns, and connect to the same backend APIs.

## 📱 Applications

### Web Application (`frontend/web/`)

**Modern React Application with:**
- ⚡ **React 18** with TypeScript
- 🎨 **Styled Components** & **Tailwind CSS**
- 📊 **Chart.js** & **Recharts** for data visualization
- 🔄 **React Query** for data fetching and caching
- 🗄️ **Redux Toolkit** for state management
- 🎭 **Framer Motion** for smooth animations
- 📱 **Responsive Design** for all screen sizes
- 🔒 **JWT Authentication** with auto-refresh
- 🎯 **Progressive Web App** capabilities

**Key Features:**
- Real-time financial dashboard
- Interactive charts and analytics
- Bank account management
- Transaction categorization
- Budget tracking and alerts
- Goal setting and progress tracking
- AI-powered financial insights
- Dark/light mode support

### Mobile Applications (`mobile/`)

**React Native Application with:**
- 📱 **React Native 0.72** with TypeScript
- 🧭 **React Navigation 6** for seamless navigation
- 🎨 **React Native Paper** for Material Design
- 📊 **React Native Chart Kit** for mobile-optimized charts
- 🔐 **Biometric Authentication** (Face ID, Touch ID, Fingerprint)
- 🔔 **Push Notifications** for alerts and reminders
- 📸 **Camera Integration** for receipt scanning
- 🗺️ **Location Services** for transaction categorization
- 💾 **Offline Support** with data synchronization
- 🔄 **Background Sync** for real-time updates

**Mobile-Specific Features:**
- Biometric login (Face ID, Touch ID, Fingerprint)
- Push notifications for budget alerts
- Receipt photo capture and OCR
- Quick balance check with widgets
- Location-based transaction insights
- Apple Pay / Google Pay integration ready
- App shortcuts for quick actions
- Deep linking support

## 🛠️ Technology Stack

### Web Application
```
Frontend Framework: React 18 + TypeScript
Styling: Styled Components + Tailwind CSS
State Management: Redux Toolkit + React Query
Charts: Chart.js + Recharts
Authentication: JWT with refresh tokens
Build Tool: Create React App + Custom Webpack
Testing: Jest + React Testing Library
Deployment: Docker + Nginx
```

### Mobile Applications
```
Framework: React Native 0.72 + TypeScript
Navigation: React Navigation 6
UI Library: React Native Paper
State Management: Redux Toolkit + React Query  
Charts: React Native Chart Kit
Authentication: JWT + Biometric
Security: React Native Keychain
Notifications: React Native Push Notification
Build: Gradle (Android) + Xcode (iOS)
```

## 🏗️ Architecture

### Component Architecture
```
src/
├── components/          # Reusable UI components
│   ├── UI/             # Basic UI elements (Button, Card, etc.)
│   ├── Charts/         # Chart components
│   ├── Forms/          # Form components
│   └── Layout/         # Layout components
├── pages/              # Page components
├── hooks/              # Custom React hooks
├── services/           # API and external services
├── store/              # Redux store configuration
├── styles/             # Global styles and themes
├── utils/              # Utility functions
└── types/              # TypeScript type definitions
```

### State Management
```
Redux Store Structure:
├── auth/               # Authentication state
├── accounts/           # Bank accounts data
├── transactions/       # Transaction data
├── budgets/            # Budget data
├── goals/              # Financial goals
├── insights/           # AI insights
└── ui/                 # UI state (theme, modals, etc.)
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn
- Docker (for web deployment)
- Xcode (for iOS development)
- Android Studio (for Android development)

### Web Application Setup

```bash
# Navigate to web directory
cd frontend/web

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test

# Build Docker image
docker build -t mintflow/web .
```

### Mobile Application Setup

```bash
# Navigate to mobile directory
cd mobile

# Install dependencies
npm install

# Install iOS dependencies (macOS only)
cd ios && pod install && cd ..

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start Metro bundler
npm start

# Run on iOS (macOS only)
npm run ios

# Run on Android
npm run android

# Build for production
npm run build:ios     # iOS
npm run build:android # Android
```

## 🎨 Design System

### Color Palette
```css
Primary: #3B82F6 (Blue)
Secondary: #8B5CF6 (Purple)
Success: #10B981 (Green)
Warning: #F59E0B (Amber)
Error: #EF4444 (Red)
Gray Scale: #F9FAFB to #111827
```

### Typography
```css
Font Family: Inter (Web) / System (Mobile)
Sizes: 12px, 14px, 16px, 18px, 20px, 24px, 32px, 48px
Weights: 400 (Regular), 500 (Medium), 600 (Semibold), 700 (Bold)
```

### Components
- **Cards**: Elevated containers with rounded corners
- **Buttons**: Primary, secondary, outline, text variants
- **Forms**: Consistent input styling with validation
- **Charts**: Responsive and interactive data visualization
- **Modals**: Overlay dialogs for actions and details

## 🔐 Security Features

### Web Application
- JWT token management with auto-refresh
- Secure HTTP-only cookie storage
- CSRF protection
- Content Security Policy headers
- XSS prevention
- HTTPS enforcement

### Mobile Applications
- Biometric authentication
- Secure keychain storage
- Certificate pinning
- App transport security
- Jailbreak/root detection
- Screen recording prevention

## 📊 Features Overview

### Dashboard
- **Net Worth Overview**: Real-time net worth calculation
- **Account Summary**: All connected accounts at a glance
- **Recent Transactions**: Latest financial activity
- **Spending Charts**: Visual spending breakdown
- **Budget Progress**: Current budget status
- **AI Insights**: Personalized financial recommendations

### Account Management
- **Bank Connection**: Connect 11,000+ banks via Plaid
- **Account Sync**: Real-time balance and transaction updates
- **Multiple Institutions**: Support for multiple bank relationships
- **Account Types**: Checking, savings, credit cards, investments

### Transaction Management
- **Real-time Sync**: Instant transaction updates
- **AI Categorization**: Automatic transaction categorization
- **Manual Override**: Ability to recategorize transactions
- **Search & Filter**: Advanced transaction filtering
- **Receipt Attachment**: Photo receipt storage (mobile)

### Budget & Goals
- **Flexible Budgets**: Monthly, weekly, yearly budgets
- **Category Budgets**: Budget by spending category
- **Goal Tracking**: Financial goal creation and monitoring
- **Progress Alerts**: Notifications for budget/goal milestones
- **Spending Analysis**: AI-powered spending insights

### Analytics & Insights
- **Spending Trends**: Historical spending analysis
- **Category Breakdown**: Detailed spending by category
- **Income vs Expenses**: Monthly financial flow
- **Net Worth Tracking**: Long-term wealth monitoring
- **AI Recommendations**: Personalized financial advice

## 🚀 Deployment

### Web Application Deployment

#### Development
```bash
# Start development server
npm start
# Access at http://localhost:3000
```

#### Production
```bash
# Build and deploy
./deploy-frontend.sh production web

# Or manual deployment
npm run build
docker build -t mintflow/web .
docker push mintflow/web
kubectl apply -f k8s/frontend-deployment.yaml
```

### Mobile App Deployment

#### Development
```bash
# iOS (macOS only)
npx react-native run-ios

# Android
npx react-native run-android
```

#### Production
```bash
# Build all platforms
./deploy-frontend.sh production all

# iOS only
./deploy-frontend.sh production ios

# Android only  
./deploy-frontend.sh production android
```

## 📱 Platform-Specific Features

### iOS Features
- Face ID / Touch ID authentication
- Apple Pay integration ready
- iOS widgets for quick balance check
- Haptic feedback
- 3D Touch support
- iOS-specific animations

### Android Features
- Fingerprint authentication
- Google Pay integration ready
- Android widgets for quick actions
- Material Design animations
- Adaptive icons
- Android-specific permissions

### Web Features
- Progressive Web App (PWA)
- Offline functionality
- Desktop notifications
- Keyboard shortcuts
- Print-friendly pages
- Browser extension ready

## 🧪 Testing

### Web Application
```bash
# Unit tests
npm test

# Coverage report
npm run test:coverage

# E2E tests
npm run test:e2e

# Accessibility tests
npm run test:a11y
```

### Mobile Applications
```bash
# Unit tests
npm test

# iOS tests
npm run test:ios

# Android tests
npm run test:android

# Detox E2E tests
npm run test:e2e
```

## 📈 Performance

### Web Application Optimizations
- Code splitting and lazy loading
- Image optimization and WebP support
- Service worker for caching
- Bundle analysis and optimization
- CDN delivery for static assets

### Mobile Application Optimizations
- Native module optimization
- Image caching and compression
- Background sync for data updates
- Efficient list rendering
- Memory management

## 🔍 Monitoring & Analytics

### Error Tracking
- Sentry integration for error monitoring
- Performance monitoring
- User session replay
- Crash reporting

### User Analytics
- User behavior tracking
- Feature usage analytics
- Performance metrics
- Conversion funnel analysis

## 🌍 Internationalization

### Supported Languages
- English (default)
- Spanish
- French
- German
- Portuguese

### Localization Features
- Currency formatting by locale
- Date/time formatting
- Number formatting
- RTL language support ready

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Submit a pull request

### Code Standards
- TypeScript for type safety
- ESLint + Prettier for code formatting
- Conventional commits
- Component documentation
- Test coverage > 80%

## 📞 Support

### Getting Help
- 📖 **Documentation**: Check inline code documentation
- 🐛 **Issues**: Report bugs via GitHub issues
- 💬 **Discussions**: Join community discussions
- 📧 **Email**: Contact support@mintflow.com

### Common Issues
- **Build failures**: Check Node.js version and dependencies
- **iOS build issues**: Ensure Xcode is updated
- **Android build issues**: Check Android SDK configuration
- **API connection**: Verify backend service is running

---

**Built with ❤️ by the MintFlow Team**

*Making personal finance accessible, secure, and intelligent for everyone.*