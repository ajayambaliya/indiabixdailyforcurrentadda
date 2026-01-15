# Indiabix Current Affairs Scraper

This project automatically scrapes daily current affairs from Indiabix, translates them into Gujarati, and stores them in a Supabase database. It runs daily via GitHub Actions.

## Setup Instructions

### 1. Supabase Setup
- Create a Supabase project.
- Run the SQL in `supabase_schema.sql` in the Supabase SQL Editor to create the necessary tables.

### 2. GitHub Gist Setup
- Create a new Secret Gist at [gist.github.com](https://gist.github.com).
- Add a file named `scraped_urls.json` with content `[]`.
- Note the **Gist ID** from the URL (the long string of characters at the end of the URL).

### 3. GitHub Repository Secrets
In your GitHub repository, go to **Settings > Secrets and variables > Actions** and add the following secrets:
- `SUPABASE_URL`: Your Supabase Project URL.
- `SUPABASE_KEY`: Your Supabase `service_role` API key (required for inserts).
- `GH_TOKEN`: A Personal Access Token (PAT) with `gist` scope.
- `GIST_ID`: The ID of the Gist you created in step 2.

### 4. Running the Scraper
- The scraper is scheduled to run daily at midnight (UTC).
- You can also trigger it manually from the **Actions** tab in your GitHub repository.

## Features
- **Daily Scraping**: Automatically finds new dates on Indiabix Current Affairs.
- **Translation**: Translates questions, options, and explanations into Gujarati using `deep-translator`.
- **Gist Sync**: Keeps track of processed URLs in a GitHub Gist to avoid duplicate scraping.
- **Supabase Integration**: Stores data in a structured format suitable for a quiz application.

## Schema Changes
The provided `supabase_schema.sql` has been updated to include:
- `category` in the `quizzes` table.
- `text_gu`, `options_gu`, and `explanation_gu` in the `questions` table for Gujarati content.
