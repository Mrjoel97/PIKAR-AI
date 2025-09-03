import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { toast } from 'sonner';
import { supabase } from '@/lib/supabase';

// Auth context
const AuthContext = createContext();

// Auth actions
const AUTH_ACTIONS = {
  LOGIN_START: 'LOGIN_START',
  LOGIN_SUCCESS: 'LOGIN_SUCCESS',
  LOGIN_FAILURE: 'LOGIN_FAILURE',
  LOGOUT: 'LOGOUT',
  REFRESH_TOKEN: 'REFRESH_TOKEN',
  UPDATE_USER: 'UPDATE_USER',
  SET_LOADING: 'SET_LOADING'
};

// Permission definitions for each tier (mirrors previous mapping)
const TIER_PERMISSIONS = {
  solopreneur: [
    'basic_agents',
    'basic_analytics',
    'basic_campaigns',
    'file_upload',
    'profile_management'
  ],
  startup: [
    'basic_agents',
    'basic_analytics',
    'basic_campaigns',
    'team_collaboration',
    'advanced_agents',
    'file_upload',
    'profile_management',
    'api_access'
  ],
  sme: [
    'all_agents',
    'advanced_analytics',
    'workflow_templates',
    'team_collaboration',
    'advanced_campaigns',
    'custom_reports',
    'file_upload',
    'profile_management',
    'api_access',
    'integrations'
  ],
  enterprise: [
    'all_features',
    'custom_integrations',
    'priority_support',
    'advanced_security',
    'audit_logs',
    'custom_branding',
    'sso',
    'advanced_permissions',
    'bulk_operations',
    'data_export'
  ]
};

// Initial state
const initialState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
  tokens: {
    accessToken: null,
    refreshToken: null
  }
};

// Auth reducer
function authReducer(state, action) {
  switch (action.type) {
    case AUTH_ACTIONS.LOGIN_START:
      return {
        ...state,
        isLoading: true,
        error: null
      };

    case AUTH_ACTIONS.LOGIN_SUCCESS:
      return {
        ...state,
        user: action.payload.user,
        tokens: action.payload.tokens,
        isAuthenticated: true,
        isLoading: false,
        error: null
      };

    case AUTH_ACTIONS.LOGIN_FAILURE:
      return {
        ...state,
        user: null,
        tokens: { accessToken: null, refreshToken: null },
        isAuthenticated: false,
        isLoading: false,
        error: action.payload.error
      };

    case AUTH_ACTIONS.LOGOUT:
      return {
        ...initialState,
        isLoading: false
      };

    case AUTH_ACTIONS.REFRESH_TOKEN:
      return {
        ...state,
        tokens: action.payload.tokens
      };

    case AUTH_ACTIONS.UPDATE_USER:
      return {
        ...state,
        user: { ...state.user, ...action.payload.user }
      };

    case AUTH_ACTIONS.SET_LOADING:
      return {
        ...state,
        isLoading: action.payload.isLoading
      };

    default:
      return state;
  }
}

// Auth provider component
export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Initialize auth state on app load
  useEffect(() => {
    const sub = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (session?.user) {
        const profile = await supabase.from('profiles').select('*').eq('id', session.user.id).single();
        dispatch({
          type: AUTH_ACTIONS.LOGIN_SUCCESS,
          payload: { user: { id: session.user.id, email: session.user.email, tier: profile.data?.tier || 'solopreneur', admin_role: profile.data?.admin_role, profile: profile.data }, tokens: { accessToken: session?.access_token || null, refreshToken: session?.refresh_token || null } }
        });
      } else {
        dispatch({ type: AUTH_ACTIONS.LOGOUT });
      }
    });
    initializeAuth();
    return () => { sub.data?.subscription?.unsubscribe?.(); };
  }, []);

  // Supabase auto refreshes tokens; no manual timer needed

  const initializeAuth = async () => {
    try {
      dispatch({ type: AUTH_ACTIONS.SET_LOADING, payload: { isLoading: true } });
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        const { data: profile } = await supabase.from('profiles').select('*').eq('id', session.user.id).single();
        dispatch({
          type: AUTH_ACTIONS.LOGIN_SUCCESS,
          payload: { user: { id: session.user.id, email: session.user.email, tier: profile?.tier || 'solopreneur', admin_role: profile?.admin_role, profile }, tokens: { accessToken: session?.access_token || null, refreshToken: session?.refresh_token || null } }
        });
      }
    } catch (error) {
      console.error('Auth initialization failed:', error);
    } finally {
      dispatch({ type: AUTH_ACTIONS.SET_LOADING, payload: { isLoading: false } });
    }
  };

  const login = async ({ email, password }) => {
    try {
      dispatch({ type: AUTH_ACTIONS.LOGIN_START });
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      const { session, user } = data;
      const { data: profile } = await supabase.from('profiles').select('*').eq('id', user.id).single();
      dispatch({
        type: AUTH_ACTIONS.LOGIN_SUCCESS,
        payload: { user: { id: user.id, email: user.email, tier: profile?.tier || 'solopreneur', admin_role: profile?.admin_role, profile }, tokens: { accessToken: session?.access_token || null, refreshToken: session?.refresh_token || null } }
      });
      toast.success('Login successful!');
      return { success: true };
    } catch (error) {
      const errorMessage = error.message || 'Login failed';
      dispatch({ type: AUTH_ACTIONS.LOGIN_FAILURE, payload: { error: errorMessage } });
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const register = async ({ email, password, ...metadata }) => {
    try {
      dispatch({ type: AUTH_ACTIONS.LOGIN_START });
      const { data, error } = await supabase.auth.signUp({ email, password, options: { data: metadata } });
      if (error) throw error;
      // If email confirmation is required, session may be null
      const user = data.user;
      const session = data.session;
      // Profile row will be created by trigger; fetch it if session exists
      let profile = null;
      if (session?.user?.id) {
        const { data: p } = await supabase.from('profiles').select('*').eq('id', session.user.id).single();
        profile = p;
      }
      dispatch({
        type: AUTH_ACTIONS.LOGIN_SUCCESS,
        payload: { user: user ? { id: user.id, email: user.email, tier: profile?.tier || 'solopreneur', admin_role: profile?.admin_role, profile } : null, tokens: { accessToken: session?.access_token || null, refreshToken: session?.refresh_token || null } }
      });
      toast.success('Registration successful! Check your email to verify your account.');
      return { success: true };
    } catch (error) {
      const errorMessage = error.message || 'Registration failed';
      dispatch({ type: AUTH_ACTIONS.LOGIN_FAILURE, payload: { error: errorMessage } });
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const logout = async () => {
    try {
      await supabase.auth.signOut();
      dispatch({ type: AUTH_ACTIONS.LOGOUT });
      toast.success('Logged out successfully');
    } catch (error) {
      console.error('Logout error:', error);
      dispatch({ type: AUTH_ACTIONS.LOGOUT });
    }
  };

  const refreshToken = async () => {
    try {
      const storedTokens = await authService.getStoredTokens();
      if (!storedTokens.refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await authService.refreshToken(storedTokens.refreshToken);

      if (response.success) {
        const { tokens } = response.data;
        await authService.storeTokens(tokens);

        dispatch({
          type: AUTH_ACTIONS.REFRESH_TOKEN,
          payload: { tokens }
        });

        return tokens;
      } else {
        throw new Error('Token refresh failed');
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
      // If refresh fails, logout user
      logout();
      return null;
    }
  };

  const updateUser = (userData) => {
    dispatch({
      type: AUTH_ACTIONS.UPDATE_USER,
      payload: { user: userData }
    });
  };

  const hasPermission = (permission) => {
    if (!state.user) return false;
    return authService.hasPermission(state.user.tier, permission);
  };

  const hasAnyPermission = (permissions) => {
    if (!state.user) return false;
    return permissions.some(permission => hasPermission(permission));
  };

  const contextValue = {
    // State
    user: state.user,
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    error: state.error,
    tokens: state.tokens,
    
    // Actions
    login,
    register,
    logout,
    refreshToken,
    updateUser,
    
    // Permissions
    hasPermission,
    hasAnyPermission
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// HOC for components that require authentication
export function withAuth(Component) {
  return function AuthenticatedComponent(props) {
    const { isAuthenticated, isLoading } = useAuth();
    
    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
        </div>
      );
    }
    
    if (!isAuthenticated) {
      // Redirect to login or show login component
      return <div>Please log in to access this page.</div>;
    }
    
    return <Component {...props} />;
  };
}
