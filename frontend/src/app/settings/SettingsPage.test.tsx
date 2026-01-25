// @vitest-environment jsdom
import { render, screen, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach } from 'vitest'
import SettingsPage from './page'

describe('SettingsPage', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders settings form', () => {
    render(<SettingsPage />)
    
    expect(screen.getByText('User Settings')).toBeTruthy()
    expect(screen.getByText('Profile Information')).toBeTruthy()
    expect(screen.getByLabelText('Full Name')).toBeTruthy()
    expect(screen.getByLabelText('Email Address')).toBeTruthy()
  })

  it('renders save button', () => {
    render(<SettingsPage />)
    
    expect(screen.getByText('Save Changes')).toBeTruthy()
  })
})
