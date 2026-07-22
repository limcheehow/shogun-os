---
name: ecommerce-listing
description: "Product listing sync to Shopee/Lazada, image compliance checking, SEO title optimization, and inventory accuracy across platforms. Manages multi-channel e-commerce catalog."
version: 1.0.0
tags: [retail, ecommerce, listing, marketplace, catalog, shopee, lazada]
triggers:
  - "product listing"
  - "listing sync"
  - "ecommerce catalog"
  - "image compliance"
  - "seo title optimization"
  - "inventory accuracy"
  - "shopee listing"
  - "lazada listing"
---

# Ecommerce Listing

Product listing synchronization to Shopee and Lazada, image compliance auditing, SEO title optimization, and cross-platform inventory accuracy management.

## Overview

The Ecommerce Listing skill manages the end-to-end product catalog lifecycle across online marketplaces. It ensures product listings are consistent, compliant with platform requirements, SEO-optimized, and reflect accurate inventory levels.

| Function | Description | Frequency |
|----------|-------------|-----------|
| Listing Sync | Push product data to Shopee/Lazada APIs | Hourly |
| Image Compliance | Check image dimensions, size, and format | Per listing |
| SEO Optimization | Optimize titles and descriptions for search | Weekly |
| Inventory Sync | Reconcile stock levels across platforms | Real-time |
| Listing Health | Monitor active listings for errors | Daily |

## Usage

### Sync Listings to Marketplace

```
listing sync --platform shopee --sku SKU_ID [--full]
```

### Check Image Compliance

```
listing images --sku SKU_ID [--platform shopee]
```

### Optimize SEO Titles

```
listing optimize-seo --sku SKU_ID [--language en]
```

### Check Inventory Accuracy

```
listing inventory-check --platform lazada [--store STORE_ID]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LISTING_SHOPEE_API_KEY` | Shopee API key | — |
| `LISTING_SHOPEE_SHOP_ID` | Shopee shop identifier | — |
| `LISTING_LAZADA_API_KEY` | Lazada API key | — |
| `LISTING_LAZADA_SELLER_ID` | Lazada seller identifier | — |
| `LISTING_IMAGE_MIN_WIDTH` | Minimum image width in pixels | `500` |
| `LISTING_IMAGE_MIN_HEIGHT` | Minimum image height in pixels | `500` |
| `LISTING_IMAGE_MAX_SIZE_MB` | Maximum image file size in MB | `5` |
| `LISTING_SEO_TITLE_MAX_LENGTH` | Maximum title length in characters | `120` |
| `LISTING_INVENTORY_ACCURACY_TARGET` | Target inventory accuracy % | `99` |
| `LISTING_SYNC_INTERVAL` | Sync interval in minutes | `60` |
| `LISTING_DB_URL` | Database connection for product catalog | `postgresql://localhost:5432/catalog` |

### Platform Configuration (platforms.yaml)

```yaml
platforms:
  shopee:
    api_version: "v2"
    image_requirements:
      min_width: 500
      min_height: 500
      max_size_mb: 5
      formats: [jpg, jpeg, png]
      max_images: 9
  lazada:
    api_version: "v2"
    image_requirements:
      min_width: 500
      min_height: 500
      max_size_mb: 5
      formats: [jpg, jpeg, png]
      max_images: 8
```

## Scripts

### `scripts/sync-listings.py`

Pushes product data to connected marketplace platforms. Supports incremental and full sync modes with error logging.

### `scripts/image-compliance.py`

Audits product images against platform-specific requirements. Flags non-compliant images and suggests corrections.

### `scripts/seo-optimizer.py`

Analyzes listing titles and descriptions for SEO effectiveness. Generates optimized title suggestions based on search volume data.

### `scripts/inventory-reconciliation.py`

Compares inventory levels across all platforms and the warehouse management system. Flags discrepancies and generates adjustment requests.

## Related Skills

- [ecommerce-order-management](../ecommerce-order-management/SKILL.md) — Order fulfillment routing and returns
- [marketplace-analytics](../marketplace-analytics/SKILL.md) — Sales performance by platform
- [warehouse-distribution](../warehouse-distribution/SKILL.md) — Pick-pack-ship for ecommerce orders

## Pitfalls

- **API rate limits**: Marketplace APIs have strict rate limits. Implement retry with exponential backoff and avoid bulk updates during peak trading hours.
- **Image compliance drift**: Platform requirements change. Check image specs quarterly rather than assuming they're static.
- **Title truncation**: Different platforms render titles differently on mobile vs desktop. Test SEO titles on actual devices before full rollout.
- **Inventory race conditions**: Simultaneous orders on different platforms can cause overselling. Implement a centralized inventory buffer with 5-10% safety stock.
- **Category taxonomy changes**: Marketplaces occasionally restructure category trees. Monitor for category mapping errors during sync.