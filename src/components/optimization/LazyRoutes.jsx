/**
 * Lazy Routes with Code Splitting
 * Optimized route components with lazy loading and error boundaries
 */

import React, { Suspense, lazy } from 'react';
import { Route, Routes } from 'react-router-dom';
import { ErrorBoundary } from 'react-error-boundary';
import LoadingSpinner from '@/components/ui/loading-spinner';
import { performanceOptimizationService } from '@/services/performanceOptimizationService';

// Enhanced loading component with performance tracking
const EnhancedLoadingSpinner = ({ componentName }) => {
  React.useEffect(() => {
    if (typeof window !== 'undefined' && window.markComponentStart) {
      window.markComponentStart(`lazy-${componentName}`);
    }
  }, [componentName]);

  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <LoadingSpinner size="lg" />
      <span className="ml-3 text-sm text-gray-600">Loading {componentName}...</span>
    </div>
  );
};

// Error fallback component
const RouteErrorFallback = ({ error, resetErrorBoundary, componentName }) => (
  <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
    <div className="text-center">
      <h2 className="text-xl font-semibold text-red-600 mb-2">
        Failed to load {componentName}
      </h2>
      <p className="text-gray-600 mb-4">
        {error?.message || 'An unexpected error occurred'}
      </p>
      <button
        onClick={resetErrorBoundary}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Try Again
      </button>
    </div>
  </div>
);

// Higher-order component for lazy loading with performance tracking
const withLazyLoading = (importFunc, componentName, preloadDeps = []) => {
  const LazyComponent = lazy(async () => {
    // Mark loading start
    if (typeof window !== 'undefined' && window.markComponentStart) {
      window.markComponentStart(`lazy-${componentName}`);
    }

    try {
      // Preload dependencies if specified
      if (preloadDeps.length > 0) {
        performanceOptimizationService.preloadResources(preloadDeps);
      }

      const module = await importFunc();
      
      // Mark loading end
      if (typeof window !== 'undefined' && window.markComponentEnd) {
        window.markComponentEnd(`lazy-${componentName}`);
      }

      return module;
    } catch (error) {
      console.error(`Failed to load ${componentName}:`, error);
      throw error;
    }
  });

  LazyComponent.displayName = `Lazy(${componentName})`;
  return LazyComponent;
};

// Lazy-loaded page components with performance optimization
const Dashboard = withLazyLoading(
  () => import('@/pages/Dashboard'),
  'Dashboard',
  [
    { url: '/api/dashboard/metrics', type: 'fetch' },
    { url: '/assets/dashboard-bg.jpg', type: 'image' }
  ]
);

const PerformanceAnalytics = withLazyLoading(
  () => import('@/pages/PerformanceAnalytics'),
  'PerformanceAnalytics',
  [
    { url: '/api/analytics/performance', type: 'fetch' }
  ]
);

const ContentCreation = withLazyLoading(
  () => import('@/pages/ContentCreation'),
  'ContentCreation'
);

const StrategicPlanning = withLazyLoading(
  () => import('@/pages/StrategicPlanning'),
  'StrategicPlanning'
);

const CustomerSupport = withLazyLoading(
  () => import('@/pages/CustomerSupport'),
  'CustomerSupport'
);

const SalesIntelligence = withLazyLoading(
  () => import('@/pages/SalesIntelligence'),
  'SalesIntelligence'
);

const DataAnalysis = withLazyLoading(
  () => import('@/pages/DataAnalysis'),
  'DataAnalysis'
);

const MarketingAutomation = withLazyLoading(
  () => import('@/pages/MarketingAutomation'),
  'MarketingAutomation'
);

const FinancialAnalysis = withLazyLoading(
  () => import('@/pages/FinancialAnalysis'),
  'FinancialAnalysis'
);

const OperationsOptimization = withLazyLoading(
  () => import('@/pages/OperationsOptimization'),
  'OperationsOptimization'
);

const CustomAgents = withLazyLoading(
  () => import('@/pages/CustomAgents'),
  'CustomAgents'
);

const SocialCampaigns = withLazyLoading(
  () => import('@/pages/SocialCampaigns'),
  'SocialCampaigns'
);

const MetaAdsManager = withLazyLoading(
  () => import('@/pages/MetaAdsManager'),
  'MetaAdsManager'
);

const LinkedInAdsManager = withLazyLoading(
  () => import('@/pages/LinkedInAdsManager'),
  'LinkedInAdsManager'
);

const ReportBuilder = withLazyLoading(
  () => import('@/pages/ReportBuilder'),
  'ReportBuilder'
);

const UserProfile = withLazyLoading(
  () => import('@/pages/UserProfile'),
  'UserProfile'
);

const Settings = withLazyLoading(
  () => import('@/pages/Settings'),
  'Settings'
);

// Route component with error boundary
const LazyRoute = ({ path, Component, componentName, ...props }) => (
  <Route
    path={path}
    element={
      <ErrorBoundary
        FallbackComponent={(errorProps) => (
          <RouteErrorFallback {...errorProps} componentName={componentName} />
        )}
        onError={(error, errorInfo) => {
          console.error(`Route error in ${componentName}:`, error, errorInfo);
          // Log to error service
          if (window.errorHandlingService) {
            window.errorHandlingService.handleComponentError(error, {
              component: componentName,
              route: path,
              errorInfo
            });
          }
        }}
      >
        <Suspense fallback={<EnhancedLoadingSpinner componentName={componentName} />}>
          <Component {...props} />
        </Suspense>
      </ErrorBoundary>
    }
  />
);

// Main lazy routes component
export const LazyRoutes = () => {
  return (
    <Routes>
      {/* Dashboard Routes */}
      <LazyRoute 
        path="/dashboard" 
        Component={Dashboard} 
        componentName="Dashboard" 
      />
      
      {/* Analytics Routes */}
      <LazyRoute 
        path="/performance-analytics" 
        Component={PerformanceAnalytics} 
        componentName="Performance Analytics" 
      />
      
      {/* AI Agent Routes */}
      <LazyRoute 
        path="/content-creation" 
        Component={ContentCreation} 
        componentName="Content Creation" 
      />
      <LazyRoute 
        path="/strategic-planning" 
        Component={StrategicPlanning} 
        componentName="Strategic Planning" 
      />
      <LazyRoute 
        path="/customer-support" 
        Component={CustomerSupport} 
        componentName="Customer Support" 
      />
      <LazyRoute 
        path="/sales-intelligence" 
        Component={SalesIntelligence} 
        componentName="Sales Intelligence" 
      />
      <LazyRoute 
        path="/data-analysis" 
        Component={DataAnalysis} 
        componentName="Data Analysis" 
      />
      <LazyRoute 
        path="/marketing-automation" 
        Component={MarketingAutomation} 
        componentName="Marketing Automation" 
      />
      <LazyRoute 
        path="/financial-analysis" 
        Component={FinancialAnalysis} 
        componentName="Financial Analysis" 
      />
      <LazyRoute 
        path="/operations-optimization" 
        Component={OperationsOptimization} 
        componentName="Operations Optimization" 
      />
      <LazyRoute 
        path="/custom-agents" 
        Component={CustomAgents} 
        componentName="Custom Agents" 
      />
      
      {/* Social Media Routes */}
      <LazyRoute 
        path="/social-campaigns" 
        Component={SocialCampaigns} 
        componentName="Social Campaigns" 
      />
      <LazyRoute 
        path="/meta-ads-manager" 
        Component={MetaAdsManager} 
        componentName="Meta Ads Manager" 
      />
      <LazyRoute 
        path="/linkedin-ads-manager" 
        Component={LinkedInAdsManager} 
        componentName="LinkedIn Ads Manager" 
      />
      
      {/* Utility Routes */}
      <LazyRoute 
        path="/report-builder" 
        Component={ReportBuilder} 
        componentName="Report Builder" 
      />
      <LazyRoute 
        path="/profile" 
        Component={UserProfile} 
        componentName="User Profile" 
      />
      <LazyRoute 
        path="/settings" 
        Component={Settings} 
        componentName="Settings" 
      />
    </Routes>
  );
};

// Route preloader for critical routes
export const preloadCriticalRoutes = () => {
  // Preload dashboard and most commonly accessed routes
  const criticalRoutes = [
    Dashboard,
    PerformanceAnalytics,
    ContentCreation,
    SocialCampaigns
  ];

  // Preload on idle
  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(() => {
      criticalRoutes.forEach(Component => {
        // This will trigger the lazy loading
        const preloadPromise = Component._payload?._result || Component._payload?._value;
        if (preloadPromise && typeof preloadPromise.then === 'function') {
          preloadPromise.catch(() => {
            // Ignore preload errors
          });
        }
      });
    });
  }
};

// Route prefetcher for predictive loading
export const prefetchRoute = (routeName) => {
  const routeMap = {
    dashboard: Dashboard,
    analytics: PerformanceAnalytics,
    content: ContentCreation,
    strategic: StrategicPlanning,
    support: CustomerSupport,
    sales: SalesIntelligence,
    data: DataAnalysis,
    marketing: MarketingAutomation,
    financial: FinancialAnalysis,
    operations: OperationsOptimization,
    agents: CustomAgents,
    social: SocialCampaigns,
    meta: MetaAdsManager,
    linkedin: LinkedInAdsManager,
    reports: ReportBuilder,
    profile: UserProfile,
    settings: Settings
  };

  const Component = routeMap[routeName];
  if (Component) {
    // Trigger lazy loading
    const preloadPromise = Component._payload?._result || Component._payload?._value;
    if (preloadPromise && typeof preloadPromise.then === 'function') {
      return preloadPromise.catch(() => {
        console.warn(`Failed to prefetch route: ${routeName}`);
      });
    }
  }
  
  return Promise.resolve();
};

export default LazyRoutes;
