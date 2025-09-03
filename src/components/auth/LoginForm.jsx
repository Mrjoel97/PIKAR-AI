import React, { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useValidation } from '@/hooks/useValidation';
import { LoginSchema } from '@/lib/validation/schemas';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Loader2, Eye, EyeOff, Mail, Lock } from 'lucide-react';
import { toast } from 'sonner';
import ErrorBoundary from '@/components/ErrorBoundary';

function LoginForm() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const [showPassword, setShowPassword] = useState(false);

  const {
    data: formData,
    errors,
    isValid,
    updateField,
    handleBlur,
    validateAll,
    getFieldError,
    hasFieldError
  } = useValidation(LoginSchema, {
    email: '',
    password: '',
    rememberMe: false
  });

  // Redirect if already authenticated
  if (isAuthenticated) {
    const from = location.state?.from?.pathname || '/dashboard';
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const validation = await validateAll();
    if (!validation.success) {
      toast.error('Please fix the validation errors');
      return;
    }

    const result = await login(validation.data);
    if (result.success) {
      const from = location.state?.from?.pathname || '/dashboard';
      window.location.href = from; // Force navigation to ensure proper state reset
    }
  };

  const handleDemoLogin = async () => {
    const demoCredentials = {
      email: 'demo@pikar-ai.com',
      password: 'password123',
      rememberMe: false
    };

    const result = await login(demoCredentials);
    if (result.success) {
      window.location.href = '/dashboard';
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-blue-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-emerald-600 to-emerald-900 rounded-xl flex items-center justify-center">
            <span className="text-2xl font-bold text-white">P</span>
          </div>
          <div>
            <CardTitle className="text-2xl font-bold text-gray-900">
              Welcome back
            </CardTitle>
            <CardDescription className="text-base mt-2">
              Sign in to your PIKAR AI account
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div className="space-y-2">
              <Label htmlFor="email">Email address</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => updateField('email', e.target.value)}
                  onBlur={() => handleBlur('email')}
                  placeholder="Enter your email"
                  className={`pl-10 ${hasFieldError('email') ? 'border-red-500' : ''}`}
                  disabled={isLoading}
                  autoComplete="email"
                  required
                />
              </div>
              {hasFieldError('email') && (
                <p className="text-sm text-red-600">{getFieldError('email')}</p>
              )}
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => updateField('password', e.target.value)}
                  onBlur={() => handleBlur('password')}
                  placeholder="Enter your password"
                  className={`pl-10 pr-10 ${hasFieldError('password') ? 'border-red-500' : ''}`}
                  disabled={isLoading}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  disabled={isLoading}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {hasFieldError('password') && (
                <p className="text-sm text-red-600">{getFieldError('password')}</p>
              )}
            </div>

            {/* Remember Me */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="rememberMe"
                checked={formData.rememberMe}
                onCheckedChange={(checked) => updateField('rememberMe', checked)}
                disabled={isLoading}
              />
              <Label htmlFor="rememberMe" className="text-sm text-gray-600">
                Remember me for 30 days
              </Label>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              className="w-full"
              disabled={isLoading || !isValid}
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </Button>

            {/* Demo Login */}
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={handleDemoLogin}
              disabled={isLoading}
            >
              Try Demo Account
            </Button>
          </form>

          {/* Additional Links */}
          <div className="mt-6 space-y-4">
            <div className="text-center">
              <a
                href="/forgot-password"
                className="text-sm text-emerald-600 hover:text-emerald-700 hover:underline"
              >
                Forgot your password?
              </a>
            </div>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">Don't have an account?</span>
              </div>
            </div>

            <Button
              variant="outline"
              className="w-full"
              onClick={() => window.location.href = '/register'}
              disabled={isLoading}
            >
              Create new account
            </Button>
          </div>

          {/* Demo Credentials Info */}
          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <h4 className="text-sm font-medium text-blue-900 mb-2">Demo Credentials</h4>
            <div className="text-xs text-blue-800 space-y-1">
              <p><strong>Email:</strong> demo@pikar-ai.com</p>
              <p><strong>Password:</strong> password123</p>
              <p><strong>Admin:</strong> admin@pikar-ai.com / password123</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Wrap with ErrorBoundary
export default function LoginFormWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <LoginForm />
    </ErrorBoundary>
  );
}
