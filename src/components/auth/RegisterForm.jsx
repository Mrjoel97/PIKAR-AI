import React, { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader2, Mail, Lock, User } from 'lucide-react'
import ErrorBoundary from '@/components/ErrorBoundary'

export default function RegisterFormWithBoundary() {
  return (
    <ErrorBoundary>
      <RegisterForm />
    </ErrorBoundary>
  )
}

function RegisterForm() {
  const { register, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '', full_name: '' })
  const [showPassword, setShowPassword] = useState(false)

  if (isAuthenticated) {
    const from = location.state?.from?.pathname || '/dashboard'
    return <Navigate to={from} replace />
  }

  const onChange = (e) => {
    const { name, value } = e.target
    setForm((f) => ({ ...f, [name]: value }))
  }

  const onSubmit = async (e) => {
    e.preventDefault()
    if (!form.email || !form.password) return
    await register({ email: form.email, password: form.password, full_name: form.full_name })
    // Supabase may require email verification; the AuthProvider will reflect state
    window.location.href = '/dashboard'
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-blue-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-emerald-600 to-emerald-900 rounded-xl flex items-center justify-center">
            <span className="text-2xl font-bold text-white">P</span>
          </div>
          <div>
            <CardTitle className="text-2xl font-bold text-gray-900">Create your account</CardTitle>
            <CardDescription className="text-base mt-1">Sign up for PIKAR AI</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="full_name">Full name (optional)</Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input id="full_name" name="full_name" value={form.full_name} onChange={onChange} placeholder="Your name" className="pl-10" disabled={isLoading} />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email address</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input id="email" name="email" type="email" value={form.email} onChange={onChange} placeholder="you@example.com" className="pl-10" autoComplete="email" required disabled={isLoading} />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input id="password" name="password" type={showPassword ? 'text' : 'password'} value={form.password} onChange={onChange} placeholder="••••••••" className="pl-10 pr-10" autoComplete="new-password" required disabled={isLoading} />
                <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600" onClick={() => setShowPassword((s) => !s)}>
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>
            <Button type="submit" className="w-full" disabled={isLoading || !form.email || !form.password}>
              {isLoading ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" />Creating account...</>) : 'Create account'}
            </Button>
            <Button type="button" variant="outline" className="w-full" onClick={() => (window.location.href = '/login')} disabled={isLoading}>
              Already have an account? Sign in
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

