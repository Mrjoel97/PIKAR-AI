# 🔧 PIKAR AI - Integration Guide

**Complete setup guide for all implemented features**

---

## 🚀 **QUICK START**

### **1. Environment Setup**

Create `.env` file with required variables:

```bash
# Base44 Integration
BASE44_API_KEY=your_base44_api_key_here
BASE44_APP_ID=your_base44_app_id_here
BASE44_API_URL=https://api.base44.com

# Email Service (Choose one)
EMAIL_PROVIDER=sendgrid  # sendgrid, ses, mailgun, smtp
EMAIL_API_KEY=your_email_api_key_here
EMAIL_FROM_ADDRESS=noreply@pikar-ai.com
EMAIL_FROM_NAME=PIKAR AI

# Database
DATABASE_URL=your_database_connection_string
REDIS_URL=your_redis_connection_string

# Payment Processing
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret

# Security
JWT_SECRET=your_jwt_secret_key
ENCRYPTION_KEY=your_encryption_key

# External APIs
SLACK_WEBHOOK_URL=your_slack_webhook_url
```

### **2. Service Initialization**

Add to your main application file:

```javascript
import { tierService } from '@/services/tierService'
import { emailNotificationService } from '@/services/emailNotificationService'
import { abTestingService } from '@/services/abTestingService'
import { userManagementService } from '@/services/userManagementService'

// Initialize services on app startup
async function initializeServices() {
  try {
    await tierService.initialize()
    await emailNotificationService.initialize()
    await abTestingService.initialize()
    await userManagementService.initialize()
    
    console.log('✅ All services initialized successfully')
  } catch (error) {
    console.error('❌ Service initialization failed:', error)
    process.exit(1)
  }
}

// Call during app startup
initializeServices()
```

### **3. React Context Setup**

Wrap your app with the tier context:

```jsx
import { TierProvider } from '@/contexts/TierContext'

function App() {
  return (
    <TierProvider>
      {/* Your app components */}
    </TierProvider>
  )
}
```

---

## 💰 **PRICING TIER SYSTEM**

### **Basic Usage**

```jsx
import { useTier } from '@/hooks/useTier'

function MyComponent() {
  const { 
    currentTier, 
    hasFeatureAccess, 
    trackUsage, 
    upgradeTier 
  } = useTier()

  // Check feature access
  if (!hasFeatureAccess('customIntegrations')) {
    return <TierGate requiredTier="pro" feature="customIntegrations" />
  }

  // Track usage
  const handleAgentExecution = async () => {
    try {
      await trackUsage('monthlyExecutions', 1)
      // Execute agent...
    } catch (error) {
      // Handle quota exceeded
      console.error('Quota exceeded:', error)
    }
  }

  return (
    <div>
      <h2>Current Tier: {currentTier?.name}</h2>
      <button onClick={handleAgentExecution}>
        Execute Agent
      </button>
    </div>
  )
}
```

### **Tier Gate Component**

```jsx
import TierGate from '@/components/TierGate'

function PremiumFeature() {
  return (
    <TierGate 
      requiredTier="pro" 
      feature="advancedAnalytics"
      quotaType="monthlyExecutions"
    >
      {/* Premium feature content */}
      <AdvancedAnalyticsDashboard />
    </TierGate>
  )
}
```

---

## 📧 **EMAIL NOTIFICATIONS**

### **Sending Notifications**

```javascript
import { emailNotificationService } from '@/services/emailNotificationService'

// Send welcome email
await emailNotificationService.sendNotification(
  userId,
  'welcome',
  {
    userName: 'John Doe',
    activationLink: 'https://app.pikar-ai.com/activate/token'
  }
)

// Send agent completion notification
await emailNotificationService.sendNotification(
  userId,
  'agent_execution_complete',
  {
    userName: 'John Doe',
    agentType: 'Strategic Planning',
    executionId: 'exec_123',
    duration: '2 minutes',
    results: 'Generated 5 strategic recommendations',
    dashboardLink: 'https://app.pikar-ai.com/dashboard'
  }
)
```

### **User Preferences Component**

```jsx
import EmailPreferences from '@/components/notifications/EmailPreferences'

function SettingsPage() {
  return (
    <div>
      <h1>Notification Settings</h1>
      <EmailPreferences />
    </div>
  )
}
```

### **Notification Center**

```jsx
import NotificationCenter from '@/components/notifications/NotificationCenter'

function NotificationsPage() {
  return <NotificationCenter />
}
```

---

## 🧪 **A/B TESTING**

### **Creating Tests**

```javascript
import { abTestingService } from '@/services/abTestingService'

// Create A/B test
const test = await abTestingService.createTest(userId, {
  name: 'Homepage CTA Button',
  description: 'Test different CTA button colors',
  hypothesis: 'Blue button will increase conversions by 15%',
  primaryMetric: 'conversion_rate',
  variants: [
    {
      name: 'Control (Green)',
      description: 'Current green button',
      configuration: { buttonColor: 'green' }
    },
    {
      name: 'Variant (Blue)',
      description: 'New blue button',
      configuration: { buttonColor: 'blue' }
    }
  ],
  trafficAllocation: 0.5, // 50% of users
  significanceLevel: 0.05 // 95% confidence
})

// Start the test
await abTestingService.startTest(userId, test.id)
```

### **Using Tests in Components**

```jsx
import { abTestingService } from '@/services/abTestingService'

function CTAButton({ userId }) {
  const [variant, setVariant] = useState(null)

  useEffect(() => {
    // Get user's variant assignment
    const assignment = abTestingService.assignUserToVariant(userId, 'test_123')
    if (assignment) {
      setVariant(assignment.variantId)
    }
  }, [userId])

  const handleClick = async () => {
    // Track conversion
    await abTestingService.trackConversion(
      userId, 
      'test_123', 
      'conversion_rate', 
      1
    )
    
    // Handle click...
  }

  const buttonColor = variant === 'variant_blue' ? 'blue' : 'green'

  return (
    <button 
      style={{ backgroundColor: buttonColor }}
      onClick={handleClick}
    >
      Get Started
    </button>
  )
}
```

---

## 👥 **USER MANAGEMENT**

### **Creating Users**

```javascript
import { userManagementService } from '@/services/userManagementService'

// Create new user
const user = await userManagementService.createUser({
  email: 'john@example.com',
  firstName: 'John',
  lastName: 'Doe',
  roleId: 'member'
})

// Create team
const team = await userManagementService.createTeam({
  name: 'Marketing Team',
  description: 'Marketing and growth team',
  visibility: 'private'
}, creatorUserId)

// Add user to team
await userManagementService.addUserToTeam(
  team.id, 
  user.id, 
  'member', 
  creatorUserId
)
```

### **Permission Checking**

```javascript
// Check specific permission
const canManageUsers = userManagementService.hasPermission(
  userId, 
  'users.manage'
)

// Get all user permissions
const permissions = userManagementService.getUserPermissions(userId)

// Use in components
function AdminPanel({ userId }) {
  const canManageUsers = userManagementService.hasPermission(userId, 'users.manage')
  
  if (!canManageUsers) {
    return <div>Access denied</div>
  }
  
  return <UserManagementInterface />
}
```

---

## 🚀 **DEPLOYMENT**

### **GitHub Actions Setup**

1. Add repository secrets:
   - `BASE44_API_KEY`
   - `BASE44_APP_ID`
   - `SLACK_WEBHOOK` (optional)

2. The workflow will automatically:
   - Run security scans
   - Build and test the application
   - Deploy to Base44
   - Perform health checks
   - Send notifications

### **Manual Deployment**

```bash
# Build the application
npm run build

# Deploy to Base44 (using their CLI)
base44 deploy --app-id your-app-id --build-dir dist
```

---

## 🔧 **DATABASE INTEGRATION**

### **Required Tables**

```sql
-- Users table
CREATE TABLE users (
  id VARCHAR(255) PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  first_name VARCHAR(255) NOT NULL,
  last_name VARCHAR(255) NOT NULL,
  role_id VARCHAR(50) NOT NULL,
  status VARCHAR(50) DEFAULT 'active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Teams table
CREATE TABLE teams (
  id VARCHAR(255) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  created_by VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id)
);

-- User tiers table
CREATE TABLE user_tiers (
  user_id VARCHAR(255) PRIMARY KEY,
  tier_id VARCHAR(50) NOT NULL,
  start_date TIMESTAMP NOT NULL,
  billing_info JSON,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Usage tracking table
CREATE TABLE usage_tracking (
  user_id VARCHAR(255),
  metric_type VARCHAR(100),
  value INT DEFAULT 0,
  last_reset TIMESTAMP,
  PRIMARY KEY (user_id, metric_type),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- A/B tests table
CREATE TABLE ab_tests (
  id VARCHAR(255) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  status VARCHAR(50) NOT NULL,
  config JSON NOT NULL,
  created_by VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Email notifications table
CREATE TABLE email_notifications (
  id VARCHAR(255) PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  type VARCHAR(100) NOT NULL,
  status VARCHAR(50) NOT NULL,
  sent_at TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## 🔍 **MONITORING & ANALYTICS**

### **Service Health Checks**

```javascript
// Add health check endpoints
app.get('/health/tiers', async (req, res) => {
  const stats = tierService.getTierStatistics()
  res.json({ status: 'healthy', stats })
})

app.get('/health/notifications', async (req, res) => {
  const stats = emailNotificationService.getDeliveryStatistics()
  res.json({ status: 'healthy', stats })
})
```

### **Error Monitoring**

```javascript
// Set up error tracking
import { auditService } from '@/services/auditService'

process.on('unhandledRejection', (error) => {
  auditService.logSystem.error(error, 'unhandled_rejection')
})

process.on('uncaughtException', (error) => {
  auditService.logSystem.error(error, 'uncaught_exception')
  process.exit(1)
})
```

---

## 🎯 **TESTING**

### **Unit Tests**

```javascript
import { tierService } from '@/services/tierService'

describe('TierService', () => {
  test('should check feature access correctly', () => {
    const hasAccess = tierService.hasFeatureAccess('user123', 'customIntegrations')
    expect(hasAccess).toBe(true)
  })

  test('should track usage correctly', async () => {
    const result = await tierService.trackUsage('user123', 'monthlyExecutions', 1)
    expect(result.success).toBe(true)
  })
})
```

### **Integration Tests**

```javascript
describe('Email Integration', () => {
  test('should send welcome email', async () => {
    const result = await emailNotificationService.sendNotification(
      'user123',
      'welcome',
      { userName: 'Test User' }
    )
    expect(result.success).toBe(true)
  })
})
```

---

## 📞 **SUPPORT**

For implementation support:
- 📧 Email: dev@pikar-ai.com
- 📚 Documentation: https://docs.pikar-ai.com
- 🐛 Issues: https://github.com/pikar-ai/issues

---

*Integration guide last updated: December 1, 2024*
