---
name: htmx-alpine-flowbite-guidelines
description: Frontend patterns for Django templates using HTMX, Alpine.js, Flowbite, DaisyUI, and Tailwind CSS. Use when creating templates, components, modals, forms, or any frontend UI. Covers HTMX for server interactions, Alpine.js for client-side state, and Flowbite/DaisyUI for styling.
---

# HTMX + Alpine.js + Flowbite Guidelines

## Purpose

Establish consistent frontend patterns for tformance using Django templates enhanced with HTMX, Alpine.js, Flowbite, and DaisyUI/Tailwind.

## When to Use This Skill

Automatically activates when working on:
- Django templates (.html files)
- HTMX interactions (hx-get, hx-post, etc.)
- Alpine.js components (x-data, x-on, etc.)
- Flowbite or DaisyUI components
- Tailwind CSS styling

## Technology Stack

| Technology | Purpose |
|------------|---------|
| **HTMX** | Server interactions without full page reload |
| **Alpine.js** | Client-side interactivity and state |
| **Flowbite** | UI components library |
| **DaisyUI** | Tailwind component classes |
| **Tailwind CSS** | Utility-first styling |
| **Vite** | Asset bundling |

## Quick Decision Guide

| Need | Use |
|------|-----|
| Fetch data from server | HTMX |
| Submit form to server | HTMX |
| Toggle dropdown (no server) | Alpine.js |
| Form validation (client-side) | Alpine.js |
| Complex component | Flowbite |
| Simple button/card | DaisyUI |

## HTMX Patterns

### Basic Request

```html
<!-- GET request -->
<button hx-get="{% url 'myapp:data' team_slug=request.team.slug %}"
        hx-target="#result"
        hx-swap="innerHTML">
  Load Data
</button>
<div id="result"></div>
```

### Form Submission

```html
<form hx-post="{% url 'myapp:create' team_slug=request.team.slug %}"
      hx-target="#form-container"
      hx-swap="outerHTML">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit" class="btn btn-primary">Save</button>
</form>
```

### Loading States

```html
<button hx-get="/api/data"
        hx-target="#result"
        hx-indicator="#loading">
  <span id="loading" class="htmx-indicator loading loading-spinner"></span>
  Load Data
</button>
```

### Trigger Events

```html
<!-- Trigger on input change with debounce -->
<input type="text"
       name="search"
       hx-get="{% url 'myapp:search' team_slug=request.team.slug %}"
       hx-trigger="keyup changed delay:300ms"
       hx-target="#results">
```

## Alpine.js Patterns

### Basic Component

```html
<div x-data="{ open: false }">
  <button @click="open = !open" class="btn">
    Toggle
  </button>
  <div x-show="open" x-transition>
    Content here
  </div>
</div>
```

### Form State

```html
<form x-data="{ submitting: false }"
      @submit="submitting = true"
      hx-post="/submit">
  <button type="submit"
          :disabled="submitting"
          :class="{ 'loading': submitting }">
    <span x-show="!submitting">Submit</span>
    <span x-show="submitting">Saving...</span>
  </button>
</form>
```

### Dropdown

```html
<div x-data="{ open: false }" class="relative">
  <button @click="open = !open" class="btn">
    Options
  </button>
  <div x-show="open"
       @click.away="open = false"
       x-transition
       class="absolute mt-2 bg-base-100 shadow-lg rounded-lg">
    <a href="#" class="block px-4 py-2 hover:bg-base-200">Option 1</a>
    <a href="#" class="block px-4 py-2 hover:bg-base-200">Option 2</a>
  </div>
</div>
```

## Component Patterns

### Card (DaisyUI)

```html
<div class="card bg-base-100 shadow-xl">
  <div class="card-body">
    <h2 class="card-title">{{ project.name }}</h2>
    <p>{{ project.description }}</p>
    <div class="card-actions justify-end">
      <a href="{% url 'projects:detail' team_slug=request.team.slug project_id=project.id %}"
         class="btn btn-primary">View</a>
    </div>
  </div>
</div>
```

### Modal (Flowbite + HTMX)

```html
<!-- Trigger button -->
<button hx-get="{% url 'myapp:modal' team_slug=request.team.slug %}"
        hx-target="#modal-container"
        hx-swap="innerHTML"
        data-modal-target="modal"
        data-modal-toggle="modal"
        class="btn btn-primary">
  Open Modal
</button>

<!-- Modal container -->
<div id="modal-container"></div>

<!-- Modal partial template (myapp/_modal.html) -->
<div id="modal" class="modal modal-open">
  <div class="modal-box">
    <h3 class="font-bold text-lg">Modal Title</h3>
    <p class="py-4">Modal content here</p>
    <div class="modal-action">
      <button @click="$dispatch('close-modal')" class="btn">Close</button>
    </div>
  </div>
  <div class="modal-backdrop" @click="$dispatch('close-modal')"></div>
</div>
```

### Table with Sorting

```html
<table class="table">
  <thead>
    <tr>
      <th hx-get="{% url 'myapp:list' team_slug=request.team.slug %}?sort=name"
          hx-target="#table-body"
          class="cursor-pointer hover:bg-base-200">
        Name
      </th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody id="table-body">
    {% include "myapp/_table_rows.html" %}
  </tbody>
</table>
```

## Template Structure

### Base Template Pattern

```html
<!-- templates/base.html -->
{% load django_vite %}
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  {% vite_asset 'assets/styles/app.css' %}
</head>
<body>
  {% include "components/navbar.html" %}

  <main class="container mx-auto px-4 py-8">
    {% block content %}{% endblock %}
  </main>

  {% vite_asset 'assets/js/app.js' %}
</body>
</html>
```

### Component Template

```html
<!-- templates/components/project_card.html -->
<div class="card bg-base-100 shadow-xl">
  <div class="card-body">
    <h2 class="card-title">{{ project.name }}</h2>
    <p>{{ project.description|truncatewords:20 }}</p>
    <div class="card-actions justify-end">
      <a href="{{ project.get_absolute_url }}" class="btn btn-primary btn-sm">
        View Details
      </a>
    </div>
  </div>
</div>
```

### Using Components

```html
{% for project in projects %}
  {% include "components/project_card.html" with project=project %}
{% endfor %}
```

## Anti-Patterns to Avoid

❌ Inline `<script>` tags (use Alpine.js or asset files)
❌ Direct fetch/axios calls (use HTMX or generated API client)
❌ Heavy JavaScript frameworks (React/Vue) for simple interactions
❌ Custom CSS when DaisyUI/Tailwind classes exist
❌ HTMX for purely client-side interactions (use Alpine.js)

## Resource Files

### [resources/htmx-patterns.md](resources/htmx-patterns.md)
Complete HTMX patterns and examples

### [resources/alpine-patterns.md](resources/alpine-patterns.md)
Alpine.js component patterns

### [resources/flowbite-components.md](resources/flowbite-components.md)
Flowbite component integration

### [resources/styling-guide.md](resources/styling-guide.md)
Tailwind/DaisyUI styling conventions

---

**Skill Status**: COMPLETE
**Line Count**: < 500
**Progressive Disclosure**: Resource files for detailed information
