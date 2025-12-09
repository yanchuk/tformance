# Alpine.js Patterns

## Table of Contents
1. [Core Concepts](#core-concepts)
2. [State Management](#state-management)
3. [Event Handling](#event-handling)
4. [Common Components](#common-components)
5. [With HTMX](#with-htmx)
6. [Tips and Tricks](#tips-and-tricks)

## Core Concepts

Alpine.js adds reactivity to HTML with simple attributes.

**Key Directives:**
- `x-data` - Define reactive data
- `x-bind` or `:` - Bind attributes
- `x-on` or `@` - Handle events
- `x-show` - Toggle visibility
- `x-if` - Conditional rendering
- `x-for` - Loops
- `x-model` - Two-way binding
- `x-text` - Set text content

## State Management

### Local State

```html
<div x-data="{ count: 0 }">
  <button @click="count++">+</button>
  <span x-text="count"></span>
  <button @click="count--">-</button>
</div>
```

### Complex State

```html
<div x-data="{
    items: [],
    newItem: '',
    addItem() {
        if (this.newItem.trim()) {
            this.items.push(this.newItem);
            this.newItem = '';
        }
    },
    removeItem(index) {
        this.items.splice(index, 1);
    }
}">
  <input type="text" x-model="newItem" @keyup.enter="addItem">
  <button @click="addItem">Add</button>

  <ul>
    <template x-for="(item, index) in items" :key="index">
      <li>
        <span x-text="item"></span>
        <button @click="removeItem(index)">Remove</button>
      </li>
    </template>
  </ul>
</div>
```

### Shared State (Alpine Store)

```javascript
// In assets/js/app.js
document.addEventListener('alpine:init', () => {
    Alpine.store('notifications', {
        items: [],
        add(message, type = 'info') {
            const id = Date.now();
            this.items.push({ id, message, type });
            setTimeout(() => this.remove(id), 5000);
        },
        remove(id) {
            this.items = this.items.filter(item => item.id !== id);
        }
    });
});
```

```html
<!-- Using the store -->
<button @click="$store.notifications.add('Item saved!', 'success')">
  Save
</button>

<!-- Notification display -->
<div class="fixed top-4 right-4 space-y-2">
  <template x-for="notification in $store.notifications.items" :key="notification.id">
    <div class="alert" :class="'alert-' + notification.type">
      <span x-text="notification.message"></span>
      <button @click="$store.notifications.remove(notification.id)">×</button>
    </div>
  </template>
</div>
```

## Event Handling

### Click Events

```html
<button @click="open = true">Open</button>
<button @click="handleClick($event)">With Event</button>
<button @click.prevent="submitForm()">Prevent Default</button>
<button @click.stop="handleClick()">Stop Propagation</button>
<button @click.once="runOnce()">Run Once</button>
```

### Keyboard Events

```html
<input @keyup.enter="submit()">
<input @keyup.escape="cancel()">
<input @keydown.arrow-up="selectPrevious()">
<input @keydown.arrow-down="selectNext()">
<div @keydown.ctrl.s.prevent="save()">Ctrl+S to save</div>
```

### Window/Document Events

```html
<div x-data @keydown.escape.window="open = false">
  <!-- Closes on Escape key anywhere -->
</div>

<div x-data @click.away="open = false">
  <!-- Closes when clicking outside -->
</div>
```

## Common Components

### Dropdown

```html
<div x-data="{ open: false }" class="relative">
  <button @click="open = !open" class="btn">
    Options
    <svg :class="{ 'rotate-180': open }" class="w-4 h-4 transition-transform">
      <!-- chevron icon -->
    </svg>
  </button>

  <div x-show="open"
       x-transition:enter="transition ease-out duration-100"
       x-transition:enter-start="opacity-0 scale-95"
       x-transition:enter-end="opacity-100 scale-100"
       x-transition:leave="transition ease-in duration-75"
       x-transition:leave-start="opacity-100 scale-100"
       x-transition:leave-end="opacity-0 scale-95"
       @click.away="open = false"
       class="absolute right-0 mt-2 w-48 bg-base-100 rounded-lg shadow-lg z-10">
    <a href="#" class="block px-4 py-2 hover:bg-base-200">Option 1</a>
    <a href="#" class="block px-4 py-2 hover:bg-base-200">Option 2</a>
    <hr class="my-1">
    <a href="#" class="block px-4 py-2 text-error hover:bg-base-200">Delete</a>
  </div>
</div>
```

### Tabs

```html
<div x-data="{ activeTab: 'overview' }">
  <div class="tabs tabs-boxed">
    <button @click="activeTab = 'overview'"
            :class="{ 'tab-active': activeTab === 'overview' }"
            class="tab">
      Overview
    </button>
    <button @click="activeTab = 'details'"
            :class="{ 'tab-active': activeTab === 'details' }"
            class="tab">
      Details
    </button>
    <button @click="activeTab = 'settings'"
            :class="{ 'tab-active': activeTab === 'settings' }"
            class="tab">
      Settings
    </button>
  </div>

  <div x-show="activeTab === 'overview'" class="py-4">
    Overview content
  </div>
  <div x-show="activeTab === 'details'" class="py-4">
    Details content
  </div>
  <div x-show="activeTab === 'settings'" class="py-4">
    Settings content
  </div>
</div>
```

### Modal

```html
<div x-data="{ open: false }">
  <button @click="open = true" class="btn">Open Modal</button>

  <div x-show="open"
       x-transition:enter="ease-out duration-300"
       x-transition:enter-start="opacity-0"
       x-transition:enter-end="opacity-100"
       x-transition:leave="ease-in duration-200"
       x-transition:leave-start="opacity-100"
       x-transition:leave-end="opacity-0"
       class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">

    <div @click.away="open = false"
         x-transition:enter="ease-out duration-300"
         x-transition:enter-start="opacity-0 scale-95"
         x-transition:enter-end="opacity-100 scale-100"
         class="bg-base-100 rounded-lg shadow-xl max-w-md w-full mx-4">
      <div class="p-6">
        <h3 class="text-lg font-bold">Modal Title</h3>
        <p class="py-4">Modal content here</p>
        <div class="flex justify-end gap-2">
          <button @click="open = false" class="btn">Cancel</button>
          <button @click="submit(); open = false" class="btn btn-primary">Confirm</button>
        </div>
      </div>
    </div>
  </div>
</div>
```

### Accordion

```html
<div x-data="{ openSection: null }">
  <div class="border rounded-lg divide-y">
    <div>
      <button @click="openSection = openSection === 1 ? null : 1"
              class="w-full px-4 py-3 text-left flex justify-between items-center">
        <span>Section 1</span>
        <span x-text="openSection === 1 ? '−' : '+'"></span>
      </button>
      <div x-show="openSection === 1" x-collapse class="px-4 pb-3">
        Section 1 content
      </div>
    </div>

    <div>
      <button @click="openSection = openSection === 2 ? null : 2"
              class="w-full px-4 py-3 text-left flex justify-between items-center">
        <span>Section 2</span>
        <span x-text="openSection === 2 ? '−' : '+'"></span>
      </button>
      <div x-show="openSection === 2" x-collapse class="px-4 pb-3">
        Section 2 content
      </div>
    </div>
  </div>
</div>
```

## With HTMX

### Form Submission State

```html
<form x-data="{ submitting: false }"
      @htmx:before-request="submitting = true"
      @htmx:after-request="submitting = false"
      hx-post="{% url 'myapp:create' team_slug=request.team.slug %}"
      hx-target="#result">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit" :disabled="submitting" class="btn btn-primary">
    <span x-show="!submitting">Save</span>
    <span x-show="submitting" class="loading loading-spinner loading-sm"></span>
  </button>
</form>
```

### Responding to HTMX Events

```html
<div x-data="{ message: '' }"
     @htmx:response-error="message = 'An error occurred'"
     @htmx:after-request="setTimeout(() => message = '', 3000)">
  <div x-show="message" x-text="message" class="alert alert-error"></div>
  <!-- HTMX content here -->
</div>
```

## Tips and Tricks

### Initialize with Server Data

```html
<div x-data="{ items: {{ items_json|safe }} }">
  <!-- Use items from Django -->
</div>
```

### Computed Properties

```html
<div x-data="{
    firstName: '',
    lastName: '',
    get fullName() {
        return `${this.firstName} ${this.lastName}`.trim();
    }
}">
  <input x-model="firstName" placeholder="First">
  <input x-model="lastName" placeholder="Last">
  <p>Full name: <span x-text="fullName"></span></p>
</div>
```

### Watch for Changes

```html
<div x-data="{ search: '' }"
     x-init="$watch('search', value => console.log('Search changed:', value))">
  <input x-model="search">
</div>
```
