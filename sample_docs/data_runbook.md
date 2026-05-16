---
title: Data Engineering Runbook
category: Data
author: Data Platform Team
last_updated: 2024-04-10
---

# Data Engineering Runbook

Operational guide for the data platform — pipelines, warehouses, and incident procedures.

## Data Stack Overview

| Component | Tool | Purpose |
|-----------|------|---------|
| Ingestion | Fivetran + custom Python | EL from SaaS sources |
| Transformation | dbt (BigQuery) | Data modeling |
| Warehouse | Google BigQuery | Analytical storage |
| Orchestration | Airflow (Cloud Composer) | Pipeline scheduling |
| BI Layer | Looker | Dashboards & reports |
| Data Quality | Great Expectations | Automated testing |
| Reverse ETL | Census | Sync warehouse → SaaS |

## Pipeline Architecture

```
SaaS Sources (Shopify, Stripe, HubSpot)
        │
        ▼ [Fivetran – every 6 hours]
  BigQuery Raw Layer (bq_raw_*)
        │
        ▼ [dbt – daily 2 AM UTC]
  BigQuery Staging Layer (bq_stg_*)
        │
        ▼ [dbt]
  BigQuery Mart Layer (bq_mart_*)
        │
        ▼ [Looker]
  Dashboards & Ad-hoc Analysis
```

## Common Runbook Tasks

### Triggering a Manual Pipeline Run

```bash
# Trigger a specific Airflow DAG
gcloud composer environments run data-platform \
  --location us-central1 \
  dags trigger -- shopify_daily_sync

# Check DAG status
gcloud composer environments run data-platform \
  --location us-central1 \
  dags state -- shopify_daily_sync <run_id>
```

### Running dbt Models

```bash
# Activate dbt environment
source ~/.venv/dbt/bin/activate
cd /repos/analytics

# Run all models
dbt run --target prod

# Run specific model and its dependencies
dbt run --select +mart_revenue_daily --target prod

# Run tests
dbt test --select mart_revenue_daily

# Full refresh (reprocess historical data)
dbt run --full-refresh --select stg_shopify_orders
```

### Checking Data Freshness

```sql
-- Check when tables were last updated
SELECT
  table_name,
  TIMESTAMP_MILLIS(last_modified_time) AS last_modified,
  row_count,
  size_bytes / 1e9 AS size_gb
FROM `company-data.bq_mart.__TABLES__`
ORDER BY last_modified DESC;
```

### Backfilling Historical Data

```bash
# Fivetran backfill via API
curl -X POST https://api.fivetran.com/v1/connectors/{connector_id}/resync \
  -H "Authorization: Bearer $FIVETRAN_API_KEY" \
  -d '{"scope": {"schemas": ["public"], "tables": ["orders"]}}'

# dbt incremental backfill
dbt run --full-refresh --select stg_shopify_orders+
```

## Data Quality Checks

### Running Great Expectations

```bash
cd /repos/analytics/great_expectations

# Run all checkpoints
great_expectations checkpoint run daily_revenue_checkpoint

# Run specific suite
great_expectations suite run --suite revenue_suite
```

### Critical Data Quality Rules

These tests run on every pipeline execution and will page on-call if they fail:

| Table | Check | Threshold |
|-------|-------|-----------|
| `mart_revenue_daily` | Row count > 0 | Hard fail |
| `mart_revenue_daily` | No nulls in `revenue_usd` | Hard fail |
| `mart_revenue_daily` | Revenue variance < 50% day-over-day | Warning |
| `stg_orders` | Unique `order_id` | Hard fail |
| `stg_customers` | Valid email format | Warning (< 2% failure) |

## Incident Response

### Pipeline Failure (SEV2)

1. Check Airflow UI at `airflow.internal.company.com`
2. Identify the failed task and view logs
3. Check if it's a transient error (retry the task)
4. If data source issue, check Fivetran status dashboard
5. Notify `#data-incidents` Slack channel
6. Escalate to data platform on-call if not resolved in 2 hours

### Data Discrepancy (SEV3)

If stakeholders report incorrect numbers:
1. Identify affected metric and time range
2. Trace through: Looker → dbt mart → dbt staging → raw
3. Check recent dbt run logs for warnings
4. Compare raw source vs warehouse counts:

```sql
-- Shopify order count discrepancy check
SELECT
  DATE(created_at) AS order_date,
  COUNT(*) AS raw_count
FROM `company-data.bq_raw_shopify.orders`
WHERE DATE(created_at) BETWEEN '2024-01-01' AND '2024-01-31'
GROUP BY 1

EXCEPT DISTINCT

SELECT
  order_date,
  order_count
FROM `company-data.bq_mart.mart_revenue_daily`
WHERE order_date BETWEEN '2024-01-01' AND '2024-01-31';
```

### BigQuery Quota Exceeded

```bash
# Check current quota usage
bq show --project_id=company-data

# Cancel runaway queries
bq ls --jobs --all | grep RUNNING
bq cancel <job_id>
```

## Access & Permissions

### Requesting BigQuery Access
Submit request to `#data-platform` Slack with:
- Your Google account email
- Dataset(s) needed
- Business justification
- Duration (temporary or permanent)

### Access Levels
| Role | Access | Who Gets It |
|------|--------|-------------|
| `viewer` | Read bq_mart_* only | Analysts, PMs |
| `analyst` | Read all layers | Senior analysts |
| `engineer` | Read/write staging | Data engineers |
| `admin` | Full access | Data platform team |

## Useful Queries

### Revenue dashboard quick check
```sql
SELECT
  order_date,
  SUM(revenue_usd) AS total_revenue,
  COUNT(DISTINCT order_id) AS orders,
  COUNT(DISTINCT customer_id) AS unique_customers
FROM `company-data.bq_mart.mart_revenue_daily`
WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY 1
ORDER BY 1 DESC;
```

### Pipeline health check
```sql
SELECT
  dag_id,
  state,
  execution_date,
  start_date,
  end_date,
  TIMESTAMP_DIFF(end_date, start_date, MINUTE) AS duration_minutes
FROM `company-data.bq_raw_airflow.dag_run`
WHERE execution_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
ORDER BY execution_date DESC;
```

## Contacts

| Role | Contact | On-Call |
|------|---------|---------|
| Data Platform Lead | dataplatform@company.com | Yes (PagerDuty) |
| Analytics Engineer | analytics@company.com | No |
| Fivetran Support | support.fivetran.com | Vendor |
| BigQuery Support | cloud.google.com/support | Vendor |
