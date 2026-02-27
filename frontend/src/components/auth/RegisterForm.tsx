'use client';
import { useState } from 'react';
import { signUp, signInWithGoogle } from '../../services/auth';

export default function RegisterForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await signUp(email, password);
  };

  const handleGoogleSignIn = async () => {
    await signInWithGoogle();
  };

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <input
          id="register-email"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="p-2 border rounded"
        />
        <input
          id="register-password"
          name="password"
          type="password"
          autoComplete="new-password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="p-2 border rounded"
        />
        <button type="submit" className="bg-green-500 text-white p-2 rounded">
          Sign Up
        </button>
      </form>
      <div className="text-center">OR</div>
      <button
        type="button"
        onClick={handleGoogleSignIn}
        className="bg-white border border-gray-300 text-gray-700 p-2 rounded hover:bg-gray-50"
      >
        Continue with Google
      </button>
    </div>
  );
}