# Specification: Frontend Polish & Features

## 1. Overview
This track focuses on completing the user-facing frontend features: distinct persona dashboards, a robust authentication flow (including password recovery), a "Dynamic Workflow Generator" interface, and final polish of the Landing Page and routing.

## 2. Goals
- **Complete Auth Flow:** Add Forgot/Reset Password pages and proper navigation links.
- **Persona-Specific Dashboards:** Replace generic shells with feature-rich dashboards for Solopreneur, Startup, SME, and Enterprise.
- **Dynamic Workflow Generator:** Implement a UI for "Text-to-Workflow" generation.
- **Routing Reliability:** Ensure secure and correct routing between all pages.

## 3. Scope

### 3.1 Authentication
- `src/app/auth/forgot-password`: Email request form.
- `src/app/auth/reset-password`: New password form.
- `src/app/settings`: Persona-aware settings page.

### 3.2 Dynamic Workflow Generator
- A new interface (`src/components/workflow/DynamicWorkflowGenerator.tsx`) where users describe a process, and it visualizes a generated workflow (mocked or connected to `ExecutiveAgent`).

### 3.3 Persona Dashboards
- **Solopreneur:** Focus on "My Agents", "Quick Tasks", "Revenue".
- **Startup:** Focus on "Team Velocity", "Product Roadmap", "Growth Metrics".
- **SME:** Focus on "Department Health", "Compliance", "Vendor Status".
- **Enterprise:** Focus on "Global Overview", "Security Audit", "Multi-Region Stats".

### 3.4 Landing Page & Routing
- Verify `ThreeBackground` component.
- Ensure all "Sign In" / "Get Started" links work.
- Validate Middleware protection.

## 4. Technical Constraints
- Next.js App Router.
- Tailwind CSS 4.
- Supabase Auth.

## 5. Success Criteria
- [ ] Users can reset their password.
- [ ] Each persona sees a unique, relevant dashboard.
- [ ] Users can use the Dynamic Workflow Generator UI.
- [ ] Landing page visuals render correctly.
- [ ] All navigation links are functional.
