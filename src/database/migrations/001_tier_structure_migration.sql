-- PIKAR AI Tier Structure Migration
-- Migrates from old tier structure to blueprint-compliant tiers
-- Removes FREE tier and implements 7-day trials

-- 1. Add new columns for trial management
ALTER TABLE user_tiers ADD COLUMN IF NOT EXISTS trial_start_date TIMESTAMP;
ALTER TABLE user_tiers ADD COLUMN IF NOT EXISTS trial_end_date TIMESTAMP;
ALTER TABLE user_tiers ADD COLUMN IF NOT EXISTS trial_status VARCHAR(20) DEFAULT 'active';
ALTER TABLE user_tiers ADD COLUMN IF NOT EXISTS billing_status VARCHAR(20) DEFAULT 'trial';

-- 2. Update existing tier IDs to match blueprint
UPDATE user_tiers SET tier_id = 'SOLOPRENEUR' WHERE tier_id = 'FREE' OR tier_id = 'free';
UPDATE user_tiers SET tier_id = 'STARTUP' WHERE tier_id = 'PRO' OR tier_id = 'pro';
UPDATE user_tiers SET tier_id = 'SME' WHERE tier_id = 'sme';
UPDATE user_tiers SET tier_id = 'ENTERPRISE' WHERE tier_id = 'ENTERPRISE' OR tier_id = 'enterprise';

-- 3. Set trial dates for existing users (7-day trial from now)
UPDATE user_tiers 
SET 
  trial_start_date = NOW(),
  trial_end_date = NOW() + INTERVAL '7 days',
  trial_status = 'active',
  billing_status = 'trial'
WHERE trial_start_date IS NULL;

-- 4. Create tier definitions table
CREATE TABLE IF NOT EXISTS tier_definitions (
  id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  price_monthly INTEGER, -- in cents, NULL for contact sales
  price_yearly INTEGER,  -- in cents, NULL for contact sales
  trial_days INTEGER DEFAULT 7,
  features JSONB NOT NULL,
  limits JSONB NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 5. Insert blueprint-compliant tier definitions
INSERT INTO tier_definitions (id, name, price_monthly, price_yearly, features, limits) VALUES
('SOLOPRENEUR', 'Solopreneur', 9900, 99000, 
  '{"agentTypes": ["strategic_planning", "customer_support", "content_creation", "sales_intelligence"], "maxAgentExecutions": 500, "maxTeamMembers": 1, "maxProjects": 10, "maxFileUploads": 50, "maxStorageGB": 5, "supportLevel": "email", "analyticsRetentionDays": 60, "customIntegrations": true, "whiteLabel": false, "apiAccess": false, "advancedAnalytics": true, "prioritySupport": false, "customAgents": false, "abTesting": false, "marketingAutomation": true, "socialScheduling": true, "workflowTemplates": true}',
  '{"dailyExecutions": 25, "monthlyExecutions": 500, "concurrentExecutions": 2, "fileUploadSizeMB": 25, "apiCallsPerDay": 500, "workflowsPerMonth": 10}'
),
('STARTUP', 'Startup', 29700, 297000,
  '{"agentTypes": "all", "maxAgentExecutions": 2000, "maxTeamMembers": 5, "maxProjects": 50, "maxFileUploads": 200, "maxStorageGB": 25, "supportLevel": "priority", "analyticsRetentionDays": 120, "customIntegrations": true, "whiteLabel": false, "apiAccess": true, "advancedAnalytics": true, "prioritySupport": true, "customAgents": false, "abTesting": true, "marketingAutomation": true, "socialScheduling": true, "workflowTemplates": true, "teamCollaboration": true, "advancedReporting": true}',
  '{"dailyExecutions": 100, "monthlyExecutions": 2000, "concurrentExecutions": 5, "fileUploadSizeMB": 100, "apiCallsPerDay": 2000, "workflowsPerMonth": 50}'
),
('SME', 'SME', 59700, 597000,
  '{"agentTypes": "all", "maxAgentExecutions": 5000, "maxTeamMembers": 15, "maxProjects": "unlimited", "maxFileUploads": 500, "maxStorageGB": 100, "supportLevel": "priority", "analyticsRetentionDays": 180, "customIntegrations": true, "whiteLabel": true, "apiAccess": true, "advancedAnalytics": true, "prioritySupport": true, "customAgents": true, "abTesting": true, "marketingAutomation": true, "socialScheduling": true, "workflowTemplates": true, "teamCollaboration": true, "advancedReporting": true, "customReports": true, "bulkOperations": true}',
  '{"dailyExecutions": 250, "monthlyExecutions": 5000, "concurrentExecutions": 10, "fileUploadSizeMB": 250, "apiCallsPerDay": 5000, "workflowsPerMonth": "unlimited"}'
),
('ENTERPRISE', 'Enterprise', NULL, NULL,
  '{"agentTypes": "all", "maxAgentExecutions": "unlimited", "maxTeamMembers": "unlimited", "maxProjects": "unlimited", "maxFileUploads": "unlimited", "maxStorageGB": "unlimited", "supportLevel": "dedicated", "analyticsRetentionDays": 365, "customIntegrations": true, "whiteLabel": true, "apiAccess": true, "advancedAnalytics": true, "prioritySupport": true, "customAgents": true, "abTesting": true, "marketingAutomation": true, "socialScheduling": true, "workflowTemplates": true, "teamCollaboration": true, "advancedReporting": true, "customReports": true, "bulkOperations": true, "customSLA": true, "dedicatedManager": true, "onPremiseDeployment": true, "ssoIntegration": true, "advancedSecurity": true, "auditLogs": true, "dataExport": true}',
  '{"dailyExecutions": "unlimited", "monthlyExecutions": "unlimited", "concurrentExecutions": "unlimited", "fileUploadSizeMB": "unlimited", "apiCallsPerDay": "unlimited", "workflowsPerMonth": "unlimited"}'
)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  price_monthly = EXCLUDED.price_monthly,
  price_yearly = EXCLUDED.price_yearly,
  features = EXCLUDED.features,
  limits = EXCLUDED.limits,
  updated_at = NOW();

-- 6. Create usage tracking table
CREATE TABLE IF NOT EXISTS user_usage_tracking (
  user_id VARCHAR(255) PRIMARY KEY,
  monthly_executions INTEGER DEFAULT 0,
  daily_executions INTEGER DEFAULT 0,
  file_upload_size_mb DECIMAL(10,2) DEFAULT 0,
  workflows_this_month INTEGER DEFAULT 0,
  api_calls_today INTEGER DEFAULT 0,
  last_daily_reset TIMESTAMP DEFAULT NOW(),
  last_monthly_reset TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 7. Create trial notifications table
CREATE TABLE IF NOT EXISTS trial_notifications (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  notification_type VARCHAR(50) NOT NULL, -- 'trial_started', 'trial_warning', 'trial_expired'
  days_remaining INTEGER,
  sent_at TIMESTAMP DEFAULT NOW(),
  email_sent BOOLEAN DEFAULT false,
  in_app_shown BOOLEAN DEFAULT false,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 8. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_tiers_trial_end ON user_tiers(trial_end_date);
CREATE INDEX IF NOT EXISTS idx_user_tiers_status ON user_tiers(trial_status, billing_status);
CREATE INDEX IF NOT EXISTS idx_usage_tracking_user ON user_usage_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_trial_notifications_user ON trial_notifications(user_id, notification_type);

-- 9. Create function to check trial expiration
CREATE OR REPLACE FUNCTION check_trial_expiration()
RETURNS TRIGGER AS $$
BEGIN
  -- If trial is ending in 3 days, 1 day, or has expired
  IF NEW.trial_end_date <= NOW() + INTERVAL '3 days' AND 
     OLD.trial_end_date > NOW() + INTERVAL '3 days' THEN
    INSERT INTO trial_notifications (user_id, notification_type, days_remaining)
    VALUES (NEW.user_id, 'trial_warning', 3);
  END IF;
  
  IF NEW.trial_end_date <= NOW() + INTERVAL '1 day' AND 
     OLD.trial_end_date > NOW() + INTERVAL '1 day' THEN
    INSERT INTO trial_notifications (user_id, notification_type, days_remaining)
    VALUES (NEW.user_id, 'trial_warning', 1);
  END IF;
  
  IF NEW.trial_end_date <= NOW() AND OLD.trial_end_date > NOW() THEN
    UPDATE user_tiers SET trial_status = 'expired' WHERE user_id = NEW.user_id;
    INSERT INTO trial_notifications (user_id, notification_type, days_remaining)
    VALUES (NEW.user_id, 'trial_expired', 0);
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 10. Create trigger for trial expiration
DROP TRIGGER IF EXISTS trial_expiration_trigger ON user_tiers;
CREATE TRIGGER trial_expiration_trigger
  AFTER UPDATE ON user_tiers
  FOR EACH ROW
  WHEN (OLD.trial_end_date IS DISTINCT FROM NEW.trial_end_date)
  EXECUTE FUNCTION check_trial_expiration();

-- 11. Create function to reset daily usage
CREATE OR REPLACE FUNCTION reset_daily_usage()
RETURNS void AS $$
BEGIN
  UPDATE user_usage_tracking 
  SET 
    daily_executions = 0,
    api_calls_today = 0,
    last_daily_reset = NOW()
  WHERE last_daily_reset < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

-- 12. Create function to reset monthly usage
CREATE OR REPLACE FUNCTION reset_monthly_usage()
RETURNS void AS $$
BEGIN
  UPDATE user_usage_tracking 
  SET 
    monthly_executions = 0,
    workflows_this_month = 0,
    file_upload_size_mb = 0,
    last_monthly_reset = NOW()
  WHERE last_monthly_reset < DATE_TRUNC('month', NOW());
END;
$$ LANGUAGE plpgsql;

-- 13. Insert initial usage tracking for existing users
INSERT INTO user_usage_tracking (user_id)
SELECT DISTINCT user_id FROM user_tiers
WHERE user_id NOT IN (SELECT user_id FROM user_usage_tracking);

-- 14. Update audit log to track tier changes
INSERT INTO audit_logs (action_type, success, action_details, risk_level, created_at)
VALUES (
  'tier_migration',
  true,
  '{"event": "tier_structure_migration", "old_tiers": ["FREE", "PRO", "ENTERPRISE"], "new_tiers": ["SOLOPRENEUR", "STARTUP", "SME", "ENTERPRISE"], "trial_days": 7}',
  'low',
  NOW()
);

-- 15. Create view for active trials
CREATE OR REPLACE VIEW active_trials AS
SELECT 
  ut.user_id,
  ut.tier_id,
  td.name as tier_name,
  ut.trial_start_date,
  ut.trial_end_date,
  EXTRACT(DAYS FROM (ut.trial_end_date - NOW())) as days_remaining,
  ut.trial_status,
  ut.billing_status
FROM user_tiers ut
JOIN tier_definitions td ON ut.tier_id = td.id
WHERE ut.trial_status = 'active' 
  AND ut.trial_end_date > NOW();

COMMIT;
