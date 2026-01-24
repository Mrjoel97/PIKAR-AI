/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import LoginForm from '../../src/components/auth/LoginForm';
import RegisterForm from '../../src/components/auth/RegisterForm';
import * as authService from '../../src/services/auth';

// Mock the auth service
vi.mock('../../src/services/auth', () => ({
  signIn: vi.fn(),
  signUp: vi.fn(),
}));

afterEach(() => {
  cleanup();
});

describe('Auth Forms', () => {
  describe('LoginForm', () => {
    it('renders email and password inputs', () => {
      render(<LoginForm />);
      expect(screen.getByPlaceholderText(/email/i)).toBeDefined();
      expect(screen.getByPlaceholderText(/password/i)).toBeDefined();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeDefined();
    });

    it('calls signIn on submit', async () => {
      render(<LoginForm />);
      
      fireEvent.change(screen.getByPlaceholderText(/email/i), { target: { value: 'test@example.com' } });
      fireEvent.change(screen.getByPlaceholderText(/password/i), { target: { value: 'password' } });
      
      fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
      
      expect(authService.signIn).toHaveBeenCalledWith('test@example.com', 'password');
    });
  });

  describe('RegisterForm', () => {
    it('renders email and password inputs', () => {
      render(<RegisterForm />);
      expect(screen.getByPlaceholderText(/email/i)).toBeDefined();
      expect(screen.getByPlaceholderText(/password/i)).toBeDefined();
      expect(screen.getByRole('button', { name: /sign up/i })).toBeDefined();
    });

    it('calls signUp on submit', async () => {
      render(<RegisterForm />);
      
      fireEvent.change(screen.getByPlaceholderText(/email/i), { target: { value: 'new@example.com' } });
      fireEvent.change(screen.getByPlaceholderText(/password/i), { target: { value: 'newpass' } });
      
      fireEvent.click(screen.getByRole('button', { name: /sign up/i }));
      
      expect(authService.signUp).toHaveBeenCalledWith('new@example.com', 'newpass');
    });
  });
});
