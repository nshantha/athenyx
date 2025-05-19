## Running locally

You will need to use the environment variables [defined in `.env.example`](.env.example) 

> Note: You should not commit your `.env` file or it will expose secrets that will allow others to control access to your various OpenAI and authentication provider accounts.

Copy the `.env.example` file and populate the required env vars:

```bash
cp .env.example .env
```

[Install the Supabase CLI](https://supabase.com/docs/guides/cli) and start the local Supabase stack:

```bash
npm install supabase --save-dev
npx supabase start
```

Install the local dependencies and start dev mode:

```bash
pnpm install
pnpm dev
```

Your app template should now be running on [localhost:3000](http://localhost:3000/).

## Actuamind Integration

This Next.js frontend has been customized to work with Actuamind's backend API. The integration provides:

1. Repository management (add, select, and view repositories)
2. Chat interface to query code repositories
3. Optional Supabase authentication and chat history storage

### About this Frontend

This frontend is based on a Next.js template but has been modified to:

1. **Remove OpenAI dependencies**: The original template used OpenAI directly, but we've modified it to use the Actuamind backend API instead.

2. **Why Vercel is used**: The frontend uses Vercel-related packages for:
   - Analytics (`@vercel/analytics`): For website usage tracking
   - Open Graph image generation (`@vercel/og`): For generating preview images for social sharing
   
   These are optional dependencies and not required for the core functionality.

3. **Direct API Integration**: The chat component now communicates directly with the Actuamind backend API instead of using the Vercel AI SDK.

### Setup

1. Copy `.env.example` to `.env.local` and configure:
   ```
   NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000  # URL to your Actuamind backend
   ```

2. If using Supabase for authentication (optional):
   ```
   NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
   ```

3. Install dependencies and start the development server:
   ```bash
   npm install
   npm run dev
   ```

4. Access the application at http://localhost:3000

### API Integration

The frontend communicates with the Actuamind backend using these endpoints:

- `/api/repositories` - Repository management
- `/api/query` - Chat queries about repositories

Authentication is optional - the application will work without login but won't store chat history.
