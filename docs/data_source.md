# Data Source and Simulation Design Documentation

This document outlines the schema, design rationale, and statistical distributions used for generating the simulated TikTok KOL (Key Opinion Leader) dataset for the optimizer platform.

---

## 1. Schema Definitions (12 Fields)

The dataset contains the following 12 fields generated for each influencer profile:

| Field Name | Data Type | Description |
| :--- | :--- | :--- |
| `kol_id` | String / Int | Unique identifier for the TikTok creator profile. |
| `username` | String | Simulated handle/name of the creator. |
| `tier` | String | Market categorization based on follower size (`Nano`, `Micro`, `Macro`, `Mega`). |
| `followers` | Integer | Total follower count on the platform. |
| `avg_views` | Integer | Average video view count over recent posts. |
| `likes_avg` | Integer | Average number of likes per video. |
| `comments_avg` | Integer | Average number of comments per video. |
| `shares_avg` | Integer | Average number of video shares. |
| `engagement_rate` | Float | Metric calculated as: `((likes + comments + shares) / followers) * 100`. |
| `reach` | Integer | Estimated unique audience reach per campaign post. |
| `cost` | Float / Int | Base financial cost (USD) to secure a sponsored post with the creator. |
| `niche` | String | Primary content category (e.g., Tech, Beauty, Gaming, Lifestyle). |

---

## 2. Simulation Rationale (Why Mock Data?)

The data used in this optimization engine is entirely simulated rather than scraped from live production environments due to two primary constraints:

* **Lack of Open TikTok APIs:** TikTok maintains strict rate limits and does not provide public, open-access developer endpoints to harvest sweeping database records of global creator pricing and internal performance metrics.
* **Privacy and Commercial Sensitivity:** Real-world influencer contracts, cost-per-post figures, and demographic performance variables are governed by strict non-disclosure agreements (NDAs) and privacy laws. Mock generation ensures compliance while allowing system stress-testing.

---

## 3. Distribution Assumptions

The simulator builds populations based on structural parameters aligned with actual social media market dynamics:

### Market Tier Splits
The population is strictly segmented to replicate real-world long-tail distribution frequencies:
* **Nano KOLs:** **40%** of total dataset (High volume, niche focus)
* **Micro KOLs:** **35%** of total dataset
* **Macro KOLs:** **20%** of total dataset
* **Mega KOLs:** **5%** of total dataset (Celebrity tier, scarce availability)

### Behavioral Rules
* **Inverse Engagement Logic:** Engagement rates are modeled to be **inversely proportional** to follower counts. As a creator's follower base expands into Macro and Mega tiers, their percentage-based engagement decays naturally.
* **Positive Cost Correlation:** Total booking `cost` is modeled with a **strong positive correlation** to estimated user `reach`. Larger reach metrics scale the baseline asset valuations upward.