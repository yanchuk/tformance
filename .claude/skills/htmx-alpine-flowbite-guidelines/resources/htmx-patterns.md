# HTMX Patterns

## Table of Contents
1. [Core Concepts](#core-concepts)
2. [Request Patterns](#request-patterns)
3. [Response Patterns](#response-patterns)
4. [Forms](#forms)
5. [Lists and Tables](#lists-and-tables)
6. [Advanced Patterns](#advanced-patterns)

## Core Concepts

HTMX extends HTML with attributes to make AJAX requests and update the DOM.

**Key Attributes:**
- `hx-get`, `hx-post`, `hx-put`, `hx-delete` - HTTP methods
- `hx-target` - Where to put the response
- `hx-swap` - How to swap content
- `hx-trigger` - When to trigger the request

## Request Patterns

### GET Request

```html
<!-- Load content -->
<button hx-get="{% url 'myapp:data' team_slug=request.team.slug %}"
        hx-target="#content">
  Load
</button>
<div id="content"></div>
```

### POST Request

```html
<!-- Submit action -->
<button hx-post="{% url 'myapp:action' team_slug=request.team.slug %}"
        hx-target="#result">
  Submit
</button>
```

### DELETE Request

```html
<!-- Delete item -->
<button hx-delete="{% url 'myapp:delete' team_slug=request.team.slug item_id=item.id %}"
        hx-confirm="Are you sure?"
        hx-target="closest tr"
        hx-swap="outerHTML">
  Delete
</button>
```

### With Parameters

```html
<!-- Include values -->
<button hx-post="/action"
        hx-vals='{"item_id": "{{ item.id }}", "action": "archive"}'>
  Archive
</button>
```

## Response Patterns

### Swap Modes

```html
<!-- Replace inner HTML (default) -->
<div hx-get="/data" hx-target="#target" hx-swap="innerHTML">

<!-- Replace entire element -->
<div hx-get="/data" hx-target="#target" hx-swap="outerHTML">

<!-- Insert before target -->
<div hx-get="/data" hx-target="#target" hx-swap="beforebegin">

<!-- Insert after target -->
<div hx-get="/data" hx-target="#target" hx-swap="afterend">

<!-- Append to target -->
<div hx-get="/data" hx-target="#target" hx-swap="beforeend">

<!-- Delete target -->
<div hx-get="/data" hx-swap="delete">
```

### Django View for HTMX

```python
@login_and_team_required
def item_list(request, team_slug):
    items = Item.objects.for_team(request.team)

    # Return partial for HTMX, full page otherwise
    if request.headers.get("HX-Request"):
        return render(request, "myapp/_item_list.html", {"items": items})

    return render(request, "myapp/item_list.html", {"items": items})
```

### Out-of-Band Updates

Update multiple parts of the page:

```html
<!-- In your response template -->
<div id="main-content">
  Updated main content
</div>

<div id="notification" hx-swap-oob="true">
  <div class="alert alert-success">Item saved!</div>
</div>
```

## Forms

### Basic Form

```html
<form hx-post="{% url 'myapp:create' team_slug=request.team.slug %}"
      hx-target="#form-container"
      hx-swap="outerHTML">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit" class="btn btn-primary">Save</button>
</form>
```

### Form with Validation Errors

```python
# View
@login_and_team_required
def create_item(request, team_slug):
    if request.method == "POST":
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.team = request.team
            item.save()
            # Return success partial
            return render(request, "myapp/_item_created.html", {"item": item})
    else:
        form = ItemForm()

    return render(request, "myapp/_item_form.html", {"form": form})
```

```html
<!-- _item_form.html -->
<div id="form-container">
  <form hx-post="{% url 'myapp:create' team_slug=request.team.slug %}"
        hx-target="#form-container"
        hx-swap="outerHTML">
    {% csrf_token %}
    {% for field in form %}
      <div class="form-control">
        <label class="label">{{ field.label }}</label>
        {{ field }}
        {% if field.errors %}
          <span class="text-error text-sm">{{ field.errors.0 }}</span>
        {% endif %}
      </div>
    {% endfor %}
    <button type="submit" class="btn btn-primary">Save</button>
  </form>
</div>
```

### Inline Edit

```html
<!-- Display mode -->
<div id="item-{{ item.id }}" class="flex items-center gap-2">
  <span>{{ item.name }}</span>
  <button hx-get="{% url 'myapp:edit_form' team_slug=request.team.slug item_id=item.id %}"
          hx-target="#item-{{ item.id }}"
          hx-swap="outerHTML"
          class="btn btn-xs">
    Edit
  </button>
</div>

<!-- Edit mode (_edit_form.html) -->
<form id="item-{{ item.id }}"
      hx-post="{% url 'myapp:update' team_slug=request.team.slug item_id=item.id %}"
      hx-target="#item-{{ item.id }}"
      hx-swap="outerHTML"
      class="flex items-center gap-2">
  {% csrf_token %}
  <input type="text" name="name" value="{{ item.name }}" class="input input-bordered input-sm">
  <button type="submit" class="btn btn-xs btn-success">Save</button>
  <button type="button"
          hx-get="{% url 'myapp:item_display' team_slug=request.team.slug item_id=item.id %}"
          hx-target="#item-{{ item.id }}"
          hx-swap="outerHTML"
          class="btn btn-xs">
    Cancel
  </button>
</form>
```

## Lists and Tables

### Infinite Scroll

```html
<div id="items">
  {% for item in items %}
    {% include "myapp/_item.html" %}
  {% endfor %}

  {% if has_more %}
    <div hx-get="{% url 'myapp:list' team_slug=request.team.slug %}?page={{ next_page }}"
         hx-trigger="revealed"
         hx-swap="outerHTML">
      <div class="loading loading-spinner"></div>
    </div>
  {% endif %}
</div>
```

### Search with Debounce

```html
<input type="search"
       name="q"
       placeholder="Search..."
       hx-get="{% url 'myapp:search' team_slug=request.team.slug %}"
       hx-trigger="keyup changed delay:300ms, search"
       hx-target="#results"
       class="input input-bordered">

<div id="results">
  {% include "myapp/_results.html" %}
</div>
```

### Sortable Table Headers

```html
<table class="table">
  <thead>
    <tr>
      <th hx-get="{% url 'myapp:list' team_slug=request.team.slug %}?sort=name"
          hx-target="#table-body"
          hx-swap="innerHTML"
          class="cursor-pointer hover:bg-base-200">
        Name {% if sort == 'name' %}↑{% endif %}
      </th>
      <th hx-get="{% url 'myapp:list' team_slug=request.team.slug %}?sort=-created_at"
          hx-target="#table-body"
          class="cursor-pointer hover:bg-base-200">
        Date
      </th>
    </tr>
  </thead>
  <tbody id="table-body">
    {% include "myapp/_table_rows.html" %}
  </tbody>
</table>
```

## Advanced Patterns

### Loading Indicators

```html
<button hx-get="/data"
        hx-target="#result"
        hx-indicator="#spinner"
        class="btn">
  Load Data
  <span id="spinner" class="htmx-indicator loading loading-spinner loading-sm"></span>
</button>
```

Add CSS:
```css
.htmx-indicator {
  display: none;
}
.htmx-request .htmx-indicator {
  display: inline;
}
```

### Polling

```html
<!-- Poll every 10 seconds -->
<div hx-get="{% url 'myapp:status' team_slug=request.team.slug %}"
     hx-trigger="every 10s"
     hx-target="this"
     hx-swap="innerHTML">
  {% include "myapp/_status.html" %}
</div>
```

### Server-Sent Events

```html
<div hx-ext="sse"
     sse-connect="/events"
     sse-swap="message">
  Waiting for updates...
</div>
```

### Response Headers

```python
# Django view returning HTMX headers
from django.http import HttpResponse

@login_and_team_required
def delete_item(request, team_slug, item_id):
    item = get_object_or_404(Item.objects.for_team(request.team), id=item_id)
    item.delete()

    response = HttpResponse()
    # Trigger client-side event
    response["HX-Trigger"] = "itemDeleted"
    # Or redirect
    response["HX-Redirect"] = reverse("myapp:list", kwargs={"team_slug": team_slug})
    return response
```
