# IT Economic Calendar – daily Discord poster

Posts today's **high-impact** news for the major currencies (USD, EUR, GBP, JPY, AUD, NZD, CAD, CHF, CNY), plus bank holidays, to the `economic-calendar` channel every day at **00:10 SAST**. Times are shown in SAST. On days with nothing scheduled it posts a green "No high-impact news" card.

Data source: the public Forex Factory weekly calendar feed (`nfs.faireconomy.media`).

## One-time setup (about 5 minutes)

> Already done for this repo. Kept here in case you ever need to rebuild it.
> This repo is **public** so GitHub Actions runs free. The webhook URL is never in the code; it lives only in the `DISCORD_WEBHOOK_URL` secret, which nobody else can see.

1. **Create the repo**: on github.com click **New repository**, name it `it-economic-calendar`, and tick **Add a README**.
2. **Add the script**: in the repo click **Add file → Upload files** and drag in `post_calendar.py`.
3. **Add the schedule**: click **Add file → Create new file**. For the file name type exactly
   `.github/workflows/daily-calendar.yml`
   then paste in the contents of `daily-calendar.yml` and click **Commit changes**.
   (A Mac hides folders that start with a dot, which is why this step is done by hand.)
4. **Add the webhook as a secret**:
   - In Discord, go to economic-calendar → **Edit Channel → Integrations → Webhooks → IT Economic Calendar → Copy Webhook URL**.
   - In GitHub, go to **Settings → Secrets and variables → Actions → New repository secret**.
   - Name: `DISCORD_WEBHOOK_URL`. Value: paste the URL. Click **Add secret**.
5. **Test it**: go to the **Actions** tab → **Daily high-impact news** → **Run workflow**. A post should appear in economic-calendar within about a minute.

After that it runs on its own every night.

## Notes
- The webhook URL works like a password for posting in that channel. Keep it only in the GitHub secret. If it ever leaks, delete the webhook in Discord, create a new one, and update the secret.
- GitHub sometimes starts scheduled jobs a few minutes late when its servers are busy.
- Forex Factory times can change on the day. The post's footer says so.
- To change the currencies, edit the `MAJORS` list in `post_calendar.py`.
