// Base44 removed: platform functions are not implemented in this build
const base44 = { functions: {} };
import { errorHandlingService } from '@/services/errorHandlingService';
import { auditService } from '@/services/auditService';
import { validateClientData } from '@/lib/validation/middleware';
import { z } from 'zod';

// Validation schemas for API functions
const MetaPostSchema = z.object({
  page_id: z.string().min(1, 'Page ID is required'),
  message: z.string().min(1, 'Message is required'),
  link: z.string().url().optional(),
  image_url: z.string().url().optional()
});

const TwitterPostSchema = z.object({
  text: z.string().min(1).max(280, 'Tweet must be 1-280 characters'),
  media_ids: z.array(z.string()).optional(),
  reply_to: z.string().optional()
});

const LinkedInPostSchema = z.object({
  text: z.string().min(1, 'Post text is required'),
  visibility: z.enum(['PUBLIC', 'CONNECTIONS']).default('PUBLIC'),
  media_url: z.string().url().optional()
});

// Enhanced Meta/Facebook Functions
export const metaOauthStart = createEnhancedFunction(
  base44.functions.metaOauthStart,
  'metaOauthStart',
  'meta'
);

export const metaOauthCallback = createEnhancedFunction(
  base44.functions.metaOauthCallback,
  'metaOauthCallback',
  'meta'
);

export const metaListPages = createEnhancedFunction(
  base44.functions.metaListPages,
  'metaListPages',
  'meta'
);

export const metaPostPage = createEnhancedFunction(
  base44.functions.metaPostPage,
  'metaPostPage',
  'meta',
  MetaPostSchema
);

export const metaValidateSecrets = createEnhancedFunction(
  base44.functions.metaValidateSecrets,
  'metaValidateSecrets',
  'meta'
);

// Enhanced function creator with validation, error handling, and audit logging
function createEnhancedFunction(baseFunction, functionName, platform, validationSchema = null) {
  return async function(params = {}) {
    const startTime = Date.now();

    if (!baseFunction) {
      const msg = `${functionName} for ${platform} is not configured in this build.`
      // Log and throw a clear error; callers can handle gracefully
      try { auditService?.logSystem?.configChange?.(null, 'api_function_unavailable', functionName, platform) } catch {}
      throw new Error(msg)
    }

    try {
      // Validate input parameters if schema provided
      if (validationSchema) {
        const validation = validationSchema.safeParse(params);
        if (!validation.success) {
          const error = new Error(`Invalid parameters for ${functionName}: ${validation.error.message}`);
          error.validationErrors = validation.error.errors;
          throw error;
        }
        params = validation.data;
      }

      // Log function call
      auditService.logAccess.dataAccess(null, 'api_function_call', functionName, {
        platform,
        params: Object.keys(params)
      });

      // Call the base function
      const result = await baseFunction(params);

      // Log successful execution
      const executionTime = Date.now() - startTime;
      auditService.logSystem.configChange(null, 'api_function_success', functionName, `${executionTime}ms`);

      return result;
    } catch (error) {
      // Enhanced error handling
      const executionTime = Date.now() - startTime;
      const enhancedError = errorHandlingService.handleApiError(error, {
        endpoint: functionName,
        platform,
        params,
        executionTime
      });

      // Log error
      auditService.logSystem.error(error, 'api_function_error', {
        functionName,
        platform,
        executionTime
      });

      throw error;
    }
  };
}

// Enhanced Twitter Functions
export const twitterValidateSecrets = createEnhancedFunction(
  base44.functions.twitterValidateSecrets,
  'twitterValidateSecrets',
  'twitter'
);

export const twitterOauthStart = createEnhancedFunction(
  base44.functions.twitterOauthStart,
  'twitterOauthStart',
  'twitter'
);

export const twitterOauthCallback = createEnhancedFunction(
  base44.functions.twitterOauthCallback,
  'twitterOauthCallback',
  'twitter'
);

export const twitterListAccount = createEnhancedFunction(
  base44.functions.twitterListAccount,
  'twitterListAccount',
  'twitter'
);

export const twitterPostTweet = createEnhancedFunction(
  base44.functions.twitterPostTweet,
  'twitterPostTweet',
  'twitter',
  TwitterPostSchema
);

// Enhanced LinkedIn Functions
export const linkedinValidateSecrets = createEnhancedFunction(
  base44.functions.linkedinValidateSecrets,
  'linkedinValidateSecrets',
  'linkedin'
);

export const linkedinOauthStart = createEnhancedFunction(
  base44.functions.linkedinOauthStart,
  'linkedinOauthStart',
  'linkedin'
);

export const linkedinOauthCallback = createEnhancedFunction(
  base44.functions.linkedinOauthCallback,
  'linkedinOauthCallback',
  'linkedin'
);

export const linkedinGetProfile = createEnhancedFunction(
  base44.functions.linkedinGetProfile,
  'linkedinGetProfile',
  'linkedin'
);

export const linkedinPostShare = createEnhancedFunction(
  base44.functions.linkedinPostShare,
  'linkedinPostShare',
  'linkedin',
  LinkedInPostSchema
);

// Additional validation schemas
const YouTubeUploadSchema = z.object({
  title: z.string().min(1).max(100, 'Title must be 1-100 characters'),
  description: z.string().max(5000, 'Description must be under 5000 characters').optional(),
  tags: z.array(z.string()).max(500, 'Maximum 500 tags').optional(),
  category_id: z.string().optional(),
  privacy_status: z.enum(['private', 'public', 'unlisted']).default('private'),
  video_file_url: z.string().url('Valid video file URL required')
});

const TikTokUploadSchema = z.object({
  title: z.string().min(1).max(150, 'Title must be 1-150 characters'),
  description: z.string().max(2200, 'Description must be under 2200 characters').optional(),
  hashtags: z.array(z.string()).optional(),
  video_file_url: z.string().url('Valid video file URL required'),
  cover_image_url: z.string().url().optional(),
  privacy_level: z.enum(['PUBLIC', 'FRIENDS', 'PRIVATE']).default('PUBLIC'),
  is_commercial: z.boolean().default(false),
  schedule_time: z.string().optional()
});

// Enhanced YouTube Functions
export const youtubeValidateSecrets = createEnhancedFunction(
  base44.functions.youtubeValidateSecrets,
  'youtubeValidateSecrets',
  'youtube'
);

export const youtubeOauthStart = createEnhancedFunction(
  base44.functions.youtubeOauthStart,
  'youtubeOauthStart',
  'youtube'
);

export const youtubeOauthCallback = createEnhancedFunction(
  base44.functions.youtubeOauthCallback,
  'youtubeOauthCallback',
  'youtube'
);

export const youtubeGetChannel = createEnhancedFunction(
  base44.functions.youtubeGetChannel,
  'youtubeGetChannel',
  'youtube'
);

// Enhanced Meta Advanced Functions
export const metaGetAdAccounts = createEnhancedFunction(
  base44.functions.metaGetAdAccounts,
  'metaGetAdAccounts',
  'meta'
);

export const metaCreateCampaign = createEnhancedFunction(
  base44.functions.metaCreateCampaign,
  'metaCreateCampaign',
  'meta',
  z.object({
    name: z.string().min(1, 'Campaign name is required'),
    objective: z.string().min(1, 'Campaign objective is required'),
    ad_account_id: z.string().min(1, 'Ad account ID is required'),
    budget: z.number().positive('Budget must be positive').optional(),
    status: z.enum(['ACTIVE', 'PAUSED']).default('PAUSED')
  })
);

export const metaPublishInstagram = createEnhancedFunction(
  base44.functions.metaPublishInstagram,
  'metaPublishInstagram',
  'meta',
  z.object({
    image_url: z.string().url('Valid image URL required'),
    caption: z.string().max(2200, 'Caption must be under 2200 characters').optional(),
    hashtags: z.array(z.string()).optional()
  })
);

export const metaGetInsights = createEnhancedFunction(
  base44.functions.metaGetInsights,
  'metaGetInsights',
  'meta',
  z.object({
    object_id: z.string().min(1, 'Object ID is required'),
    metric: z.array(z.string()).min(1, 'At least one metric is required'),
    date_preset: z.string().optional(),
    time_range: z.object({
      since: z.string(),
      until: z.string()
    }).optional()
  })
);

export const jobProcessor = createEnhancedFunction(
  base44.functions.jobProcessor,
  'jobProcessor',
  'system'
);

// Enhanced LinkedIn Advanced Functions
export const linkedinGetAdAccounts = createEnhancedFunction(
  base44.functions.linkedinGetAdAccounts,
  'linkedinGetAdAccounts',
  'linkedin'
);

export const linkedinGetCompanyPages = createEnhancedFunction(
  base44.functions.linkedinGetCompanyPages,
  'linkedinGetCompanyPages',
  'linkedin'
);

export const linkedinCreateCampaign = createEnhancedFunction(
  base44.functions.linkedinCreateCampaign,
  'linkedinCreateCampaign',
  'linkedin',
  z.object({
    name: z.string().min(1, 'Campaign name is required'),
    account_id: z.string().min(1, 'Account ID is required'),
    campaign_group_id: z.string().min(1, 'Campaign group ID is required'),
    objective_type: z.enum(['BRAND_AWARENESS', 'WEBSITE_VISITS', 'LEAD_GENERATION']),
    cost_type: z.enum(['CPC', 'CPM']).default('CPC'),
    status: z.enum(['ACTIVE', 'PAUSED', 'ARCHIVED']).default('PAUSED')
  })
);

export const linkedinCreateLeadGenForm = createEnhancedFunction(
  base44.functions.linkedinCreateLeadGenForm,
  'linkedinCreateLeadGenForm',
  'linkedin',
  z.object({
    name: z.string().min(1, 'Form name is required'),
    headline: z.string().min(1, 'Headline is required'),
    description: z.string().optional(),
    privacy_policy_url: z.string().url('Valid privacy policy URL required'),
    thank_you_message: z.string().optional()
  })
);

export const linkedinGetLeads = createEnhancedFunction(
  base44.functions.linkedinGetLeads,
  'linkedinGetLeads',
  'linkedin',
  z.object({
    form_id: z.string().min(1, 'Form ID is required'),
    start_date: z.string().optional(),
    end_date: z.string().optional()
  })
);

// Enhanced Twitter Advanced Functions
export const twitterGetAdAccounts = createEnhancedFunction(
  base44.functions.twitterGetAdAccounts,
  'twitterGetAdAccounts',
  'twitter'
);

export const twitterCreateCampaign = createEnhancedFunction(
  base44.functions.twitterCreateCampaign,
  'twitterCreateCampaign',
  'twitter',
  z.object({
    name: z.string().min(1, 'Campaign name is required'),
    funding_instrument_id: z.string().min(1, 'Funding instrument ID is required'),
    entity_status: z.enum(['ACTIVE', 'PAUSED']).default('PAUSED'),
    campaign_optimization: z.enum(['DEFAULT', 'WEBSITE_CLICKS', 'ENGAGEMENTS']).default('DEFAULT'),
    objective: z.enum(['AWARENESS', 'TWEET_ENGAGEMENTS', 'WEBSITE_CLICKS', 'FOLLOWERS']),
    start_time: z.string().optional(),
    end_time: z.string().optional()
  })
);

export const twitterCreateStreamRule = createEnhancedFunction(
  base44.functions.twitterCreateStreamRule,
  'twitterCreateStreamRule',
  'twitter',
  z.object({
    value: z.string().min(1, 'Rule value is required'),
    tag: z.string().optional()
  })
);

export const twitterBulkOperation = createEnhancedFunction(
  base44.functions.twitterBulkOperation,
  'twitterBulkOperation',
  'twitter',
  z.object({
    operation_type: z.enum(['CREATE', 'UPDATE', 'DELETE']),
    entity_type: z.enum(['CAMPAIGN', 'AD_GROUP', 'TWEET']),
    entities: z.array(z.object({})).min(1, 'At least one entity is required')
  })
);

// Enhanced YouTube Advanced Functions
export const youtubeUploadVideo = createEnhancedFunction(
  base44.functions.youtubeUploadVideo,
  'youtubeUploadVideo',
  'youtube',
  YouTubeUploadSchema
);

export const youtubeGetAnalytics = createEnhancedFunction(
  base44.functions.youtubeGetAnalytics,
  'youtubeGetAnalytics',
  'youtube',
  z.object({
    channel_id: z.string().optional(),
    video_id: z.string().optional(),
    metrics: z.array(z.string()).min(1, 'At least one metric is required'),
    start_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format'),
    end_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format'),
    dimensions: z.array(z.string()).optional()
  })
);

export const youtubeCreatePlaylist = createEnhancedFunction(
  base44.functions.youtubeCreatePlaylist,
  'youtubeCreatePlaylist',
  'youtube',
  z.object({
    title: z.string().min(1).max(150, 'Title must be 1-150 characters'),
    description: z.string().max(5000, 'Description must be under 5000 characters').optional(),
    privacy_status: z.enum(['private', 'public', 'unlisted']).default('private'),
    tags: z.array(z.string()).optional()
  })
);

export const youtubeManageSubscriptions = createEnhancedFunction(
  base44.functions.youtubeManageSubscriptions,
  'youtubeManageSubscriptions',
  'youtube',
  z.object({
    action: z.enum(['subscribe', 'unsubscribe']),
    channel_id: z.string().min(1, 'Channel ID is required')
  })
);

// Enhanced TikTok Functions
export const tiktokValidateSecrets = createEnhancedFunction(
  base44.functions.tiktokValidateSecrets,
  'tiktokValidateSecrets',
  'tiktok'
);

export const tiktokOauthStart = createEnhancedFunction(
  base44.functions.tiktokOauthStart,
  'tiktokOauthStart',
  'tiktok'
);

export const tiktokOauthCallback = createEnhancedFunction(
  base44.functions.tiktokOauthCallback,
  'tiktokOauthCallback',
  'tiktok'
);

export const tiktokGetAccount = createEnhancedFunction(
  base44.functions.tiktokGetAccount,
  'tiktokGetAccount',
  'tiktok'
);

export const tiktokUploadVideo = createEnhancedFunction(
  base44.functions.tiktokUploadVideo,
  'tiktokUploadVideo',
  'tiktok',
  TikTokUploadSchema
);

export const tiktokGetVideos = createEnhancedFunction(
  base44.functions.tiktokGetVideos,
  'tiktokGetVideos',
  'tiktok',
  z.object({
    max_count: z.number().min(1).max(100).default(20),
    cursor: z.string().optional(),
    start_date: z.string().optional(),
    end_date: z.string().optional()
  })
);

// Function availability checker
export const checkFunctionAvailability = async (functionName) => {
  try {
    const func = await import(`./functions.js`).then(module => module[functionName]);
    return {
      available: !!func,
      functionName,
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    return {
      available: false,
      functionName,
      error: error.message,
      timestamp: new Date().toISOString()
    };
  }
};

// Additional utility functions for API management
export const getAllPlatformFunctions = () => {
  return {
    meta: [
      'metaValidateSecrets', 'metaOauthStart', 'metaOauthCallback',
      'metaListPages', 'metaPostPage', 'metaGetAdAccounts',
      'metaCreateCampaign', 'metaPublishInstagram', 'metaGetInsights'
    ],
    twitter: [
      'twitterValidateSecrets', 'twitterOauthStart', 'twitterOauthCallback',
      'twitterListAccount', 'twitterPostTweet', 'twitterGetAdAccounts',
      'twitterCreateCampaign', 'twitterCreateStreamRule', 'twitterBulkOperation'
    ],
    linkedin: [
      'linkedinValidateSecrets', 'linkedinOauthStart', 'linkedinOauthCallback',
      'linkedinGetProfile', 'linkedinPostShare', 'linkedinGetAdAccounts',
      'linkedinGetCompanyPages', 'linkedinCreateCampaign', 'linkedinCreateLeadGenForm',
      'linkedinGetLeads'
    ],
    youtube: [
      'youtubeValidateSecrets', 'youtubeOauthStart', 'youtubeOauthCallback',
      'youtubeGetChannel', 'youtubeUploadVideo', 'youtubeGetAnalytics',
      'youtubeCreatePlaylist', 'youtubeManageSubscriptions'
    ],
    tiktok: [
      'tiktokValidateSecrets', 'tiktokOauthStart', 'tiktokOauthCallback',
      'tiktokGetAccount', 'tiktokUploadVideo', 'tiktokGetVideos'
    ]
  };
};

// Batch function availability checker
export const checkAllFunctionsAvailability = async () => {
  const platforms = getAllPlatformFunctions();
  const results = {};

  for (const [platform, functions] of Object.entries(platforms)) {
    results[platform] = {};

    for (const functionName of functions) {
      results[platform][functionName] = await checkFunctionAvailability(functionName);
    }
  }

  return results;
};

// Function execution with retry logic
export const executeWithRetry = async (functionName, params = {}, maxRetries = 3) => {
  let lastError;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const func = await import(`./functions.js`).then(module => module[functionName]);
      if (!func) {
        throw new Error(`Function ${functionName} not found`);
      }

      const result = await func(params);

      // Log successful execution after retry
      if (attempt > 1) {
        auditService.logSystem.configChange(null, 'function_retry_success', functionName, `attempt_${attempt}`);
      }

      return result;
    } catch (error) {
      lastError = error;

      // Log retry attempt
      auditService.logSystem.error(error, 'function_retry_attempt', {
        functionName,
        attempt,
        maxRetries
      });

      // Don't retry on validation errors
      if (error.validationErrors) {
        break;
      }

      // Wait before retry (exponential backoff)
      if (attempt < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
      }
    }
  }

  // All retries failed
  auditService.logSystem.error(lastError, 'function_retry_failed', {
    functionName,
    maxRetries
  });

  throw lastError;
};

// Platform-specific function groups
export const metaFunctions = {
  metaValidateSecrets,
  metaOauthStart,
  metaOauthCallback,
  metaListPages,
  metaPostPage,
  metaGetAdAccounts,
  metaCreateCampaign,
  metaPublishInstagram,
  metaGetInsights
};

export const twitterFunctions = {
  twitterValidateSecrets,
  twitterOauthStart,
  twitterOauthCallback,
  twitterListAccount,
  twitterPostTweet,
  twitterGetAdAccounts,
  twitterCreateCampaign,
  twitterCreateStreamRule,
  twitterBulkOperation
};

export const linkedinFunctions = {
  linkedinValidateSecrets,
  linkedinOauthStart,
  linkedinOauthCallback,
  linkedinGetProfile,
  linkedinPostShare,
  linkedinGetAdAccounts,
  linkedinGetCompanyPages,
  linkedinCreateCampaign,
  linkedinCreateLeadGenForm,
  linkedinGetLeads
};

export const youtubeFunctions = {
  youtubeValidateSecrets,
  youtubeOauthStart,
  youtubeOauthCallback,
  youtubeGetChannel,
  youtubeUploadVideo,
  youtubeGetAnalytics,
  youtubeCreatePlaylist,
  youtubeManageSubscriptions
};

export const tiktokFunctions = {
  tiktokValidateSecrets,
  tiktokOauthStart,
  tiktokOauthCallback,
  tiktokGetAccount,
  tiktokUploadVideo,
  tiktokGetVideos
};

// Export all functions grouped by platform
export const allPlatformFunctions = {
  meta: metaFunctions,
  twitter: twitterFunctions,
  linkedin: linkedinFunctions,
  youtube: youtubeFunctions,
  tiktok: tiktokFunctions
};

