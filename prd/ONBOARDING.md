# Tformance Onboarding Flow

> Part of [PRD Documentation](README.md)

## Overview

Goal: Get a CTO from sign-up to seeing their first dashboard in <10 minutes.

**Key principle:** GitHub org connection auto-discovers team members and creates the team. No manual setup required.

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
│  ☑ I agree to the Terms and Conditions  │
│                                         │
│  [Create Account]                       │
└─────────────────────────────────────────┘
```

**No team name required** - team is created from GitHub org in next step.

---

## Step 2: Connect GitHub (Team Discovery)

```
┌─────────────────────────────────────────┐
│        Connect Your GitHub Org          │
├─────────────────────────────────────────┤
│                                         │
│  We'll import your team from GitHub     │
│  and start tracking engineering metrics.│
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
│  [Continue →]                           │
└─────────────────────────────────────────┘
```

**Behind the scenes:**
- Create Team from org name
- Fetch org members via GitHub API
- Create TeamMember records with GitHub IDs
- Set up org-level webhook for new members

---

## Step 3: Select Repositories

```
┌─────────────────────────────────────────┐
│       Select Repositories to Track      │
├─────────────────────────────────────────┤
│                                         │
│  Which repositories should we analyze?  │
│                                         │
│  ☑️ acme-corp/main-app                  │
│  ☑️ acme-corp/api-service               │
│  ☑️ acme-corp/mobile-app                │
│  ☐ acme-corp/docs (documentation)       │
│  ☐ acme-corp/infrastructure (ops)       │
│                                         │
│  💡 Tip: Select repos where your team   │
│     actively creates PRs                │
│                                         │
│  [Continue →]                           │
└─────────────────────────────────────────┘
```

**Behind the scenes:**
- Set up webhooks for selected repos
- Queue historical data sync (last 90 days)

---

## Step 4: Connect Jira (Optional)

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
- Queue historical sync

---

## Step 5: Connect Slack (Optional)

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
│  [Skip for now →]                       │
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
- Match Slack users to GitHub users by email
- Send test message to verify bot works

---

## Step 6: Initial Sync

```
┌─────────────────────────────────────────┐
│       🚀 Setting Up Your Dashboard      │
├─────────────────────────────────────────┤
│                                         │
│  ✅ Team created (42 members)           │
│  ✅ Repositories configured (3)         │
│  ⏳ Syncing GitHub data...              │
│     └─ 847 PRs found, importing...      │
│  ⏳ Syncing Jira data...                │
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
| Connect GitHub | 2 min |
| Select repositories | 1 min |
| Connect Jira (optional) | 2 min |
| Connect Slack (optional) | 2 min |
| Initial sync | 2-5 min (background) |
| **Total** | **~10 minutes** |

---

## Error Handling

| Error | Resolution |
|-------|------------|
| GitHub OAuth denied | Explain required permissions, retry |
| No org access | Guide to request org admin approval |
| No organizations found | Suggest creating org or check account |
| Jira connection fails | Allow skip, continue without Jira |
| Slack connection fails | Allow skip, continue without Slack |

---

## Post-Onboarding

### Welcome Email (Sent immediately)

```
Subject: Welcome to Tformance - Your dashboard is ready!

Hi {name},

Your team "{team_name}" is set up and syncing data.

📊 View your dashboard: {dashboard_url}

What's happening now:
- Importing {pr_count} PRs from the last 90 days
- Syncing {issue_count} Jira issues
- Matching {member_count} team members

We'll send another email once the initial sync is complete.

Questions? Reply to this email.

– The Tformance Team
```

### Sync Complete Email (Sent when done)

```
Subject: Your Tformance dashboard is ready!

Hi {name},

Your dashboard is fully loaded with data!

✅ {pr_count} PRs imported
✅ {issue_count} Jira issues synced
✅ {member_count} team members matched

🚀 View Dashboard: {dashboard_url}

What's next:
- PR surveys start automatically when PRs are merged
- First leaderboard posts {next_monday} at 9 AM
- Check the AI Correlation view after collecting survey data

– The Tformance Team
```
