# Onboarding Flow

> Part of [PRD Documentation](README.md)

## Overview

Goal: Get a CTO from sign-up to seeing their first dashboard in <15 minutes.

**Key principle:** GitHub org connection auto-discovers team members, minimizing manual setup.

---

## Step 1: Sign Up

```
┌─────────────────────────────────────────┐
│           Create Your Account           │
├─────────────────────────────────────────┤
│                                         │
│  Email: [________________________]      │
│  Password: [____________________]       │
│                                         │
│  ─── OR ───                            │
│                                         │
│  [🔵 Continue with Google]              │
│                                         │
├─────────────────────────────────────────┤
│  Company name: [________________]       │
│                                         │
│  Team size:                             │
│  ○ 1-10 developers                      │
│  ○ 11-25 developers                     │
│  ○ 26-50 developers                     │
│  ○ 50+ developers                       │
│                                         │
│  [Create Account]                       │
└─────────────────────────────────────────┘
```

---

## Step 2: Connect Supabase (BYOS)

```
┌─────────────────────────────────────────┐
│         Set Up Your Database            │
├─────────────────────────────────────────┤
│                                         │
│  Your data stays in YOUR database.      │
│  We never store your engineering data.  │
│                                         │
│  📘 Don't have Supabase? [Create free]  │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Supabase URL:                          │
│  [https://xxx.supabase.co_________]     │
│                                         │
│  Service Role Key:                      │
│  [eyJhbGciOiJIUzI1NiIsInR5cCI6___]     │
│                                         │
│  [Test Connection]                      │
│                                         │
│  ✅ Connected! We'll create tables      │
│     automatically.                      │
│                                         │
│  [Continue →]                           │
└─────────────────────────────────────────┘
```

**Behind the scenes:**
- Test connection to Supabase
- Run migration script to create tables
- Verify RLS policies are enabled

---

## Step 3: Connect GitHub (Auto-Discovery)

```
┌─────────────────────────────────────────┐
│        Connect GitHub Organization      │
├─────────────────────────────────────────┤
│                                         │
│  We'll import your team from GitHub.    │
│                                         │
│  [🐙 Connect with GitHub]               │
│                                         │
└─────────────────────────────────────────┘
```

After OAuth:

```
┌─────────────────────────────────────────┐
│        Select Your Organization         │
├─────────────────────────────────────────┤
│                                         │
│  Choose organization:                   │
│  [▼ acme-corp                     ]     │
│     ├─ acme-corp (42 members)           │
│     └─ my-personal-org (3 members)      │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  🎉 Found 42 team members!              │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ 👤 john-doe                     │    │
│  │    john@acme.com                │    │
│  │ 👤 jane-smith                   │    │
│  │    jane@acme.com                │    │
│  │ 👤 bob-wilson                   │    │
│  │    bob@acme.com                 │    │
│  │ ... and 39 more                 │    │
│  └─────────────────────────────────┘    │
│                                         │
│  Select repositories to track:          │
│  ☑️ acme-corp/main-app                  │
│  ☑️ acme-corp/api-service               │
│  ☑️ acme-corp/mobile-app                │
│  ☐ acme-corp/docs (uncheck if needed)   │
│                                         │
│  [Continue →]                           │
└─────────────────────────────────────────┘
```

**Behind the scenes:**
- Fetch org members via GitHub API
- Fetch team structure (if GitHub Teams used)
- Create user records in client's Supabase
- Set up webhooks for selected repos

---

## Step 4: Connect Jira

```
┌─────────────────────────────────────────┐
│              Connect Jira               │
├─────────────────────────────────────────┤
│                                         │
│  Link Jira to see story points,         │
│  sprint velocity, and issue cycle time. │
│                                         │
│  [🔵 Connect with Atlassian]            │
│                                         │
│  [Skip for now →]                       │
└─────────────────────────────────────────┘
```

After OAuth:

```
┌─────────────────────────────────────────┐
│          Select Jira Projects           │
├─────────────────────────────────────────┤
│                                         │
│  Which projects should we track?        │
│                                         │
│  ☑️ ACME - Main Product                 │
│  ☑️ API - API Development               │
│  ☐ OPS - Operations (internal)          │
│                                         │
│  [Continue →]                           │
└─────────────────────────────────────────┘
```

**Behind the scenes:**
- Match Jira users to GitHub users by email
- Identify any unmatched users

---

## Step 5: Connect Slack

```
┌─────────────────────────────────────────┐
│             Connect Slack               │
├─────────────────────────────────────────┤
│                                         │
│  Enable PR surveys and weekly           │
│  leaderboards in Slack.                 │
│                                         │
│  [📱 Add to Slack]                      │
│                                         │
└─────────────────────────────────────────┘
```

After OAuth:

```
┌─────────────────────────────────────────┐
│          Configure Slack Bot            │
├─────────────────────────────────────────┤
│                                         │
│  Where should we post the weekly        │
│  leaderboard?                           │
│                                         │
│  Channel: [▼ #engineering         ]     │
│                                         │
│  When?                                  │
│  Day: [▼ Monday ]  Time: [▼ 09:00]     │
│                                         │
│  Features:                              │
│  ☑️ PR surveys via DM                   │
│  ☑️ Weekly leaderboard                  │
│  ☑️ Reveal messages (show guess result) │
│                                         │
│  [Continue →]                           │
└─────────────────────────────────────────┘
```

**Behind the scenes:**
- Match Slack users to GitHub/Jira users by email
- Send test message to verify bot works

---

## Step 6: Review User Mapping

```
┌─────────────────────────────────────────┐
│          Review Team Members            │
├─────────────────────────────────────────┤
│                                         │
│  ✅ Auto-matched: 38 users              │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ GitHub      │ Jira     │ Slack  │    │
│  ├─────────────┼──────────┼────────┤    │
│  │ @john-doe   │ ✓ john@  │ ✓ @john│    │
│  │ @jane-smith │ ✓ jane@  │ ✓ @jane│    │
│  │ @bob-wilson │ ✓ bob@   │ ✓ @bob │    │
│  └─────────────────────────────────┘    │
│                                         │
│  ⚠️ Needs attention: 4 users            │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ GitHub      │ Jira     │ Slack  │    │
│  ├─────────────┼──────────┼────────┤    │
│  │ @johnny-dev │ [Select▼]│ [▼]    │    │
│  │ @contractor1│ [Select▼]│ [▼]    │    │
│  │ @intern2024 │ [Select▼]│ [▼]    │    │
│  │ @bot-ci     │ [Exclude]│ -      │    │
│  └─────────────────────────────────┘    │
│                                         │
│  [Finish Setup →]                       │
└─────────────────────────────────────────┘
```

**Options for unmatched users:**
- Select from dropdown of unmatched Jira/Slack users
- Mark as "Exclude" (for bots, CI users)
- Leave unmatched (can fix later in settings)

---

## Step 7: First Sync

```
┌─────────────────────────────────────────┐
│       🚀 Setting Up Your Dashboard      │
├─────────────────────────────────────────┤
│                                         │
│  ✅ Database tables created             │
│  ✅ Users imported (42)                 │
│  ⏳ Syncing GitHub data...              │
│     └─ 847 PRs found, importing...      │
│  ⏳ Syncing Jira data...                │
│  ⏳ Syncing Copilot metrics...          │
│                                         │
│  This may take a few minutes for        │
│  larger teams. We'll email you when     │
│  it's ready!                            │
│                                         │
│  [View Dashboard] (loading...)          │
└─────────────────────────────────────────┘
```

After sync completes:

```
┌─────────────────────────────────────────┐
│            🎉 You're All Set!           │
├─────────────────────────────────────────┤
│                                         │
│  ✅ 847 PRs imported                    │
│  ✅ 1,234 Jira issues imported          │
│  ✅ 42 team members ready               │
│                                         │
│  What's next?                           │
│                                         │
│  1. Explore your dashboard              │
│  2. Wait for PR merges to see surveys   │
│  3. Check back Monday for leaderboard   │
│                                         │
│  [🚀 View Dashboard]                    │
│                                         │
└─────────────────────────────────────────┘
```

---

## Time Estimates

| Step | Time |
|------|------|
| Sign up | 1 min |
| Connect Supabase | 3 min (if already have account) |
| Connect GitHub | 2 min |
| Connect Jira | 2 min |
| Connect Slack | 2 min |
| Review mapping | 2-5 min |
| First sync | 2-10 min (background) |
| **Total** | **~15 minutes** |

---

## Error Handling

| Error | Resolution |
|-------|------------|
| Supabase connection fails | Show specific error, link to troubleshooting |
| GitHub OAuth denied | Explain required permissions, retry |
| No org access | Guide to request org admin approval |
| Jira connection fails | Allow skip, continue without Jira |
| User mapping conflicts | Allow manual resolution or skip |

---

## Post-Onboarding Checklist Email

Sent 24 hours after setup:

```
Subject: Your [Product] setup checklist

Hi {name},

Your dashboard is set up! Here's what to expect:

✅ Already done:
- {pr_count} PRs imported
- {user_count} team members synced

📊 Coming soon:
- PR surveys will start appearing when PRs are merged
- First leaderboard posts Monday at 9 AM

💡 Tips:
- Encourage your team to respond to surveys
- Check the AI Correlation dashboard after 2+ weeks of data

Questions? Reply to this email.

– The [Product] Team
```
