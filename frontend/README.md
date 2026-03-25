# Frontend - Next.js Portfolio & Dashboard

A modern, responsive portfolio and dashboard application built with **Next.js 16**, **React 19**, **TypeScript**, and **Tailwind CSS**. Features AWS Amplify authentication with Cognito OAuth (Google), role-based access control, and Material-UI components. Deployed as a static export to AWS S3 with CloudFront CDN.

## 🎯 Project Overview

- **Type**: Next.js 16 static-export web application
- **Purpose**: Personal portfolio, project showcase, and dashboard interface
- **Tech Stack**:
  - **Framework**: Next.js 16.1.6, React 19.2.3
  - **Language**: TypeScript
  - **Styling**: Tailwind CSS 4 + Material-UI (MUI) 7
  - **Auth**: AWS Amplify 6 with Cognito OAuth (Google provider)
  - **Markdown**: react-markdown with GitHub-flavored syntax support
  - **Icons**: Lucide React + Material-UI Icons
- **Deployment**: Static HTML/CSS/JS export to AWS S3 + CloudFront
- **Access Control**: Role-based hierarchy (null → user → admin_user)

---

## 📋 Prerequisites

- **Node.js** 18+ (recommended: 20 LTS or newer)
- **npm** 10+ or **Yarn** 4+
- **AWS Account** with:
  - Cognito User Pool configured (already set up in amplifyConfig.ts)
  - IAM credentials for Amplify authentication
- **Git** (optional, for version control)

---

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies

```bash
cd frontend
npm install
```

This installs all dependencies specified in `package.json`, including Next.js, React, Tailwind CSS, MUI, AWS Amplify, and development tools.

### 2. Set Environment Variables

Create a `.env.local` file in the `frontend/` directory with all required AWS Cognito configuration. You can use `.env.local.example` as a template:

```bash
cp .env.local.example .env.local
# Then edit .env.local with your Cognito values
```

```env
# AWS Cognito OAuth Domain
NEXT_PUBLIC_COGNITO_OAUTH_DOMAIN=<your-cognito-oauth-domain>

# AWS Cognito User Pool Configuration
NEXT_PUBLIC_COGNITO_USER_POOL_ID=<your-cognito-user-pool-id>
NEXT_PUBLIC_COGNITO_CLIENT_ID=<your-cognito-client-id>
NEXT_PUBLIC_COGNITO_REGION=us-east-1

# OAuth Redirect URLs
NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_IN=http://localhost:3000/
NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_OUT=http://localhost:3000/
```

**Important**: All `NEXT_PUBLIC_*` variables are exposed to the browser and must be set in `.env.local` for local development. For production deployments, update these values to match your AWS Cognito configuration and custom domain (e.g., `https://yourdomain.com/`).

### 3. Start Development Server

```bash
npm run dev
```

The application will start on **http://localhost:3000** with hot-reload enabled.

### 4. Open in Browser

Navigate to http://localhost:3000 in your browser. You'll see the portfolio page with:
- Terminal-styled introduction with role and experience info
- Skill badges (Python, Java, AWS, GenAI, etc.)
- Navigation with role-based access control
- Authentication via Google OAuth (Cognito)

---

## 📦 Available Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Start Next.js development server with hot reload on port 3000 |
| `npm run build` | Build for production (generates static export in `out/`) |
| `npm start` | Start production server (requires `npm run build` first) |
| `npm run lint` | Run ESLint to check code quality and style issues |

**Examples:**

```bash
# Development with auto-reload
npm run dev

# Build for production
npm run build

# Serve production build locally
npm start

# Check for linting errors
npm run lint

# Fix linting errors (auto-fixable ones)
npm run lint -- --fix
```

---

## 🔨 Build & Export

This project is configured as a **static export** application. This means:

- **No Node.js server required** at runtime
- Output is plain HTML, CSS, and JavaScript files
- Can be deployed to any static hosting service (S3, Netlify, Vercel, etc.)
- Optimized for edge networks and CDNs

### Build Output

Run `npm run build` to generate:

```
out/
├── index.html
├── _next/
│   ├── static/
│   │   ├── chunks/
│   │   └── css/
│   ├── images/
│   └── ...
├── [other pages and assets]
```

The `out/` directory contains the complete static site ready for deployment.

---

## 🔐 AWS Amplify & Cognito Authentication

### Configuration

Authentication is configured dynamically in `amplifyConfig.ts` using environment variables:

- **Auth Provider**: AWS Cognito with Google OAuth 2.0
- **Region**: `us-east-1` (configurable via `NEXT_PUBLIC_COGNITO_REGION`)
- **Cognito User Pool ID**: Set via `NEXT_PUBLIC_COGNITO_USER_POOL_ID`
- **Cognito Client ID**: Set via `NEXT_PUBLIC_COGNITO_CLIENT_ID`
- **OAuth Domain**: Set via `NEXT_PUBLIC_COGNITO_OAUTH_DOMAIN`
- **Redirect URLs**: Configured via `NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_IN` and `NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_OUT`

**No hardcoded values** — all configuration comes from the `.env.local` file or deployment environment, making it easy to manage different environments (local, dev, test, prod).

### User Hierarchy & Role-Based Access

The application enforces a role hierarchy defined in `app/layout.tsx`:

```
null (unauthenticated)
  ↓
user (authenticated, standard user)
  ↓
admin_user (authenticated, admin)
```

- **null users**: Not logged in; can view public pages
- **user**: Logged in via Google OAuth; access to authenticated routes
- **admin_user**: Admin flag (`custom:is_admin === 'true'`) in Cognito attributes

Access is enforced at the layout level. Routes can require a specific role:

```typescript
// In layout.tsx
function canAccess(required: UserMode, current: UserMode): boolean {
  return MODE_HIERARCHY.indexOf(current) >= MODE_HIERARCHY.indexOf(required);
}
```

### OAuth Setup for Google

Cognito is configured to accept Google OAuth logins:

```typescript
loginWith: {
    oauth: {
        domain: "...",
        providers: ["Google"],
        redirectSignIn: [...],
        redirectSignOut: [...],
        scopes: ["openid", "email", "profile", "aws.cognito.signin.user.admin"],
    }
}
```

When users click "Sign in with Google," they're redirected to the Google Cognito login flow and then back to your redirect URL.

---

## 📝 Environment Configuration

### Required Environment Variables

All authentication and configuration is managed through environment variables. Create a `.env.local` file in the `frontend/` directory:

| Variable | Purpose | Example |
|----------|---------|---------|
| `NEXT_PUBLIC_COGNITO_OAUTH_DOMAIN` | Cognito OAuth domain | `<region><random>.auth.<region>.amazoncognito.com` |
| `NEXT_PUBLIC_COGNITO_USER_POOL_ID` | Cognito User Pool ID | `<region>_<random>` |
| `NEXT_PUBLIC_COGNITO_CLIENT_ID` | Cognito application client ID | `<client-id-from-console>` |
| `NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_OUT` | Post-logout redirect URL | `http://localhost:3000/` |

### Environment Variable Format

**Local Development** (`.env.local`):
```env
NEXT_PUBLIC_COGNITO_OAUTH_DOMAIN=<your-oauth-domain>
NEXT_PUBLIC_COGNITO_USER_POOL_ID=<your-pool-id>
NEXT_PUBLIC_COGNITO_CLIENT_ID=<your-client-id>
NEXT_PUBLIC_COGNITO_REGION=us-east-1
NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_IN=http://localhost:3000/
NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_OUT=http://localhost:3000/
```

**Production** (via deployment script):
The `scripts/deploy-frontend.sh` script reads Cognito configuration from:
1. `.env.local` if present
2. AWS Systems Manager Parameter Store
3. Terraform outputs in S3 state

All variables can be overridden at build time or deployment time.

### Security Notes

- ⚠️ All `NEXT_PUBLIC_*` variables are **exposed to the browser** — do not include secrets or API keys
- OAuth domain and client ID must match your Cognito user pool configuration
- Redirect URLs must be registered in your Cognito application client settings
- Store sensitive values securely using AWS Secrets Manager or Parameter Store for production

---

## 📁 Project Structure

```
frontend/
├── app/                        # Next.js App Router directory
│   ├── layout.tsx             # Root layout with auth & role-based access control
│   ├── page.tsx               # Home page (portfolio/dashboard)
│   ├── globals.css            # Global styles (Tailwind + custom CSS)
│   └── [other pages]/
├── components/                 # Reusable React components
│   └── [component files]/
├── lib/                        # Utility functions & helpers
│   └── [utility files]/
├── public/                     # Static assets (images, fonts, etc.)
│   └── [static files]/
├── amplifyConfig.ts           # AWS Amplify & Cognito configuration
├── next.config.ts             # Next.js configuration (static export)
├── tsconfig.json              # TypeScript configuration
├── postcss.config.mjs          # PostCSS config for Tailwind CSS
├── eslint.config.mjs           # ESLint configuration
├── package.json               # Dependencies & scripts
├── package-lock.json          # Lock file
└── README.md                   # This file

```

### Key Files

- **`app/layout.tsx`**: Root layout component that initializes Amplify, manages authentication state, and enforces role-based access control
- **`app/page.tsx`**: Home page with terminal-style introduction, skills showcase, and portfolio content
- **`app/globals.css`**: Global Tailwind CSS setup and custom CSS classes
- **`amplifyConfig.ts`**: AWS Amplify configuration that reads all settings from environment variables
- **`next.config.ts`**: Enables static export mode (`output: 'export'`)
- **`.env.local`**: Local development environment variables (created by you)

---

## 🎨 Development Notes

### TypeScript & Strict Mode

- **Language**: Full TypeScript with JSX support
- **Strict Mode**: Disabled (`"strict": false` in tsconfig.json) for flexibility during development
- **Path Aliases**: Use `@/*` to import from the root:
  ```typescript
  import Button from '@/components/Button';
  import { helper } from '@/lib/helpers';
  ```

### Styling

**Tailwind CSS** (Primary):
- Version 4 with PostCSS plugin
- Configured in `postcss.config.mjs`
- All utility classes available

**Material-UI (Secondary)**:
- Emotion-based styled components
- For pre-built components like icons and buttons
- Coexists with Tailwind CSS

Both can be used simultaneously; they don't conflict.

### Markdown Support

The project includes Markdown rendering capabilities:

- **react-markdown** 10.1.0: Render Markdown as React components
- **remark**: Markdown AST processor
- **remark-gfm**: GitHub-flavored Markdown syntax support
- **remark-html**: Convert Markdown to HTML

Example usage:

```typescript
import ReactMarkdown from 'react-markdown';

export default function BlogPost({ content }) {
  return <ReactMarkdown>{content}</ReactMarkdown>;
}
```

### Testing Setup

Jest and React Testing Library are configured (devDependencies):
- `jest` 30.3.0
- `@testing-library/react` 16.3.2
- `@testing-library/jest-dom` 6.9.1

Run tests with:
```bash
npm run test
```

---

## 🚢 Deployment

### Automated Deployment to AWS

Use the deployment script:

```bash
scripts/deploy-frontend.sh <environment>
```

**Supported environments**: `dev`, `test`, `prod`

**Example:**

```bash
cd /path/to/digital_twin
scripts/deploy-frontend.sh dev
```

### What the Deployment Script Does

1. Reads AWS credentials from `AWS_PROFILE` (default: `terraform`)
2. Retrieves Terraform state from S3:
   - State bucket: `twin-terraform-state-${ACCOUNT_ID}`
   - State lock table: `twin-terraform-locks`
3. Builds the frontend (`npm run build`)
4. Deploys static files to S3 bucket specified in Terraform outputs
5. Invalidates CloudFront distribution cache
6. Reads service API URLs from Terraform state and injects them into the build
7. Outputs CloudFront URL and custom domain (if configured)

### Prerequisites for Deployment

- AWS credentials configured in `~/.aws/credentials` or via `AWS_PROFILE` environment variable
- Terraform state bucket already created (via `scripts/setup-infra.sh`)
- CloudFront and S3 bucket created in Terraform
- Required IAM permissions:
  - S3 read/write to frontend bucket
  - CloudFront distribution invalidation
  - Access to Terraform state files

### Deployment Flow

```
scripts/deploy-frontend.sh dev
    ↓
Read Terraform foundation outputs (S3 bucket, CloudFront ID)
    ↓
npm run build (generate static export)
    ↓
Upload files to S3 frontend bucket
    ↓
Invalidate CloudFront cache
    ↓
Display deployment URLs
```

### Verify Deployment

After deployment completes, you'll see:

```
🌐 Deploying frontend to environment: dev
   Frontend bucket : twin-frontend-dev-xxxxx
   CloudFront      : https://d1234567890ab.cloudfront.net/
   Custom domain   : https://portfolio.example.com/ (if configured)
```

Visit the CloudFront or custom domain URL to verify the deployment.

---

## 🐛 Troubleshooting

### Issue: "Missing environment variables"

If you see errors like `Cannot read property of undefined` or auth failures, check that `.env.local` is set up correctly:

```bash
# Verify .env.local exists
ls -la frontend/.env.local

# Check if variables are loaded
npm run dev
# Look for warnings about undefined env vars in console
```

Ensure `.env.local` contains all required variables with your actual AWS Cognito values:
```env
NEXT_PUBLIC_COGNITO_OAUTH_DOMAIN=<your-oauth-domain>
NEXT_PUBLIC_COGNITO_USER_POOL_ID=<your-pool-id>
NEXT_PUBLIC_COGNITO_CLIENT_ID=<your-client-id>
NEXT_PUBLIC_COGNITO_REGION=<your-region>
NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_IN=<your-redirect-signin-url>
NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_OUT=<your-redirect-signout-url>
```

Restart the dev server after adding or modifying `.env.local`:
```bash
npm run dev
```

### Issue: "Port 3000 already in use"

The dev server defaults to port 3000. Change it with:

```bash
PORT=3001 npm run dev
```

Then access http://localhost:3001.

### Issue: Cognito authentication fails

**Check:**
1. Environment variables are set in `.env.local`:
   ```bash
   echo $NEXT_PUBLIC_COGNITO_REDIRECT_SIGN_IN
   ```
2. Redirect URLs match your Cognito user pool client settings
3. For production: update `.env.local` redirect URLs to your production domain
4. Google OAuth provider is enabled in Cognito user pool

### Issue: Build fails with TypeScript errors

```bash
npm run build
```

Check for TypeScript compilation errors. Since strict mode is disabled, ensure no runtime logic errors exist. For debugging:

```bash
npx tsc --noEmit
```

### Issue: ESLint errors prevent build/deployment

Run ESLint to see issues:

```bash
npm run lint
```

Auto-fix common issues:

```bash
npm run lint -- --fix
```

### Issue: Styles not applying (Tailwind CSS)

Ensure Tailwind is configured correctly:

1. `postcss.config.mjs` includes `@tailwindcss/postcss`
2. `globals.css` includes Tailwind directives:
   ```css
   @import "tailwindcss";
   ```
3. Template paths in `tailwind.config.js` include all component files:
   ```javascript
   content: ['./app/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}']
   ```

Rebuild after changes:

```bash
npm run build
```

### Issue: "Cannot find module '@/...'"

Path aliases are configured in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

Ensure your editor recognizes this configuration. Restart the dev server:

```bash
npm run dev
```

### Issue: Role-based access not working

Check that:
1. User is authenticated (signed in with Google)
2. Cognito user attributes are correctly set (for `admin_user` role, check `custom:is_admin`)
3. Layout component correctly reads user attributes:
   ```typescript
   const user = await fetchUserAttributes();
   const mode = getUserMode(user);
   ```

---

## 📚 Additional Resources

- **Next.js Docs**: https://nextjs.org/docs
- **React Documentation**: https://react.dev
- **Tailwind CSS**: https://tailwindcss.com
- **Material-UI**: https://mui.com
- **AWS Amplify**: https://aws.amazon.com/amplify/
- **Cognito Documentation**: https://docs.aws.amazon.com/cognito/

---

## 📞 Support & Contact

For issues or questions:
1. Check the **Troubleshooting** section above
2. Review logs: `npm run dev` shows errors in real-time
3. Check AWS Cognito console for authentication issues
4. Verify Terraform deployment: `scripts/deploy-frontend.sh` logs

---

## 📄 License

This project is part of the Digital Twin research project and follows the repository's licensing terms.

---

**Last Updated**: March 2026  
**Status**: Active (Production-Ready)
