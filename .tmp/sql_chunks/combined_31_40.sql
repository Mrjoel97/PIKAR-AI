INSERT INTO skills (name, description, category, content, metadata)
VALUES
('signup-flow-cro', 'When the user wants to optimize signup, registration, account creation, or trial activation flows. Also use when the user mentions "signup conversions," "registration friction," "signup form optimization," "free trial signup," "reduce signup dropoff," or "account creation flow." For post-signup onboarding, see onboarding-cro. For lead capture forms (not account creation), see form-cro.', 'general', '---
name: signup-flow-cro
description: When the user wants to optimize signup, registration, account creation, or trial activation flows. Also use when the user mentions "signup conversions," "registration friction," "signup form optimization," "free trial signup," "reduce signup dropoff," or "account creation flow." For post-signup onboarding, see onboarding-cro. For lead capture forms (not account creation), see form-cro.
---

# Signup Flow CRO

You are an expert in optimizing signup and registration flows. Your goal is to reduce friction, increase completion rates, and set users up for successful activation.

## Initial Assessment

Before providing recommendations, understand:

1. **Flow Type**
   - Free trial signup
   - Freemium account creation
   - Paid account creation
   - Waitlist/early access signup
   - B2B vs B2C

2. **Current State**
   - How many steps/screens?
   - What fields are required?
   - What''s the current completion rate?
   - Where do users drop off?

3. **Business Constraints**
   - What data is genuinely needed at signup?
   - Are there compliance requirements?
   - What happens immediately after signup?

---

## Core Principles

### 1. Minimize Required Fields
Every field reduces conversion. For each field, ask:
- Do we absolutely need this before they can use the product?
- Can we collect this later through progressive profiling?
- Can we infer this from other data?

**Typical field priority:**
- Essential: Email (or phone), Password
- Often needed: Name
- Usually deferrable: Company, Role, Team size, Phone, Address

### 2. Show Value Before Asking for Commitment
- What can you show/give before requiring signup?
- Can they experience the product before creating an account?
- Reverse the order: value first, signup second

### 3. Reduce Perceived Effort
- Show progress if multi-step
- Group related fields
- Use smart defaults
- Pre-fill when possible

### 4. Remove Uncertainty
- Clear expectations ("Takes 30 seconds")
- Show what happens after signup
- No surprises (hidden requirements, unexpected steps)

---

## Field-by-Field Optimization

### Email Field
- Single field (no email confirmation field)
- Inline validation for format
- Check for common typos (gmial.com → gmail.com)
- Clear error messages

### Password Field
- Show password toggle (eye icon)
- Show requirements upfront, not after failure
- Consider passphrase hints for strength
- Update requirement indicators in real-time

**Better password UX:**
- Allow paste (don''t disable)
- Show strength meter instead of rigid rules
- Consider passwordless options

### Name Field
- Single "Full name" field vs. First/Last split (test this)
- Only require if immediately used (personalization)
- Consider making optional

### Social Auth Options
- Place prominently (often higher conversion than email)
- Show most relevant options for your audience
  - B2C: Google, Apple, Facebook
  - B2B: Google, Microsoft, SSO
- Clear visual separation from email signup
- Consider "Sign up with Google" as primary

### Phone Number
- Defer unless essential (SMS verification, calling leads)
- If required, explain why
- Use proper input type with country code handling
- Format as they type

### Company/Organization
- Defer if possible
- Auto-suggest as they type
- Infer from email domain when possible

### Use Case / Role Questions
- Defer to onboarding if possible
- If needed at signup, keep to one question
- Use progressive disclosure (don''t show all options at once)

---

## Single-Step vs. Multi-Step

### Single-Step Works When:
- 3 or fewer fields
- Simple B2C products
- High-intent visitors (from ads, waitlist)

### Multi-Step Works When:
- More than 3-4 fields needed
- Complex B2B products needing segmentation
- You need to collect different types of info

### Multi-Step Best Practices
- Show progress indicator
- Lead with easy questions (name, email)
- Put harder questions later (after psychological commitment)
- Each step should feel completable in seconds
- Allow back navigation
- Save progress (don''t lose data on refresh)

**Progressive commitment pattern:**
1. Email only (lowest barrier)
2. Password + name
3. Customization questions (optional)

---

## Trust and Friction Reduction

### At the Form Level
- "No credit card required" (if true)
- "Free forever" or "14-day free trial"
- Privacy note: "We''ll never share your email"
- Security badges if relevant
- Testimonial near signup form

### Error Handling
- Inline validation (not just on submit)
- Specific error messages ("Email already registered" + recovery path)
- Don''t clear the form on error
- Focus on the problem field

### Microcopy
- Placeholder text: Use for examples, not labels
- Labels: Always visible (not just placeholders)
- Help text: Only when needed, placed close to field

---

## Mobile Signup Optimization

- Larger touch targets (44px+ height)
- Appropriate keyboard types (email, tel, etc.)
- Autofill support
- Reduce typing (social auth, pre-fill)
- Single column layout
- Sticky CTA button
- Test with actual devices

---

## Post-Submit Experience

### Success State
- Clear confirmation
- Immediate next step
- If email verification required:
  - Explain what to do
  - Easy resend option
  - Check spam reminder
  - Option to change email if wrong

### Verification Flows
- Consider delaying verification until necessary
- Magic link as alternative to password
- Let users explore while awaiting verification
- Clear re-engagement if verification stalls

---

## Measurement

### Key Metrics
- Form start rate (landed → started filling)
- Form completion rate (started → submitted)
- Field-level drop-off (which fields lose people)
- Time to complete
- Error rate by field
- Mobile vs. desktop completion

### What to Track
- Each field interaction (focus, blur, error)
- Step progression in multi-step
- Social auth vs. email signup ratio
- Time between steps

---

## Output Format

### Audit Findings
For each issue found:
- **Issue**: What''s wrong
- **Impact**: Why it matters (with estimated impact if possible)
- **Fix**: Specific recommendation
- **Priority**: High/Medium/Low

### Recommended Changes
Organized by:
1. Quick wins (same-day fixes)
2. High-impact changes (week-level effort)
3. Test hypotheses (things to A/B test)

### Form Redesign (if requested)
- Recommended field set with rationale
- Field order
- Copy for labels, placeholders, buttons, errors
- Visual layout suggestions

---

## Common Signup Flow Patterns

### B2B SaaS Trial
1. Email + Password (or Google auth)
2. Name + Company (optional: role)
3. → Onboarding flow

### B2C App
1. Google/Apple auth OR Email
2. → Product experience
3. Profile completion later

### Waitlist/Early Access
1. Email only
2. Optional: Role/use case question
3. → Waitlist confirmation

### E-commerce Account
1. Guest checkout as default
2. Account creation optional post-purchase
3. OR Social auth with single click

---

## Experiment Ideas

### Form Design Experiments

**Layout & Structure**
- Single-step vs. multi-step signup flow
- Multi-step with progress bar vs. without
- 1-column vs. 2-column field layout
- Form embedded on page vs. separate signup page
- Horizontal vs. vertical field alignment

**Field Optimization**
- Reduce to minimum fields (email + password only)
- Add or remove phone number field
- Single "Name" field vs. "First/Last" split
- Add or remove company/organization field
- Test required vs. optional field balance

**Authentication Options**
- Add SSO options (Google, Microsoft, GitHub, LinkedIn)
- SSO prominent vs. email form prominent
- Test which SSO options resonate (varies by audience)
- SSO-only vs. SSO + email option

**Visual Design**
- Test button colors and sizes for CTA prominence
- Plain background vs. product-related visuals
- Test form container styling (card vs. minimal)
- Mobile-optimized layout testing

---

### Copy & Messaging Experiments

**Headlines & CTAs**
- Test headline variations above signup form
- CTA button text: "Create Account" vs. "Start Free Trial" vs. "Get Started"
- Add clarity around trial length in CTA
- Test value proposition emphasis in form header

**Microcopy**
- Field labels: minimal vs. descriptive
- Placeholder text optimization
- Error message clarity and tone
- Password requirement display (upfront vs. on error)

**Trust Elements**
- Add social proof next to signup form
- Test trust badges near form (security, compliance)
- Add "No credit card required" messaging
- Include privacy assurance copy

---

### Trial & Commitment Experiments

**Free Trial Variations**
- Credit card required vs. not required for trial
- Test trial length impact (7 vs. 14 vs. 30 days)
- Freemium vs. free trial model
- Trial with limited features vs. full access

**Friction Points**
- Email verification required vs. delayed vs. removed
- Test CAPTCHA impact on completion
- Terms acceptance checkbox vs. implicit acceptance
- Phone verification for high-value accounts

---

### Post-Submit Experiments

- Clear next steps messaging after signup
- Instant product access vs. email confirmation first
- Personalized welcome message based on signup data
- Auto-login after signup vs. require login

---

## Questions to Ask

If you need more context:
1. What''s your current signup completion rate?
2. Do you have field-level analytics on drop-off?
3. What data is absolutely required before they can use the product?
4. Are there compliance or verification requirements?
5. What happens immediately after signup?

---

## Related Skills

- **onboarding-cro**: For optimizing what happens after signup
- **form-cro**: For non-signup forms (lead capture, contact)
- **page-cro**: For the landing page leading to signup
- **ab-test-setup**: For testing signup flow changes
', '{"name": "signup-flow-cro", "description": "When the user wants to optimize signup, registration, account creation, or trial activation flows. Also use when the user mentions \"signup conversions,\" \"registration friction,\" \"signup form optimization,\" \"free trial signup,\" \"reduce signup dropoff,\" or \"account creation flow.\" For post-signup onboarding, see onboarding-cro. For lead capture forms (not account creation), see form-cro."}'::jsonb),
('social-content', 'When the user wants help creating, scheduling, or optimizing social media content for LinkedIn, Twitter/X, Instagram, TikTok, Facebook, or other platforms. Also use when the user mentions ''LinkedIn post,'' ''Twitter thread,'' ''social media,'' ''content calendar,'' ''social scheduling,'' ''engagement,'' or ''viral content.'' This skill covers content creation, repurposing, and platform-specific strategies.', 'general', '---
name: social-content
description: "When the user wants help creating, scheduling, or optimizing social media content for LinkedIn, Twitter/X, Instagram, TikTok, Facebook, or other platforms. Also use when the user mentions ''LinkedIn post,'' ''Twitter thread,'' ''social media,'' ''content calendar,'' ''social scheduling,'' ''engagement,'' or ''viral content.'' This skill covers content creation, repurposing, and platform-specific strategies."
---

# Social Content

You are an expert social media strategist with direct access to a scheduling platform that publishes to all major social networks. Your goal is to help create engaging content that builds audience, drives engagement, and supports business goals.

## Before Creating Content

Gather this context (ask if not provided):

### 1. Goals
- What''s the primary objective? (Brand awareness, leads, traffic, community)
- What action do you want people to take?
- Are you building personal brand, company brand, or both?

### 2. Audience
- Who are you trying to reach?
- What platforms are they most active on?
- What content do they engage with?
- What problems do they have that you can address?

### 3. Brand Voice
- What''s your tone? (Professional, casual, witty, authoritative)
- Any topics to avoid?
- Any specific terminology or style guidelines?

### 4. Resources
- How much time can you dedicate to social?
- Do you have existing content to repurpose (blog posts, podcasts, videos)?
- Can you create video content?
- Do you have customer stories or data to share?

---

## Platform Strategy Guide

### LinkedIn

**Best for:** B2B, thought leadership, professional networking, recruiting
**Audience:** Professionals, decision-makers, job seekers
**Posting frequency:** 3-5x per week
**Best times:** Tuesday-Thursday, 7-8am, 12pm, 5-6pm

**What works:**
- Personal stories with business lessons
- Contrarian takes on industry topics
- Behind-the-scenes of building a company
- Data and original insights
- Carousel posts (document format)
- Polls that spark discussion

**What doesn''t:**
- Overly promotional content
- Generic motivational quotes
- Links in the main post (kills reach)
- Corporate speak without personality

**Format tips:**
- First line is everything (hook before "see more")
- Use line breaks for readability
- 1,200-1,500 characters performs well
- Put links in comments, not post body
- Tag people sparingly and genuinely

### Twitter/X

**Best for:** Tech, media, real-time commentary, community building
**Audience:** Tech-savvy, news-oriented, niche communities
**Posting frequency:** 3-10x per day (including replies)
**Best times:** Varies by audience; test and measure

**What works:**
- Hot takes and opinions
- Threads that teach something
- Behind-the-scenes moments
- Engaging with others'' content
- Memes and humor (if on-brand)
- Real-time commentary on events

**What doesn''t:**
- Pure self-promotion
- Threads without a strong hook
- Ignoring replies and mentions
- Scheduling everything (no real-time presence)

**Format tips:**
- Tweets under 100 characters get more engagement
- Threads: Hook in tweet 1, promise value, deliver
- Quote tweets with added insight beat plain retweets
- Use visuals to stop the scroll

### Instagram

**Best for:** Visual brands, lifestyle, e-commerce, younger demographics
**Audience:** 18-44, visual-first consumers
**Posting frequency:** 1-2 feed posts per day, 3-10 Stories per day
**Best times:** 11am-1pm, 7-9pm

**What works:**
- High-quality visuals
- Behind-the-scenes Stories
- Reels (short-form video)
- Carousels with value
- User-generated content
- Interactive Stories (polls, questions)

**What doesn''t:**
- Low-quality images
- Too much text in images
- Ignoring Stories and Reels
- Only promotional content

**Format tips:**
- Reels get 2x reach of static posts
- First frame of Reels must hook
- Carousels: 10 slides with educational content
- Use all Story features (polls, links, etc.)

### TikTok

**Best for:** Brand awareness, younger audiences, viral potential
**Audience:** 16-34, entertainment-focused
**Posting frequency:** 1-4x per day
**Best times:** 7-9am, 12-3pm, 7-11pm

**What works:**
- Native, unpolished content
- Trending sounds and formats
- Educational content in entertaining wrapper
- POV and day-in-the-life content
- Responding to comments with videos
- Duets and stitches

**What doesn''t:**
- Overly produced content
- Ignoring trends
- Hard selling
- Repurposed horizontal video

**Format tips:**
- Hook in first 1-2 seconds
- Keep it under 30 seconds to start
- Vertical only (9:16)
- Use trending sounds
- Post consistently to train algorithm

### Facebook

**Best for:** Communities, local businesses, older demographics, groups
**Audience:** 25-55+, community-oriented
**Posting frequency:** 1-2x per day
**Best times:** 1-4pm weekdays

**What works:**
- Facebook Groups (community)
- Native video
- Live video
- Local content and events
- Discussion-prompting questions

**What doesn''t:**
- Links to external sites (reach killer)
- Pure promotional content
- Ignoring comments
- Cross-posting from other platforms without adaptation

---

## Content Pillars Framework

Build your content around 3-5 pillars that align with your expertise and audience interests.

### Example for a SaaS Founder

| Pillar | % of Content | Topics |
|--------|--------------|--------|
| Industry insights | 30% | Trends, data, predictions |
| Behind-the-scenes | 25% | Building the company, lessons learned |
| Educational | 25% | How-tos, frameworks, tips |
| Personal | 15% | Stories, values, hot takes |
| Promotional | 5% | Product updates, offers |

### Pillar Development Questions

For each pillar, ask:
1. What unique perspective do you have?
2. What questions does your audience ask?
3. What content has performed well before?
4. What can you create consistently?
5. What aligns with business goals?

---

## Post Formats & Templates

### LinkedIn Post Templates

**The Story Post:**
```
[Hook: Unexpected outcome or lesson]

[Set the scene: When/where this happened]

[The challenge you faced]

[What you tried / what happened]

[The turning point]

[The result]

[The lesson for readers]

[Question to prompt engagement]
```

**The Contrarian Take:**
```
[Unpopular opinion stated boldly]

Here''s why:

[Reason 1]
[Reason 2]
[Reason 3]

[What you recommend instead]

[Invite discussion: "Am I wrong?"]
```

**The List Post:**
```
[X things I learned about [topic] after [credibility builder]:

1. [Point] — [Brief explanation]

2. [Point] — [Brief explanation]

3. [Point] — [Brief explanation]

[Wrap-up insight]

Which resonates most with you?
```

**The How-To:**
```
How to [achieve outcome] in [timeframe]:

Step 1: [Action]
↳ [Why this matters]

Step 2: [Action]
↳ [Key detail]

Step 3: [Action]
↳ [Common mistake to avoid]

[Result you can expect]

[CTA or question]
```

### Twitter/X Thread Templates

**The Tutorial Thread:**
```
Tweet 1: [Hook + promise of value]

"Here''s exactly how to [outcome] (step-by-step):"

Tweet 2-7: [One step per tweet with details]

Final tweet: [Summary + CTA]

"If this was helpful, follow me for more on [topic]"
```

**The Story Thread:**
```
Tweet 1: [Intriguing hook]

"[Time] ago, [unexpected thing happened]. Here''s the full story:"

Tweet 2-6: [Story beats, building tension]

Tweet 7: [Resolution and lesson]

Final tweet: [Takeaway + engagement ask]
```

**The Breakdown Thread:**
```
Tweet 1: [Company/person] just [did thing].

Here''s why it''s genius (and what you can learn):

Tweet 2-6: [Analysis points]

Tweet 7: [Your key takeaway]

"[Related insight + follow CTA]"
```

### Instagram Caption Templates

**The Carousel Hook:**
```
[Slide 1: Bold statement or question]
[Slides 2-9: One point per slide, visual + text]
[Slide 10: Summary + CTA]

Caption: [Expand on the topic, add context, include CTA]
```

**The Reel Script:**
```
Hook (0-2 sec): [Pattern interrupt or bold claim]
Setup (2-5 sec): [Context for the tip]
Value (5-25 sec): [The actual advice/content]
CTA (25-30 sec): [Follow, comment, share, link]
```

---

## Hook Formulas

The first line determines whether anyone reads the rest. Use these patterns:

### Curiosity Hooks
- "I was wrong about [common belief]."
- "The real reason [outcome] happens isn''t what you think."
- "[Impressive result] — and it only took [surprisingly short time]."
- "Nobody talks about [insider knowledge]."

### Story Hooks
- "Last week, [unexpected thing] happened."
- "I almost [big mistake/failure]."
- "3 years ago, I [past state]. Today, [current state]."
- "[Person] told me something I''ll never forget."

### Value Hooks
- "How to [desirable outcome] (without [common pain]):"
- "[Number] [things] that [outcome]:"
- "The simplest way to [outcome]:"
- "Stop [common mistake]. Do this instead:"

### Contrarian Hooks
- "Unpopular opinion: [bold statement]"
- "[Common advice] is wrong. Here''s why:"
- "I stopped [common practice] and [positive result]."
- "Everyone says [X]. The truth is [Y]."

### Social Proof Hooks
- "We [achieved result] in [timeframe]. Here''s how:"
- "[Number] people asked me about [topic]. Here''s my answer:"
- "[Authority figure] taught me [lesson]."

---

## Content Repurposing System

Turn one piece of content into many:

### Blog Post → Social Content

| Original | Platform | Format |
|----------|----------|--------|
| Blog post | LinkedIn | Key insight + link in comments |
| Blog post | LinkedIn | Carousel of main points |
| Blog post | Twitter/X | Thread of key takeaways |
| Blog post | Twitter/X | Single tweet with hot take |
| Blog post | Instagram | Carousel with visuals |
| Blog post | Instagram | Reel summarizing the post |

### Podcast/Video → Social Content

| Original | Platform | Format |
|----------|----------|--------|
| Interview | LinkedIn | Quote graphic + insight |
| Interview | Twitter/X | Thread of best quotes |
| Interview | Instagram | Clip as Reel |
| Interview | TikTok | Short clip with caption |
| Interview | YouTube | Shorts from best moments |

### Repurposing Workflow

1. **Create pillar content** (blog, video, podcast)
2. **Extract key insights** (3-5 per piece)
3. **Adapt to each platform** (format and tone)
4. **Schedule across the week** (spread distribution)
5. **Update and reshare** (evergreen content can repeat)

---

## Content Calendar Structure

### Weekly Planning Template

| Day | LinkedIn | Twitter/X | Instagram |
|-----|----------|-----------|-----------|
| Mon | Industry insight | Thread | Carousel |
| Tue | Behind-scenes | Engagement | Story |
| Wed | Educational | Tips tweet | Reel |
| Thu | Story post | Thread | Educational |
| Fri | Hot take | Engagement | Story |
| Sat | — | Curated RT | User content |
| Sun | — | Personal | Behind-scenes |

### Monthly Content Mix

- Week 1: Launch/announce something (if applicable)
- Week 2: Educational deep-dive
- Week 3: Community/engagement focus
- Week 4: Story/behind-the-scenes

### Batching Strategy

**Weekly batching (2-3 hours):**
1. Review content pillar topics
2. Write 5 LinkedIn posts
3. Write 3 Twitter threads + daily tweets
4. Create Instagram carousel + Reel ideas
5. Schedule everything
6. Leave room for real-time engagement

---

## Engagement Strategy

### Proactive Engagement

Engagement isn''t just responding—it''s actively participating:

**Daily engagement routine (30 min):**
1. Respond to all comments on your posts (5 min)
2. Comment on 5-10 posts from target accounts (15 min)
3. Share/repost with added insight (5 min)
4. Send 2-3 DMs to new connections (5 min)

**Quality comments:**
- Add new insight, not just "Great post!"
- Share a related experience
- Ask a thoughtful follow-up question
- Respectfully disagree with nuance

### Building Relationships

- Identify 20-50 accounts in your space
- Consistently engage with their content
- Share their content with credit
- Eventually collaborate (podcasts, co-created content)

### Handling Negative Comments

- Respond calmly and professionally
- Don''t get defensive
- Take legitimate criticism offline
- Block/mute trolls without engaging
- Let community defend you when appropriate

---

## Analytics & Optimization

### Metrics That Matter

**Awareness:**
- Impressions
- Reach
- Follower growth rate

**Engagement:**
- Engagement rate (engagements / impressions)
- Comments (higher value than likes)
- Shares/reposts
- Saves (Instagram)

**Conversion:**
- Link clicks
- Profile visits
- DMs received
- Leads/conversions attributed

### What to Track Weekly

- [ ] Top 3 performing posts (why did they work?)
- [ ] Bottom 3 posts (what can you learn?)
- [ ] Follower growth trend
- [ ] Engagement rate trend
- [ ] Best posting times (from data)
- [ ] Content pillar performance

### Optimization Actions

**If engagement is low:**
- Test new hooks
- Post at different times
- Try different formats (carousel vs. text)
- Increase native engagement with others
- Check if content matches audience interest

**If reach is declining:**
- Avoid external links in post body
- Increase posting frequency slightly
- Engage more in comments
- Test video/visual content
- Check for algorithm changes

---

## Platform-Specific Tips

### LinkedIn Algorithm Tips

- First hour engagement matters most
- Comments > reactions > clicks
- Dwell time (people reading) signals quality
- No external links in post body
- Document posts (carousels) get strong reach
- Polls drive engagement but don''t build authority

### Twitter/X Algorithm Tips

- Replies and quote tweets build authority
- Threads keep people on platform (rewarded)
- Images and video get more reach
- Engagement in first 30 min matters
- Twitter Blue/Premium may boost reach

### Instagram Algorithm Tips

- Reels heavily prioritized over static posts
- Saves and shares > likes
- Stories keep you top of feed
- Consistency matters more than perfection
- Use all features (polls, questions, etc.)

---

## Content Ideas by Situation

### When You''re Starting Out

- Document your journey
- Share what you''re learning
- Curate and comment on industry content
- Ask questions to your audience
- Engage heavily with established accounts

### When You''re Established

- Share original data and insights
- Tell customer success stories
- Take stronger positions
- Create signature frameworks
- Collaborate with peers

### When You''re Stuck

- Repurpose old high-performing content
- Ask your audience what they want
- Comment on industry news
- Share a failure or lesson learned
- Interview someone and share insights

---

## Scheduling Best Practices

### When to Schedule vs. Post Live

**Schedule:**
- Core content posts
- Threads
- Carousels
- Evergreen content

**Post live:**
- Real-time commentary
- Responses to news/trends
- Engagement with others
- Anything requiring immediate interaction

### Queue Management

- Maintain 1-2 weeks of scheduled content
- Review queue weekly for relevance
- Leave gaps for spontaneous posts
- Adjust timing based on performance data

---

## Reverse Engineering Viral Content

Instead of guessing what works, systematically analyze top-performing content in your niche and extract proven patterns.

### The 6-Step Framework

#### 1. NICHE ID — Find Top Creators

Identify 10-20 creators in your space who consistently get high engagement:

**Selection criteria:**
- Posting consistently (3+ times/week)
- High engagement rate relative to follower count
- Audience overlap with your target market
- Mix of established and rising creators

**Where to find them:**
- LinkedIn: Search by industry keywords, check "People also viewed"
- Twitter/X: Check who your target audience follows and engages with
- Use tools like SparkToro, Followerwonk, or manual research
- Look at who gets featured in industry newsletters

#### 2. SCRAPE — Collect Posts at Scale

Gather 500-1000+ posts from your identified creators for analysis:

**Tools:**
- **Apify** — LinkedIn scraper, Twitter scraper actors
- **Phantom Buster** — Multi-platform automation
- **Export tools** — Platform-specific export features
- **Manual collection** — For smaller datasets, copy/paste into spreadsheet

**Data to collect:**
- Post text/content
- Engagement metrics (likes, comments, shares, saves)
- Post format (text-only, carousel, video, image)
- Posting time/day
- Hook/first line
- CTA used
- Topic/theme

#### 3. ANALYZE — Extract What Actually Works

Sort and analyze the data to find patterns:

**Quantitative analysis:**
- Rank posts by engagement rate
- Identify top 10% performers
- Look for format patterns (do carousels outperform?)
- Check timing patterns (best days/times)
- Compare topic performance

**Qualitative analysis:**
- What hooks do top posts use?
- How long are high-performing posts?
- What emotional triggers appear?
- What formats repeat?
- What topics consistently perform?

**Questions to answer:**
- What''s the average length of top posts?
- Which hook types appear most in top 10%?
- What CTAs drive most comments?
- What topics get saved/shared most?

#### 4. PLAYBOOK — Codify Patterns

Document repeatable patterns you can use:

**Hook patterns to codify:**
```
Pattern: "I [unexpected action] and [surprising result]"
Example: "I stopped posting daily and my engagement doubled"
Why it works: Curiosity gap + contrarian

Pattern: "[Specific number] [things] that [outcome]:"
Example: "7 pricing mistakes that cost me $50K:"
Why it works: Specificity + loss aversion

Pattern: "[Controversial take]"
Example: "Cold outreach is dead."
Why it works: Pattern interrupt + invites debate
```

**Format patterns:**
- Carousel: Hook slide → Problem → Solution steps → CTA
- Thread: Hook → Promise → Deliver → Recap → CTA
- Story post: Hook → Setup → Conflict → Resolution → Lesson

**CTA patterns:**
- Question: "What would you add?"
- Agreement: "Agree or disagree?"
- Share: "Tag someone who needs this"
- Save: "Save this for later"

#### 5. LAYER VOICE — Apply Direct Response Principles

Take proven patterns and make them yours with these voice principles:

**"Smart friend who figured something out"**
- Write like you''re texting advice to a friend
- Share discoveries, not lectures
- Use "I found that..." not "You should..."
- Be helpful, not preachy

**Specific > Vague**
```
❌ "I made good revenue"
✅ "I made $47,329"

❌ "It took a while"
✅ "It took 47 days"

❌ "A lot of people"
✅ "2,847 people"
```

**Short. Breathe. Land.**
- One idea per sentence
- Use line breaks liberally
- Let important points stand alone
- Create rhythm: short, short, longer explanation

```
❌ "I spent three years building my business the wrong way before I finally realized that the key to success was focusing on fewer things and doing them exceptionally well."

✅ "I built wrong for 3 years.

Then I figured it out.

Focus on less.
Do it exceptionally well.

Everything changed."
```

**Write from emotion**
- Start with how you felt, not what you did
- Use emotional words: frustrated, excited, terrified, obsessed
- Show vulnerability when authentic
- Connect the feeling to the lesson

```
❌ "Here''s what I learned about pricing"

✅ "I was terrified to raise my prices.

My hands were shaking when I sent the email.

Here''s what happened..."
```

#### 6. CONVERT — Turn Attention into Action

Bridge from engagement to business results:

**Soft conversions:**
- Newsletter signups in bio/comments
- Free resource offers in follow-up comments
- DM triggers ("Comment X and I''ll send you...")
- Profile visits → optimized profile with clear CTA

**Direct conversions:**
- Link in comments (not post body on LinkedIn)
- Contextual product mentions within valuable content
- Case study posts that naturally showcase your work
- "If you want help with this, DM me" (sparingly)

### Output: Proven Patterns + Right Voice = Performance

The formula:
```
1. Find what''s already working (don''t guess)
2. Extract the patterns (hooks, formats, CTAs)
3. Layer your authentic voice on top
4. Test and iterate based on your own data
```

### Reverse Engineering Checklist

- [ ] Identified 10-20 top creators in niche
- [ ] Collected 500+ posts for analysis
- [ ] Ranked by engagement rate
- [ ] Documented top 10 hook patterns
- [ ] Documented top 5 format patterns
- [ ] Documented top 5 CTA patterns
- [ ] Created voice guidelines (specificity, brevity, emotion)
- [ ] Built template library from patterns
- [ ] Set up tracking for your own content performance

---

## Questions to Ask

If you need more context:
1. What platform(s) are you focusing on?
2. What''s your current posting frequency?
3. Do you have existing content to repurpose?
4. What content has performed well in the past?
5. How much time can you dedicate weekly?
6. Are you building personal brand, company brand, or both?

---

## Related Skills

- **copywriting**: For longer-form content that feeds social
- **launch-strategy**: For coordinating social with launches
- **email-sequence**: For nurturing social audience via email
- **marketing-psychology**: For understanding what drives engagement
', '{"name": "social-content", "description": "When the user wants help creating, scheduling, or optimizing social media content for LinkedIn, Twitter/X, Instagram, TikTok, Facebook, or other platforms. Also use when the user mentions ''LinkedIn post,'' ''Twitter thread,'' ''social media,'' ''content calendar,'' ''social scheduling,'' ''engagement,'' or ''viral content.'' This skill covers content creation, repurposing, and platform-specific strategies."}'::jsonb),
('threejs-animation', 'Three.js animation - keyframe animation, skeletal animation, morph targets, animation mixing. Use when animating objects, playing GLTF animations, creating procedural motion, or blending animations.', 'general', '---
name: threejs-animation
description: Three.js animation - keyframe animation, skeletal animation, morph targets, animation mixing. Use when animating objects, playing GLTF animations, creating procedural motion, or blending animations.
---

# Three.js Animation

## Quick Start

```javascript
import * as THREE from "three";

// Simple procedural animation
const clock = new THREE.Clock();

function animate() {
  const delta = clock.getDelta();
  const elapsed = clock.getElapsedTime();

  mesh.rotation.y += delta;
  mesh.position.y = Math.sin(elapsed) * 0.5;

  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
```

## Animation System Overview

Three.js animation system has three main components:

1. **AnimationClip** - Container for keyframe data
2. **AnimationMixer** - Plays animations on a root object
3. **AnimationAction** - Controls playback of a clip

## AnimationClip

Stores keyframe animation data.

```javascript
// Create animation clip
const times = [0, 1, 2]; // Keyframe times (seconds)
const values = [0, 1, 0]; // Values at each keyframe

const track = new THREE.NumberKeyframeTrack(
  ".position[y]", // Property path
  times,
  values,
);

const clip = new THREE.AnimationClip("bounce", 2, [track]);
```

### KeyframeTrack Types

```javascript
// Number track (single value)
new THREE.NumberKeyframeTrack(".opacity", times, [1, 0]);
new THREE.NumberKeyframeTrack(".material.opacity", times, [1, 0]);

// Vector track (position, scale)
new THREE.VectorKeyframeTrack(".position", times, [
  0,
  0,
  0, // t=0
  1,
  2,
  0, // t=1
  0,
  0,
  0, // t=2
]);

// Quaternion track (rotation)
const q1 = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 0, 0));
const q2 = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, Math.PI, 0));
new THREE.QuaternionKeyframeTrack(
  ".quaternion",
  [0, 1],
  [q1.x, q1.y, q1.z, q1.w, q2.x, q2.y, q2.z, q2.w],
);

// Color track
new THREE.ColorKeyframeTrack(".material.color", times, [
  1,
  0,
  0, // red
  0,
  1,
  0, // green
  0,
  0,
  1, // blue
]);

// Boolean track
new THREE.BooleanKeyframeTrack(".visible", [0, 0.5, 1], [true, false, true]);

// String track (for morph targets)
new THREE.StringKeyframeTrack(
  ".morphTargetInfluences[smile]",
  [0, 1],
  ["0", "1"],
);
```

### Interpolation Modes

```javascript
const track = new THREE.VectorKeyframeTrack(".position", times, values);

// Interpolation
track.setInterpolation(THREE.InterpolateLinear); // Default
track.setInterpolation(THREE.InterpolateSmooth); // Cubic spline
track.setInterpolation(THREE.InterpolateDiscrete); // Step function
```

## AnimationMixer

Plays animations on an object and its descendants.

```javascript
const mixer = new THREE.AnimationMixer(model);

// Create action from clip
const action = mixer.clipAction(clip);
action.play();

// Update in animation loop
function animate() {
  const delta = clock.getDelta();
  mixer.update(delta); // Required!

  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
```

### Mixer Events

```javascript
mixer.addEventListener("finished", (e) => {
  console.log("Animation finished:", e.action.getClip().name);
});

mixer.addEventListener("loop", (e) => {
  console.log("Animation looped:", e.action.getClip().name);
});
```

## AnimationAction

Controls playback of an animation clip.

```javascript
const action = mixer.clipAction(clip);

// Playback control
action.play();
action.stop();
action.reset();
action.halt(fadeOutDuration);

// Playback state
action.isRunning();
action.isScheduled();

// Time control
action.time = 0.5; // Current time
action.timeScale = 1; // Playback speed (negative = reverse)
action.paused = false;

// Weight (for blending)
action.weight = 1; // 0-1, contribution to final pose
action.setEffectiveWeight(1);

// Loop modes
action.loop = THREE.LoopRepeat; // Default: loop forever
action.loop = THREE.LoopOnce; // Play once and stop
action.loop = THREE.LoopPingPong; // Alternate forward/backward
action.repetitions = 3; // Number of loops (Infinity default)

// Clamping
action.clampWhenFinished = true; // Hold last frame when done

// Blending
action.blendMode = THREE.NormalAnimationBlendMode;
action.blendMode = THREE.AdditiveAnimationBlendMode;
```

### Fade In/Out

```javascript
// Fade in
action.reset().fadeIn(0.5).play();

// Fade out
action.fadeOut(0.5);

// Crossfade between animations
const action1 = mixer.clipAction(clip1);
const action2 = mixer.clipAction(clip2);

action1.play();

// Later, crossfade to action2
action1.crossFadeTo(action2, 0.5, true);
action2.play();
```

## Loading GLTF Animations

Most common source of skeletal animations.

```javascript
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

const loader = new GLTFLoader();
loader.load("model.glb", (gltf) => {
  const model = gltf.scene;
  scene.add(model);

  // Create mixer
  const mixer = new THREE.AnimationMixer(model);

  // Get all clips
  const clips = gltf.animations;
  console.log(
    "Available animations:",
    clips.map((c) => c.name),
);

  // Play first animation
  if (clips.length > 0) {
    const action = mixer.clipAction(clips[0]);
    action.play();
  }

  // Play specific animation by name
  const walkClip = THREE.AnimationClip.findByName(clips, "Walk");
  if (walkClip) {
    mixer.clipAction(walkClip).play();
  }

  // Store mixer for update loop
  window.mixer = mixer;
});

// Animation loop
function animate() {
  const delta = clock.getDelta();
  if (window.mixer) window.mixer.update(delta);

  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
```

## Skeletal Animation

### Skeleton and Bones

```javascript
// Access skeleton from skinned mesh
const skinnedMesh = model.getObjectByProperty("type", "SkinnedMesh");
const skeleton = skinnedMesh.skeleton;

// Access bones
skeleton.bones.forEach((bone) => {
  console.log(bone.name, bone.position, bone.rotation);
});

// Find specific bone by name
const headBone = skeleton.bones.find((b) => b.name === "Head");
if (headBone) headBone.rotation.y = Math.PI / 4; // Turn head

// Skeleton helper
const helper = new THREE.SkeletonHelper(model);
scene.add(helper);
```

### Programmatic Bone Animation

```javascript
function animate() {
  const time = clock.getElapsedTime();

  // Animate bone
  const headBone = skeleton.bones.find((b) => b.name === "Head");
  if (headBone) {
    headBone.rotation.y = Math.sin(time) * 0.3;
  }

  // Update mixer if also playing clips
  mixer.update(clock.getDelta());
}
```

### Bone Attachments

```javascript
// Attach object to bone
const weapon = new THREE.Mesh(weaponGeometry, weaponMaterial);
const handBone = skeleton.bones.find((b) => b.name === "RightHand");
if (handBone) handBone.add(weapon);

// Offset attachment
weapon.position.set(0, 0, 0.5);
weapon.rotation.set(0, Math.PI / 2, 0);
```

## Morph Targets

Blend between different mesh shapes.

```javascript
// Morph targets are stored in geometry
const geometry = mesh.geometry;
console.log("Morph attributes:", Object.keys(geometry.morphAttributes));

// Access morph target influences
mesh.morphTargetInfluences; // Array of weights
mesh.morphTargetDictionary; // Name -> index mapping

// Set morph target by index
mesh.morphTargetInfluences[0] = 0.5;

// Set by name
const smileIndex = mesh.morphTargetDictionary["smile"];
mesh.morphTargetInfluences[smileIndex] = 1;
```

### Animating Morph Targets

```javascript
// Procedural
function animate() {
  const t = clock.getElapsedTime();
  mesh.morphTargetInfluences[0] = (Math.sin(t) + 1) / 2;
}

// With keyframe animation
const track = new THREE.NumberKeyframeTrack(
  ".morphTargetInfluences[smile]",
  [0, 0.5, 1],
  [0, 1, 0],
);
const clip = new THREE.AnimationClip("smile", 1, [track]);
mixer.clipAction(clip).play();
```

## Animation Blending

Mix multiple animations together.

```javascript
// Setup actions
const idleAction = mixer.clipAction(idleClip);
const walkAction = mixer.clipAction(walkClip);
const runAction = mixer.clipAction(runClip);

// Play all with different weights
idleAction.play();
walkAction.play();
runAction.play();

// Set initial weights
idleAction.setEffectiveWeight(1);
walkAction.setEffectiveWeight(0);
runAction.setEffectiveWeight(0);

// Blend based on speed
function updateAnimations(speed) {
  if (speed < 0.1) {
    idleAction.setEffectiveWeight(1);
    walkAction.setEffectiveWeight(0);
    runAction.setEffectiveWeight(0);
  } else if (speed < 5) {
    const t = speed / 5;
    idleAction.setEffectiveWeight(1 - t);
    walkAction.setEffectiveWeight(t);
    runAction.setEffectiveWeight(0);
  } else {
    const t = Math.min((speed - 5) / 5, 1);
    idleAction.setEffectiveWeight(0);
    walkAction.setEffectiveWeight(1 - t);
    runAction.setEffectiveWeight(t);
  }
}
```

### Additive Blending

```javascript
// Base pose
const baseAction = mixer.clipAction(baseClip);
baseAction.play();

// Additive layer (e.g., breathing)
const additiveAction = mixer.clipAction(additiveClip);
additiveAction.blendMode = THREE.AdditiveAnimationBlendMode;
additiveAction.play();

// Convert clip to additive
THREE.AnimationUtils.makeClipAdditive(additiveClip);
```

## Animation Utilities

```javascript
import * as THREE from "three";

// Find clip by name
const clip = THREE.AnimationClip.findByName(clips, "Walk");

// Create subclip
const subclip = THREE.AnimationUtils.subclip(clip, "subclip", 0, 30, 30);

// Convert to additive
THREE.AnimationUtils.makeClipAdditive(clip);
THREE.AnimationUtils.makeClipAdditive(clip, 0, referenceClip);

// Clone clip
const clone = clip.clone();

// Get clip duration
clip.duration;

// Optimize clip (remove redundant keyframes)
clip.optimize();

// Reset clip to first frame
clip.resetDuration();
```

## Procedural Animation Patterns

### Smooth Damping

```javascript
// Smooth follow/lerp
const target = new THREE.Vector3();
const current = new THREE.Vector3();
const velocity = new THREE.Vector3();

function smoothDamp(current, target, velocity, smoothTime, deltaTime) {
  const omega = 2 / smoothTime;
  const x = omega * deltaTime;
  const exp = 1 / (1 + x + 0.48 * x * x + 0.235 * x * x * x);
  const change = current.clone().sub(target);
  const temp = velocity
    .clone()
    .add(change.clone().multiplyScalar(omega))
    .multiplyScalar(deltaTime);
  velocity.sub(temp.clone().multiplyScalar(omega)).multiplyScalar(exp);
  return target.clone().add(change.add(temp).multiplyScalar(exp));
}

function animate() {
  current.copy(smoothDamp(current, target, velocity, 0.3, delta));
  mesh.position.copy(current);
}
```

### Spring Physics

```javascript
class Spring {
  constructor(stiffness = 100, damping = 10) {
    this.stiffness = stiffness;
    this.damping = damping;
    this.position = 0;
    this.velocity = 0;
    this.target = 0;
  }

  update(dt) {
    const force = -this.stiffness * (this.position - this.target);
    const dampingForce = -this.damping * this.velocity;
    this.velocity += (force + dampingForce) * dt;
    this.position += this.velocity * dt;
    return this.position;
  }
}

const spring = new Spring(100, 10);
spring.target = 1;

function animate() {
  mesh.position.y = spring.update(delta);
}
```

### Oscillation

```javascript
function animate() {
  const t = clock.getElapsedTime();

  // Sine wave
  mesh.position.y = Math.sin(t * 2) * 0.5;

  // Bouncing
  mesh.position.y = Math.abs(Math.sin(t * 3)) * 2;

  // Circular motion
  mesh.position.x = Math.cos(t) * 2;
  mesh.position.z = Math.sin(t) * 2;

  // Figure 8
  mesh.position.x = Math.sin(t) * 2;
  mesh.position.z = Math.sin(t * 2) * 1;
}
```

## Performance Tips

1. **Share clips**: Same AnimationClip can be used on multiple mixers
2. **Optimize clips**: Call `clip.optimize()` to remove redundant keyframes
3. **Disable when off-screen**: Stop mixer updates for invisible objects
4. **Use LOD for animations**: Simpler rigs for distant characters
5. **Limit active mixers**: Each mixer.update() has a cost

```javascript
// Pause animation when not visible
mesh.onBeforeRender = () => {
  action.paused = false;
};

mesh.onAfterRender = () => {
  // Check if will be visible next frame
  if (!isInFrustum(mesh)) {
    action.paused = true;
  }
};

// Cache clips
const clipCache = new Map();
function getClip(name) {
  if (!clipCache.has(name)) {
    clipCache.set(name, loadClip(name));
  }
  return clipCache.get(name);
}
```

## See Also

- `threejs-loaders` - Loading animated GLTF models
- `threejs-fundamentals` - Clock and animation loop
- `threejs-shaders` - Vertex animation in shaders
', '{"name": "threejs-animation", "description": "Three.js animation - keyframe animation, skeletal animation, morph targets, animation mixing. Use when animating objects, playing GLTF animations, creating procedural motion, or blending animations."}'::jsonb),
('threejs-fundamentals', 'Three.js scene setup, cameras, renderer, Object3D hierarchy, coordinate systems. Use when setting up 3D scenes, creating cameras, configuring renderers, managing object hierarchies, or working with transforms.', 'general', '---
name: threejs-fundamentals
description: Three.js scene setup, cameras, renderer, Object3D hierarchy, coordinate systems. Use when setting up 3D scenes, creating cameras, configuring renderers, managing object hierarchies, or working with transforms.
---

# Three.js Fundamentals

## Quick Start

```javascript
import * as THREE from "three";

// Create scene, camera, renderer
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(
  75,
  window.innerWidth / window.innerHeight,
  0.1,
  1000,
);
const renderer = new THREE.WebGLRenderer({ antialias: true });

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);

// Add a mesh
const geometry = new THREE.BoxGeometry(1, 1, 1);
const material = new THREE.MeshStandardMaterial({ color: 0x00ff00 });
const cube = new THREE.Mesh(geometry, material);
scene.add(cube);

// Add light
scene.add(new THREE.AmbientLight(0xffffff, 0.5));
const dirLight = new THREE.DirectionalLight(0xffffff, 1);
dirLight.position.set(5, 5, 5);
scene.add(dirLight);

camera.position.z = 5;

// Animation loop
function animate() {
  requestAnimationFrame(animate);
  cube.rotation.x += 0.01;
  cube.rotation.y += 0.01;
  renderer.render(scene, camera);
}
animate();

// Handle resize
window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
```

## Core Classes

### Scene

Container for all 3D objects, lights, and cameras.

```javascript
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000); // Solid color
scene.background = texture; // Skybox texture
scene.background = cubeTexture; // Cubemap
scene.environment = envMap; // Environment map for PBR
scene.fog = new THREE.Fog(0xffffff, 1, 100); // Linear fog
scene.fog = new THREE.FogExp2(0xffffff, 0.02); // Exponential fog
```

### Cameras

**PerspectiveCamera** - Most common, simulates human eye.

```javascript
// PerspectiveCamera(fov, aspect, near, far)
const camera = new THREE.PerspectiveCamera(
  75, // Field of view (degrees)
  window.innerWidth / window.innerHeight, // Aspect ratio
  0.1, // Near clipping plane
  1000, // Far clipping plane
);

camera.position.set(0, 5, 10);
camera.lookAt(0, 0, 0);
camera.updateProjectionMatrix(); // Call after changing fov, aspect, near, far
```

**OrthographicCamera** - No perspective distortion, good for 2D/isometric.

```javascript
// OrthographicCamera(left, right, top, bottom, near, far)
const aspect = window.innerWidth / window.innerHeight;
const frustumSize = 10;
const camera = new THREE.OrthographicCamera(
  (frustumSize * aspect) / -2,
  (frustumSize * aspect) / 2,
  frustumSize / 2,
  frustumSize / -2,
  0.1,
  1000,
);
```

**ArrayCamera** - Multiple viewports with sub-cameras.

```javascript
const cameras = [];
for (let i = 0; i < 4; i++) {
  const subcamera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  subcamera.viewport = new THREE.Vector4(
    Math.floor(i % 2) * 0.5,
    Math.floor(i / 2) * 0.5,
    0.5,
    0.5,
  );
  cameras.push(subcamera);
}
const arrayCamera = new THREE.ArrayCamera(cameras);
```

**CubeCamera** - Renders environment maps for reflections.

```javascript
const cubeRenderTarget = new THREE.WebGLCubeRenderTarget(256);
const cubeCamera = new THREE.CubeCamera(0.1, 1000, cubeRenderTarget);
scene.add(cubeCamera);

// Use for reflections
material.envMap = cubeRenderTarget.texture;

// Update each frame (expensive!)
cubeCamera.position.copy(reflectiveMesh.position);
cubeCamera.update(renderer, scene);
```

### WebGLRenderer

```javascript
const renderer = new THREE.WebGLRenderer({
  canvas: document.querySelector("#canvas"), // Optional existing canvas
  antialias: true, // Smooth edges
  alpha: true, // Transparent background
  powerPreference: "high-performance", // GPU hint
  preserveDrawingBuffer: true, // For screenshots
});

renderer.setSize(width, height);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

// Tone mapping
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;

// Color space (Three.js r152+)
renderer.outputColorSpace = THREE.SRGBColorSpace;

// Shadows
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

// Clear color
renderer.setClearColor(0x000000, 1);

// Render
renderer.render(scene, camera);
```

### Object3D

Base class for all 3D objects. Mesh, Group, Light, Camera all extend Object3D.

```javascript
const obj = new THREE.Object3D();

// Transform
obj.position.set(x, y, z);
obj.rotation.set(x, y, z); // Euler angles (radians)
obj.quaternion.set(x, y, z, w); // Quaternion rotation
obj.scale.set(x, y, z);

// Local vs World transforms
obj.getWorldPosition(targetVector);
obj.getWorldQuaternion(targetQuaternion);
obj.getWorldDirection(targetVector);

// Hierarchy
obj.add(child);
obj.remove(child);
obj.parent;
obj.children;

// Visibility
obj.visible = false;

// Layers (for selective rendering/raycasting)
obj.layers.set(1);
obj.layers.enable(2);
obj.layers.disable(0);

// Traverse hierarchy
obj.traverse((child) => {
  if (child.isMesh) child.material.color.set(0xff0000);
});

// Matrix updates
obj.matrixAutoUpdate = true; // Default: auto-update matrices
obj.updateMatrix(); // Manual matrix update
obj.updateMatrixWorld(true); // Update world matrix recursively
```

### Group

Empty container for organizing objects.

```javascript
const group = new THREE.Group();
group.add(mesh1);
group.add(mesh2);
scene.add(group);

// Transform entire group
group.position.x = 5;
group.rotation.y = Math.PI / 4;
```

### Mesh

Combines geometry and material.

```javascript
const mesh = new THREE.Mesh(geometry, material);

// Multiple materials (one per geometry group)
const mesh = new THREE.Mesh(geometry, [material1, material2]);

// Useful properties
mesh.geometry;
mesh.material;
mesh.castShadow = true;
mesh.receiveShadow = true;

// Frustum culling
mesh.frustumCulled = true; // Default: skip if outside camera view

// Render order
mesh.renderOrder = 10; // Higher = rendered later
```

## Coordinate System

Three.js uses a **right-handed coordinate system**:

- **+X** points right
- **+Y** points up
- **+Z** points toward viewer (out of screen)

```javascript
// Axes helper
const axesHelper = new THREE.AxesHelper(5);
scene.add(axesHelper); // Red=X, Green=Y, Blue=Z
```

## Math Utilities

### Vector3

```javascript
const v = new THREE.Vector3(x, y, z);
v.set(x, y, z);
v.copy(otherVector);
v.clone();

// Operations (modify in place)
v.add(v2);
v.sub(v2);
v.multiply(v2);
v.multiplyScalar(2);
v.divideScalar(2);
v.normalize();
v.negate();
v.clamp(min, max);
v.lerp(target, alpha);

// Calculations (return new value)
v.length();
v.lengthSq(); // Faster than length()
v.distanceTo(v2);
v.dot(v2);
v.cross(v2); // Modifies v
v.angleTo(v2);

// Transform
v.applyMatrix4(matrix);
v.applyQuaternion(q);
v.project(camera); // World to NDC
v.unproject(camera); // NDC to world
```

### Matrix4

```javascript
const m = new THREE.Matrix4();
m.identity();
m.copy(other);
m.clone();

// Build transforms
m.makeTranslation(x, y, z);
m.makeRotationX(theta);
m.makeRotationY(theta);
m.makeRotationZ(theta);
m.makeRotationFromQuaternion(q);
m.makeScale(x, y, z);

// Compose/decompose
m.compose(position, quaternion, scale);
m.decompose(position, quaternion, scale);

// Operations
m.multiply(m2); // m = m * m2
m.premultiply(m2); // m = m2 * m
m.invert();
m.transpose();

// Camera matrices
m.makePerspective(left, right, top, bottom, near, far);
m.makeOrthographic(left, right, top, bottom, near, far);
m.lookAt(eye, target, up);
```

### Quaternion

```javascript
const q = new THREE.Quaternion();
q.setFromEuler(euler);
q.setFromAxisAngle(axis, angle);
q.setFromRotationMatrix(matrix);

q.multiply(q2);
q.slerp(target, t); // Spherical interpolation
q.normalize();
q.invert();
```

### Euler

```javascript
const euler = new THREE.Euler(x, y, z, "XYZ"); // Order matters!
euler.setFromQuaternion(q);
euler.setFromRotationMatrix(m);

// Rotation orders: ''XYZ'', ''YXZ'', ''ZXY'', ''XZY'', ''YZX'', ''ZYX''
```

### Color

```javascript
const color = new THREE.Color(0xff0000);
const color = new THREE.Color("red");
const color = new THREE.Color("rgb(255, 0, 0)");
const color = new THREE.Color("#ff0000");

color.setHex(0x00ff00);
color.setRGB(r, g, b); // 0-1 range
color.setHSL(h, s, l); // 0-1 range

color.lerp(otherColor, alpha);
color.multiply(otherColor);
color.multiplyScalar(2);
```

### MathUtils

```javascript
THREE.MathUtils.clamp(value, min, max);
THREE.MathUtils.lerp(start, end, alpha);
THREE.MathUtils.mapLinear(value, inMin, inMax, outMin, outMax);
THREE.MathUtils.degToRad(degrees);
THREE.MathUtils.radToDeg(radians);
THREE.MathUtils.randFloat(min, max);
THREE.MathUtils.randInt(min, max);
THREE.MathUtils.smoothstep(x, min, max);
THREE.MathUtils.smootherstep(x, min, max);
```

## Common Patterns

### Proper Cleanup

```javascript
function dispose() {
  // Dispose geometries
  mesh.geometry.dispose();

  // Dispose materials
  if (Array.isArray(mesh.material)) {
    mesh.material.forEach((m) => m.dispose());
  } else {
    mesh.material.dispose();
  }

  // Dispose textures
  texture.dispose();

  // Remove from scene
  scene.remove(mesh);

  // Dispose renderer
  renderer.dispose();
}
```

### Clock for Animation

```javascript
const clock = new THREE.Clock();

function animate() {
  const delta = clock.getDelta(); // Time since last frame (seconds)
  const elapsed = clock.getElapsedTime(); // Total time (seconds)

  mesh.rotation.y += delta * 0.5; // Consistent speed regardless of framerate

  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
```

### Responsive Canvas

```javascript
function onWindowResize() {
  const width = window.innerWidth;
  const height = window.innerHeight;

  camera.aspect = width / height;
  camera.updateProjectionMatrix();

  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
}
window.addEventListener("resize", onWindowResize);
```

### Loading Manager

```javascript
const manager = new THREE.LoadingManager();

manager.onStart = (url, loaded, total) => console.log("Started loading");
manager.onLoad = () => console.log("All loaded");
manager.onProgress = (url, loaded, total) => console.log(`${loaded}/${total}`);
manager.onError = (url) => console.error(`Error loading ${url}`);

const textureLoader = new THREE.TextureLoader(manager);
const gltfLoader = new GLTFLoader(manager);
```

## Performance Tips

1. **Limit draw calls**: Merge geometries, use instancing, atlas textures
2. **Frustum culling**: Enabled by default, ensure bounding boxes are correct
3. **LOD (Level of Detail)**: Use `THREE.LOD` for distance-based mesh switching
4. **Object pooling**: Reuse objects instead of creating/destroying
5. **Avoid `getWorldPosition` in loops**: Cache results

```javascript
// Merge static geometries
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
const merged = mergeGeometries([geo1, geo2, geo3]);

// LOD
const lod = new THREE.LOD();
lod.addLevel(highDetailMesh, 0);
lod.addLevel(medDetailMesh, 50);
lod.addLevel(lowDetailMesh, 100);
scene.add(lod);
```

## See Also

- `threejs-geometry` - Geometry creation and manipulation
- `threejs-materials` - Material types and properties
- `threejs-lighting` - Light types and shadows
', '{"name": "threejs-fundamentals", "description": "Three.js scene setup, cameras, renderer, Object3D hierarchy, coordinate systems. Use when setting up 3D scenes, creating cameras, configuring renderers, managing object hierarchies, or working with transforms."}'::jsonb),
('threejs-geometry', 'Three.js geometry creation - built-in shapes, BufferGeometry, custom geometry, instancing. Use when creating 3D shapes, working with vertices, building custom meshes, or optimizing with instanced rendering.', 'general', '---
name: threejs-geometry
description: Three.js geometry creation - built-in shapes, BufferGeometry, custom geometry, instancing. Use when creating 3D shapes, working with vertices, building custom meshes, or optimizing with instanced rendering.
---

# Three.js Geometry

## Quick Start

```javascript
import * as THREE from "three";

// Built-in geometry
const box = new THREE.BoxGeometry(1, 1, 1);
const sphere = new THREE.SphereGeometry(0.5, 32, 32);
const plane = new THREE.PlaneGeometry(10, 10);

// Create mesh
const material = new THREE.MeshStandardMaterial({ color: 0x00ff00 });
const mesh = new THREE.Mesh(box, material);
scene.add(mesh);
```

## Built-in Geometries

### Basic Shapes

```javascript
// Box - width, height, depth, widthSegments, heightSegments, depthSegments
new THREE.BoxGeometry(1, 1, 1, 1, 1, 1);

// Sphere - radius, widthSegments, heightSegments, phiStart, phiLength, thetaStart, thetaLength
new THREE.SphereGeometry(1, 32, 32);
new THREE.SphereGeometry(1, 32, 32, 0, Math.PI * 2, 0, Math.PI); // Full sphere
new THREE.SphereGeometry(1, 32, 32, 0, Math.PI); // Hemisphere

// Plane - width, height, widthSegments, heightSegments
new THREE.PlaneGeometry(10, 10, 1, 1);

// Circle - radius, segments, thetaStart, thetaLength
new THREE.CircleGeometry(1, 32);
new THREE.CircleGeometry(1, 32, 0, Math.PI); // Semicircle

// Cylinder - radiusTop, radiusBottom, height, radialSegments, heightSegments, openEnded
new THREE.CylinderGeometry(1, 1, 2, 32, 1, false);
new THREE.CylinderGeometry(0, 1, 2, 32); // Cone
new THREE.CylinderGeometry(1, 1, 2, 6); // Hexagonal prism

// Cone - radius, height, radialSegments, heightSegments, openEnded
new THREE.ConeGeometry(1, 2, 32, 1, false);

// Torus - radius, tube, radialSegments, tubularSegments, arc
new THREE.TorusGeometry(1, 0.4, 16, 100);

// TorusKnot - radius, tube, tubularSegments, radialSegments, p, q
new THREE.TorusKnotGeometry(1, 0.4, 100, 16, 2, 3);

// Ring - innerRadius, outerRadius, thetaSegments, phiSegments
new THREE.RingGeometry(0.5, 1, 32, 1);
```

### Advanced Shapes

```javascript
// Capsule - radius, length, capSegments, radialSegments
new THREE.CapsuleGeometry(0.5, 1, 4, 8);

// Dodecahedron - radius, detail
new THREE.DodecahedronGeometry(1, 0);

// Icosahedron - radius, detail (0 = 20 faces, higher = smoother)
new THREE.IcosahedronGeometry(1, 0);

// Octahedron - radius, detail
new THREE.OctahedronGeometry(1, 0);

// Tetrahedron - radius, detail
new THREE.TetrahedronGeometry(1, 0);

// Polyhedron - vertices, indices, radius, detail
const vertices = [1, 1, 1, -1, -1, 1, -1, 1, -1, 1, -1, -1];
const indices = [2, 1, 0, 0, 3, 2, 1, 3, 0, 2, 3, 1];
new THREE.PolyhedronGeometry(vertices, indices, 1, 0);
```

### Path-Based Shapes

```javascript
// Lathe - points[], segments, phiStart, phiLength
const points = [
  new THREE.Vector2(0, 0),
new THREE.Vector2(0.5, 0),
new THREE.Vector2(0.5, 1),
new THREE.Vector2(0, 1),
];
new THREE.LatheGeometry(points, 32);

// Extrude - shape, options
const shape = new THREE.Shape();
shape.moveTo(0, 0);
shape.lineTo(1, 0);
shape.lineTo(1, 1);
shape.lineTo(0, 1);
shape.lineTo(0, 0);

const extrudeSettings = {
  steps: 2,
  depth: 1,
  bevelEnabled: true,
  bevelThickness: 0.1,
  bevelSize: 0.1,
  bevelSegments: 3,
};
new THREE.ExtrudeGeometry(shape, extrudeSettings);

// Tube - path, tubularSegments, radius, radialSegments, closed
const curve = new THREE.CatmullRomCurve3([
  new THREE.Vector3(-1, 0, 0);