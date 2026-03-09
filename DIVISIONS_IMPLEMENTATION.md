# Kitchen Division – Implementation Guide (Instamart-style)

This document describes what was implemented in the **backend** and what you need to do in the **admin panel** and **mobile app** to support the Kitchen division (like Instamart in Swiggy).

---

## Backend summary

- **Division model**: `divisions` table with `id`, `name`, `slug`, `description`, `icon`, `image_url`, `display_order`, `is_active`.
- **Seeded divisions**: **Grocery** (slug `default`) and **Kitchen** (slug `kitchen`). Existing categories/products with `division_id = NULL` are treated as **Grocery**.
- **Category & Product**: Optional `division_id` (FK to `divisions`). `NULL` = default (Grocery).
- **Cart**: Each cart item has `division_id`. A user’s cart can only contain items from **one** division (Grocery or Kitchen). Adding a product from another division returns 400 with a message to clear cart or switch tab.
- **Order**: `division_id` is set from the first product in the order so you can filter/display orders by division.

### New/updated APIs

| API | Description |
|-----|-------------|
| `GET /api/v1/divisions` | List active divisions (for app tabs). |
| `GET /api/v1/categories?division_slug=kitchen` | Categories for Kitchen; omit for Grocery. |
| `GET /api/v1/categories/{id}/products?division_slug=kitchen` | Products in a category (division context). |
| `GET /api/v1/products?division_slug=kitchen` | Products filtered by division. |
| `GET /api/v1/cart?division_slug=kitchen` | Cart items for that division only. |
| `POST /api/v1/cart` | Add to cart; enforces single division per cart. |
| `POST /api/v1/orders` | Order gets `division_id` from first product. |

### Admin APIs

| API | Description |
|-----|-------------|
| `GET /admin/divisions` | List all divisions. |
| `GET /admin/divisions/{id}` | Get one division. |
| `POST /admin/divisions` | Create division (body: name, slug, description, icon, image_url, display_order, is_active). |
| `PATCH /admin/divisions/{id}` | Update division. |
| Categories | Create/update category with optional `division_id`. |
| Products | Create/update product with optional `divisionId` / `division_id` (form or JSON). |

---

## Admin panel implementation

1. **Divisions CRUD**
   - **List**: Call `GET /admin/divisions` and show a table (name, slug, display order, active, actions).
   - **Create**: Form with name, slug, description, icon, image URL, display order, is active → `POST /admin/divisions`.
   - **Edit**: Pre-fill from `GET /admin/divisions/{id}`, save with `PATCH /admin/divisions/{id}`.
   - Optional: reorder divisions (update `display_order` via PATCH).

2. **Categories**
   - **List**: Tree already includes `divisionId` in each node. Optionally:
     - Add a filter dropdown “Division: All / Grocery / Kitchen” and filter the tree (or filter in UI by `divisionId`).
   - **Create category**: Add a “Division” dropdown (source: `GET /admin/divisions`). Send `division_id` (UUID) in the create payload. Leave empty for Grocery.
   - **Edit category**: Show and allow changing `divisionId`; send `division_id` in update.

3. **Products**
   - **Create product**: Add “Division” dropdown (from `GET /admin/divisions`). Send `divisionId` or `division_id` in form/JSON. Empty = Grocery.
   - **Edit product**: Show and edit `division_id`; backend already accepts `divisionId` / `division_id` in update.
   - **List products**: Optional filter “Division: All / Grocery / Kitchen” (filter by `division_id` or division slug if you add that to the list API).

4. **Orders (optional)**
   - Order list/detail can show division (e.g. “Kitchen” / “Grocery”) using `order.division_id` and a small division lookup or name from `GET /admin/divisions`. Filter orders by division if needed.

5. **UI copy**
   - Use “Grocery” for default (slug `default`) and “Kitchen” for the new vertical so it’s clear in the admin.

---

## Mobile app implementation

1. **Home / navigation (Instamart-style)**
   - On app load (or home), call `GET /api/v1/divisions` and show **tabs** (e.g. “Grocery”, “Kitchen”).
   - Store current division in app state (e.g. `currentDivisionSlug`: `null` or `"default"` = Grocery, `"kitchen"` = Kitchen).
   - When user switches tab, set `currentDivisionSlug` and reload categories (and optionally products) for that division.

2. **Categories**
   - For the selected tab, call:
     - Grocery: `GET /api/v1/categories` (no query) or `GET /api/v1/categories?division_slug=default`.
     - Kitchen: `GET /api/v1/categories?division_slug=kitchen`.
   - Show category tree/list only for the current division.

3. **Products**
   - When listing products (e.g. “All products” or search), pass division:
     - `GET /api/v1/products?division_slug=kitchen` (or omit for Grocery).
   - When listing products by category, pass division if your backend expects it:
     - `GET /api/v1/categories/{category_id}/products?division_slug=kitchen`.

4. **Cart**
   - **Single cart, division-specific view**: Call cart with the current tab’s division so the user sees only that division’s items:
     - Grocery tab: `GET /api/v1/cart` or `GET /api/v1/cart?division_slug=default`.
     - Kitchen tab: `GET /api/v1/cart?division_slug=kitchen`.
   - **Add to cart**: When user adds a product (from Kitchen or Grocery), `POST /api/v1/cart` as today. If the cart already has items from the other division, the API returns 400 with a message like “Cart can only contain items from one division (Grocery or Kitchen). Clear cart or switch tab to add from the other.” Show this message and optionally offer “Clear cart and add this” (clear cart then retry add).
   - **Cart badge**: Either show one total count (all items) or two (e.g. “Grocery 3, Kitchen 0”); for the latter, call cart twice with `division_slug=default` and `division_slug=kitchen` and use `summary.item_count` for each.

5. **Checkout & orders**
   - Checkout flow is unchanged; pass the same cart items (all from one division once the rule is enforced). Order will get the correct `division_id` from the first product.
   - In “My orders”, you can show a division label (e.g. “Kitchen” / “Grocery”) using `order.division_id` and a small local mapping or a divisions list cached from `GET /api/v1/divisions`.

6. **Deep links / state**
   - If you support deep links (e.g. open app on Kitchen tab), encode division in the URL (e.g. `?division=kitchen`) and set `currentDivisionSlug` and load categories/products for that division.

---

## Migration

Run:

```bash
alembic upgrade head
```

This creates the `divisions` table, adds `division_id` to `categories`, `products`, `carts`, and `orders`, and seeds **Grocery** and **Kitchen**. Existing data stays as Grocery (`division_id` NULL).

---

## Optional enhancements

- **Admin**: Filter category tree by division; filter product list by division.
- **Mobile**: “Clear cart and add from Kitchen” when user tries to add a Kitchen product and cart has Grocery items (or vice versa).
- **Analytics**: Use `order.division_id` and `division` name for division-wise sales reports.
