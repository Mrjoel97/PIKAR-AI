import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Lock, ArrowRight, Crown } from 'lucide-react';

/**
 * Protected Route Component
 * Handles authentication and authorization for routes
 */
export function ProtectedRoute({ 
  children, 
  requiredPermission = null,
  requiredPermissions = [],
  requireAll = false,
  fallback = null,
  redirectTo = '/login'
}) {
  const { isAuthenticated, isLoading, user, hasPermission, hasAnyPermission } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  // Check permissions if required
  if (requiredPermission || requiredPermissions.length > 0) {
    const permissions = requiredPermission ? [requiredPermission] : requiredPermissions;
    
    let hasAccess = false;
    if (requireAll) {
      hasAccess = permissions.every(permission => hasPermission(permission));
    } else {
      hasAccess = hasAnyPermission(permissions);
    }

    if (!hasAccess) {
      return fallback || <AccessDenied permissions={permissions} userTier={user?.tier} />;
    }
  }

  return children;
}

/**
 * Access Denied Component
 * Shown when user doesn't have required permissions
 */
export function AccessDenied({ permissions = [], userTier = 'solopreneur' }) {
  const tierUpgrades = {
    solopreneur: 'startup',
    startup: 'sme',
    sme: 'enterprise'
  };

  const nextTier = tierUpgrades[userTier];

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mb-4">
            <Lock className="w-8 h-8 text-amber-600" />
          </div>
          <CardTitle className="text-xl font-bold text-gray-900">
            Access Restricted
          </CardTitle>
          <CardDescription className="text-base">
            This feature requires a higher subscription tier to access.
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600 mb-2">Current Plan:</p>
            <div className="flex items-center gap-2">
              <Crown className="w-4 h-4 text-emerald-600" />
              <span className="font-medium capitalize">{userTier}</span>
            </div>
          </div>

          {permissions.length > 0 && (
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm text-blue-800 font-medium mb-2">Required Permissions:</p>
              <ul className="text-sm text-blue-700 space-y-1">
                {permissions.map((permission, index) => (
                  <li key={index} className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-blue-600 rounded-full"></div>
                    {formatPermissionName(permission)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-col gap-3">
            {nextTier && (
              <Button className="w-full">
                <Crown className="w-4 h-4 mr-2" />
                Upgrade to {formatTierName(nextTier)}
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            )}
            
            <Button variant="outline" className="w-full" onClick={() => window.history.back()}>
              Go Back
            </Button>
          </div>

          <div className="text-center">
            <p className="text-xs text-gray-500">
              Need help? Contact our{' '}
              <a href="mailto:support@pikar-ai.com" className="text-emerald-600 hover:underline">
                support team
              </a>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Permission Guard Component
 * Conditionally renders children based on permissions
 */
export function PermissionGuard({ 
  permission = null,
  permissions = [],
  requireAll = false,
  fallback = null,
  children 
}) {
  const { hasPermission, hasAnyPermission } = useAuth();

  const permissionsToCheck = permission ? [permission] : permissions;
  
  if (permissionsToCheck.length === 0) {
    return children;
  }

  let hasAccess = false;
  if (requireAll) {
    hasAccess = permissionsToCheck.every(perm => hasPermission(perm));
  } else {
    hasAccess = hasAnyPermission(permissionsToCheck);
  }

  if (!hasAccess) {
    return fallback;
  }

  return children;
}

/**
 * Tier Guard Component
 * Conditionally renders children based on user tier
 */
export function TierGuard({ 
  allowedTiers = [],
  minTier = null,
  fallback = null,
  children 
}) {
  const { user } = useAuth();

  if (!user) {
    return fallback;
  }

  const tierHierarchy = ['solopreneur', 'startup', 'sme', 'enterprise'];
  const userTierIndex = tierHierarchy.indexOf(user.tier);

  let hasAccess = false;

  if (allowedTiers.length > 0) {
    hasAccess = allowedTiers.includes(user.tier);
  } else if (minTier) {
    const minTierIndex = tierHierarchy.indexOf(minTier);
    hasAccess = userTierIndex >= minTierIndex;
  }

  if (!hasAccess) {
    return fallback;
  }

  return children;
}

/**
 * Authentication Guard Hook
 * Returns authentication and permission checking functions
 */
export function useAuthGuard() {
  const { isAuthenticated, user, hasPermission, hasAnyPermission } = useAuth();

  const requireAuth = (callback) => {
    if (!isAuthenticated) {
      throw new Error('Authentication required');
    }
    return callback();
  };

  const requirePermission = (permission, callback) => {
    if (!hasPermission(permission)) {
      throw new Error(`Permission required: ${permission}`);
    }
    return callback();
  };

  const requireAnyPermission = (permissions, callback) => {
    if (!hasAnyPermission(permissions)) {
      throw new Error(`One of these permissions required: ${permissions.join(', ')}`);
    }
    return callback();
  };

  const requireTier = (minTier, callback) => {
    const tierHierarchy = ['solopreneur', 'startup', 'sme', 'enterprise'];
    const userTierIndex = tierHierarchy.indexOf(user?.tier);
    const minTierIndex = tierHierarchy.indexOf(minTier);

    if (userTierIndex < minTierIndex) {
      throw new Error(`Tier ${minTier} or higher required`);
    }
    return callback();
  };

  return {
    requireAuth,
    requirePermission,
    requireAnyPermission,
    requireTier,
    isAuthenticated,
    user
  };
}

// Utility functions
function formatPermissionName(permission) {
  return permission
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatTierName(tier) {
  return tier.charAt(0).toUpperCase() + tier.slice(1);
}
