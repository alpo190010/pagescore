# PageScore — AI Landing Page Analyzer

**Business model:** Free quick scan → $7 paid deep-dive report.  
**Target:** $10/day = ~2 sales/day.

## Stack

- **Frontend:** Next.js 16 + Tailwind CSS 4
- **AI:** OpenAI GPT-4o-mini (free scan) / GPT-4o (paid report)
- **Payments:** Lemon Squeezy ($7 one-time)
- **Email:** Resend (report delivery)
- **Hosting:** Vercel (free tier)

## Setup

### 1. API Keys

```bash
cp .env.local.example .env.local
# Fill in your keys
```

You need:
- **OpenAI API key** — [platform.openai.com](https://platform.openai.com)
- **Lemon Squeezy** — Create a store + product ($7) at [lemonsqueezy.com](https://lemonsqueezy.com)
- **Resend** — Email delivery at [resend.com](https://resend.com)

### 2. Lemon Squeezy Setup

1. Create store → Create product ($7, "PageScore Full Report")
2. Enable "Custom data" in checkout settings
3. Copy checkout URL → set `NEXT_PUBLIC_LEMONSQUEEZY_CHECKOUT_URL`
4. Add webhook pointing to `https://yourdomain.com/api/webhook`
5. Set webhook secret → `LEMONSQUEEZY_WEBHOOK_SECRET`
6. Select "order_created" event

### 3. Deploy

```bash
npm run build
# Deploy to Vercel:
npx vercel --prod
```

### 4. Domain

Buy `pagescore.app` or similar. Connect to Vercel.

## Cost Per Sale

- GPT-4o-mini (free scan): ~$0.001
- GPT-4o (paid report): ~$0.03
- Resend email: free tier (100/day)
- Vercel: free tier
- **Margin: ~99%**

## Distribution Plan

1. **Reddit** — Post in r/webdev, r/SaaS, r/startups, r/marketing (share free tool, not sales pitch)
2. **Twitter/X** — "I built an AI tool that scores your landing page" thread
3. **Indie Hackers** — Launch post + building in public
4. **Product Hunt** — Schedule launch
5. **Hacker News** — Show HN post
6. **SEO** — Target "landing page analyzer", "landing page score", "landing page audit"
