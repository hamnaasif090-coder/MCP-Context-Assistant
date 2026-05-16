---
title: Product FAQ & Troubleshooting
category: Product
author: Product Team
last_updated: 2024-03-01
---

# Product FAQ & Troubleshooting

## General Questions

### What does our product do?
Our platform provides AI-powered analytics for e-commerce businesses. It automatically ingests sales data, identifies trends, and provides actionable recommendations to increase revenue.

### Who is the target customer?
Mid-market e-commerce companies with $1M–$50M annual revenue. Primarily direct-to-consumer brands in fashion, beauty, and home goods.

### What integrations are supported?
- **E-commerce**: Shopify, WooCommerce, Magento, BigCommerce
- **Analytics**: Google Analytics 4, Mixpanel, Amplitude
- **Advertising**: Meta Ads, Google Ads, TikTok Ads
- **ERP/Finance**: QuickBooks, Xero, NetSuite
- **Email**: Klaviyo, Mailchimp, Sendgrid

## Pricing

### What are the pricing tiers?

| Plan | Price | MAU Limit | Features |
|------|-------|-----------|----------|
| Starter | $299/mo | 50K | Core analytics, 3 integrations |
| Growth | $799/mo | 250K | All integrations, AI recommendations |
| Scale | $1,999/mo | 1M | Custom models, dedicated support |
| Enterprise | Custom | Unlimited | SLA, SSO, custom contracts |

### Is there a free trial?
Yes — 14-day free trial, no credit card required. Access to all Growth features.

### Can customers downgrade?
Yes, customers can downgrade at end of billing cycle. Data is retained for 90 days after downgrade.

## Technical Troubleshooting

### Shopify Integration Issues

**Problem**: Data sync is delayed by more than 2 hours
**Solution**:
1. Check the Integrations page for error messages
2. Verify the Shopify API key hasn't been rotated
3. Re-authenticate by clicking "Reconnect" in Settings > Integrations
4. If the issue persists, contact support with your workspace ID

**Problem**: Historical data not importing
**Solution**: Historical imports are limited to 2 years. For longer histories, contact sales for a custom data migration package.

### Dashboard Issues

**Problem**: Charts showing "No Data"
**Solution**:
1. Verify your date range includes dates with orders
2. Check if a data source filter is excluding all data
3. Wait up to 15 minutes for real-time data to populate
4. Hard-refresh the browser (Ctrl+Shift+R)

**Problem**: AI recommendations not generating
**Solution**: AI recommendations require a minimum of 90 days of data and at least 100 orders. Check your data age in Settings > Data Sources.

## Data & Privacy

### How is customer data handled?
All data is encrypted at rest (AES-256) and in transit (TLS 1.3). We are SOC 2 Type II certified and GDPR compliant. Data is stored in AWS US-East-1 by default; EU data residency available on Enterprise plan.

### What data do we store?
We store aggregated e-commerce metrics (orders, revenue, traffic). We do NOT store individual customer PII from your store — only anonymized, aggregated data.

### How long is data retained?
- Active accounts: unlimited
- Canceled accounts: 90 days
- Exported on request at any time

## Support

### How to reach support?
- **In-app chat**: Available on all paid plans, 9 AM – 6 PM EST
- **Email**: support@company.com, 24-hour response SLA
- **Emergency (Scale+)**: Dedicated Slack channel with 2-hour SLA
- **Enterprise**: Named CSM + 1-hour response SLA

### Where is the status page?
status.company.com — subscribe for incident notifications.
