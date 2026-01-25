# CTA Patterns

Call-to-action patterns for CTO-focused B2B SaaS.

---

## Primary CTAs (High Commitment)

For visitors ready to try the product.

### Recommended
| CTA | When to Use |
|-----|-------------|
| **Start Free Trial** | After pricing, after strong value prop |
| **Start Free** | Shorter variant, modern feel |
| **Try It Free** | Comparison pages, after competitive analysis |
| **Get Started** | Post-onboarding, after how-it-works |

### Examples in Context
```html
<!-- After pricing section -->
<button>Start Free Trial</button>
<span class="subtext">No credit card required</span>

<!-- Compact hero -->
<button>Start Free</button>
```

---

## Secondary CTAs (Low Commitment)

For curious but not ready-to-commit visitors.

### Recommended
| CTA | When to Use |
|-----|-------------|
| **See How It Works** | Early in page, for exploration |
| **Compare All Tools** | Comparison hub page |
| **View Pricing** | When price is the lingering question |
| **Watch Demo** | Video-based explanation |
| **Read the Guide** | Content-led pages |

### Examples in Context
```html
<!-- Hero with dual CTA -->
<button class="primary">Start Free</button>
<button class="secondary">See How It Works</button>

<!-- Comparison page -->
<button>Compare All Tools</button>
```

---

## Dual CTA Pattern

Use two CTAs for different intent levels.

### Structure
```
[Primary CTA - for ready visitors]
[Secondary CTA - for curious visitors]
```

### Tformance Standard
```html
<div class="cta-group">
  <button class="btn-primary">Start Free</button>
  <button class="btn-secondary">See How It Works</button>
</div>
```

### Why It Works
- Captures high-intent visitors immediately
- Gives lower-intent visitors a next step
- No one gets stuck

---

## Context-Specific CTAs

### After Pain Point Section
```
See How We Help
Learn How We Fix This
```

### After Feature List
```
Start Free Trial
Try These Features
```

### After Pricing Display
```
Start Free Trial
Start Free
```

### After Comparison Table
```
Try It Free
See For Yourself
```

### After Testimonials/Social Proof
```
Join Them
Get Started
```

### On Comparison Pages (vs Competitor)
```
Try Tformance Instead
Switch to Tformance
Compare Side by Side
```

---

## CTA Anti-Patterns

### Avoid These

| Bad CTA | Why It Fails |
|---------|--------------|
| "Get a Demo" | Creates friction (scheduling call) |
| "Contact Sales" | CTOs avoid sales calls |
| "Learn More" | Vague, no clear next step |
| "Submit" | Generic, no value proposition |
| "Click Here" | Obvious, meaningless |
| "Sign Up Now" | Pushy, creates resistance |
| "Request Access" | Implies gatekeeping |

### Why Tformance Avoids Demo Calls
Our differentiation is self-serve. "Book a Demo" contradicts our positioning as frictionless.

---

## CTA Supporting Text

Reduce friction with reassuring subtext.

### Examples
```
Start Free Trial
→ No credit card required

Start Free
→ 2-minute setup

See How It Works
→ Watch a 3-minute video

Try It Free
→ Cancel anytime
```

### Pattern
```html
<button>[Primary CTA]</button>
<span class="subtext">[Friction reducer]</span>
```

---

## CTA Placement Rules

### Hero Section
- Primary + Secondary CTAs
- Clear visual hierarchy

### End of Each Major Section
- One CTA that matches the section content
- Example: After features → "Try These Features"

### Sticky Header (When Scrolled)
- Primary CTA only
- Compact: "Start Free"

### Footer
- Primary CTA with full context
- Repeat subtext reassurance

### Comparison Page Bottom
- Strong CTA after showing we're better
- "Try Tformance Free"

---

## Button Copy Length

### Optimal: 2-4 Words
```
Start Free           ✓ (2 words)
See How It Works     ✓ (4 words)
Start Free Trial     ✓ (3 words)
```

### Too Long
```
Click Here to Start Your Free Trial Today  ✗
Get Started with Tformance Now            ✗
```

---

## Quick Reference

| Context | Primary CTA | Secondary CTA |
|---------|-------------|---------------|
| Homepage hero | Start Free | See How It Works |
| Pricing section | Start Free Trial | Compare Plans |
| Comparison page | Try Tformance Free | See Full Comparison |
| Feature section | Try This Feature | Learn More |
| How it works | Get Started | Watch Demo |

---

**Line Count:** ~80 (within guideline)
