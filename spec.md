# Clueless - Interactive Web Guide Extension

## 1. Technology Stack

### Frontend
- **React 18.2.0** - UI component library
- **TypeScript 5.3.3** - Type-safe JavaScript
- **Plasmo 0.90.5** - Browser extension framework

### Browser Extension
- **Chrome Manifest V3** - Extension platform
- **Chrome Storage API** - Cross-domain state persistence
- **Content Scripts** - DOM manipulation and UI injection

### Development Tools
- **Prettier 3.2.4** - Code formatting
- **Node.js** - Runtime environment
- **npm** - Package management

## 2. Product Overview

Clueless is a Chrome browser extension that provides interactive, step-by-step guidance for web applications. It highlights specific elements on web pages and guides users through multi-step workflows, even across different domains and page navigations.

### Key Features
- **Cross-page Navigation**: Guides persist when clicking links that navigate to new pages
- **Element Highlighting**: Visual overlay system with pulsing green highlights
- **Smart Element Detection**: Multiple strategies to find elements on pages
- **Fallback Element Injection**: Creates guide elements when they don't exist on the page
- **State Persistence**: Maintains guide progress across browser sessions and domains

### Use Cases
- User onboarding for complex web applications
- Feature discovery and adoption
- Step-by-step tutorials for multi-page workflows
- Customer support and training

## 3. Implementation Details

### Core Components

#### Content Script (`content.tsx`)
- **Purpose**: Main orchestrator injected into web pages
- **Responsibilities**:
  - Element resolution and detection
  - Guide state management
  - Cross-page persistence
  - UI rendering coordination

#### Overlay Guide (`overlayGuide.tsx`)
- **Purpose**: Visual highlighting component
- **Features**:
  - Green pulsing border around target elements
  - Dark backdrop to focus attention
  - Click instruction tooltips
  - Responsive positioning

### Element Resolution Strategy
1. **ID Matching**: Find elements by exact ID match
2. **Href Matching**: Locate links by href attribute
3. **Data Attribute Matching**: Match by data-title attributes
4. **Text Content Matching**: Find elements by exact text content
5. **Fallback Injection**: Create and inject missing elements

### State Management
```typescript
interface GuideState {
  htmlList: string[];      // Original HTML elements to find
  currentIndex: number;    // Current step in the guide
  isActive: boolean;       // Whether guide is running
  timestamp: number;       // When state was saved
}
```

### Storage Implementation
- **Primary**: `chrome.storage.local` for cross-domain persistence
- **Fallback**: `localStorage` for development environments
- **Expiration**: 24-hour automatic cleanup of stale states

## 4. API Endpoints

### Chrome Extension APIs

#### Storage API
```typescript
// Save guide state
chrome.storage.local.set({ 
  clueless_guide_state: GuideState 
})

// Load guide state
chrome.storage.local.get('clueless_guide_state')

// Clear guide state
chrome.storage.local.remove('clueless_guide_state')
```

#### Content Script API
```typescript
// Start new guide
startGuide(htmlList: string[]): Promise<void>

// Advance to next step
advance(): Promise<void>

// Stop current guide
stopGuide(): Promise<void>
```

### Future API Endpoints (Backend Integration)
```typescript
// Get guide configuration
GET /api/guides/{guideId}
Response: {
  id: string;
  name: string;
  steps: string[];
  targetUrl: string;
}

// Track guide progress
POST /api/guides/{guideId}/progress
Body: {
  userId: string;
  stepIndex: number;
  completed: boolean;
}

// Get user's active guides
GET /api/users/{userId}/guides
Response: {
  activeGuides: Guide[];
  completedGuides: Guide[];
}
```

## 5. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Extension                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Popup     │  │  Background │  │    Content Script   │ │
│  │   (UI)      │  │   Service   │  │   (Main Logic)      │ │
│  │             │  │   Worker    │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                Chrome Storage API                           │
│              (Cross-domain persistence)                     │
├─────────────────────────────────────────────────────────────┤
│                    Web Pages                                │
│  ┌─────────────────┐              ┌─────────────────────┐   │
│  │   Page A        │    Navigate  │      Page B         │   │
│  │ docs.pinecone.io│ ──────────► │  app.pinecone.io    │   │
│  │                 │              │                     │   │
│  │ ┌─────────────┐ │              │ ┌─────────────────┐ │   │
│  │ │ Overlay     │ │              │ │ Overlay         │ │   │
│  │ │ Guide       │ │              │ │ Guide           │ │   │
│  │ │ (Step 1)    │ │              │ │ (Step 2)        │ │   │
│  │ └─────────────┘ │              │ └─────────────────┘ │   │
│  └─────────────────┘              └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Component Flow
1. **Content Script Injection**: Automatically injected into all web pages
2. **State Check**: Checks for existing guide state on page load
3. **Element Resolution**: Finds target elements using multiple strategies
4. **Overlay Rendering**: Creates visual highlights and instructions
5. **User Interaction**: Captures clicks and advances guide
6. **State Persistence**: Saves progress before navigation
7. **Cross-page Resume**: Automatically resumes on new pages

## 6. Additional Information

### Browser Compatibility
- **Chrome**: Full support (Manifest V3)
- **Edge**: Compatible (Chromium-based)
- **Firefox**: Requires Manifest V2 adaptation
- **Safari**: Requires WebExtension adaptation

### Performance Considerations
- **DOM Observation**: Uses MutationObserver for dynamic content
- **Debounced Updates**: Scroll and resize events are debounced
- **Memory Management**: Automatic cleanup of event listeners
- **State Expiration**: 24-hour automatic cleanup prevents storage bloat

### Security Features
- **Content Security Policy**: Compliant with strict CSP
- **Sandboxed Execution**: Isolated from page JavaScript
- **Permission Model**: Minimal required permissions
- **Cross-origin Safety**: Secure cross-domain state sharing

### Development Setup
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Package extension
npm run package
```

### Extension Permissions
```json
{
  "permissions": ["storage"],
  "host_permissions": ["https://*/*", "http://*/*"]
}
```

### Future Enhancements
- **Analytics Integration**: Track guide completion rates
- **A/B Testing**: Test different guide flows
- **Conditional Logic**: Branching guides based on user actions
- **Multi-language Support**: Internationalization
- **Mobile Support**: Responsive design for mobile browsers
- **Voice Guidance**: Audio instructions for accessibility
