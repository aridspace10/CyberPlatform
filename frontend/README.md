# React + Vite

## Backend URL

The frontend uses `http://localhost:8000` for local development. For a hosted
build, set `VITE_BACKEND_URL` to the backend's public HTTP(S) origin (for example,
`https://api.example.com`). Configure the backend's `CYBERPLATFORM_CORS_ORIGINS`
with the frontend origin so browser downloads and API calls are allowed.

## Public Sandbox launch

For the initial public release, build the frontend with `VITE_PUBLIC_SANDBOX_ONLY=true`
and run the API with `CYBERPLATFORM_PUBLIC_SANDBOX_ONLY=true`. These two settings
represent the same launch flag across the separately deployed frontend and API.
The frontend hides session routes and controls; the API returns 404 for multiplayer
actions and only accepts the authenticated owner's Sandbox session. Development
defaults to the full feature set when the flag is unset.

## Contact reports

The public `/contact` page sends issue reports through the backend's SMTP
connection. Set these **backend** environment variables when an inbox and an
SMTP account are ready:

```text
CYBERPLATFORM_SMTP_HOST=smtp.your-provider.example
CYBERPLATFORM_SMTP_PORT=587
CYBERPLATFORM_SMTP_SECURITY=starttls
CYBERPLATFORM_SMTP_USERNAME=your-smtp-username
CYBERPLATFORM_SMTP_PASSWORD=your-smtp-password
CYBERPLATFORM_CONTACT_FROM=verified-sender@your-domain.example
CYBERPLATFORM_CONTACT_TO=your-issues-inbox@example.com
```

Use `CYBERPLATFORM_SMTP_SECURITY=ssl` and port `465` if your provider requires
implicit TLS. Username and password may both be omitted for an SMTP relay that
does not require authentication. Choose a provider with a free plan if desired;
the app uses only standard SMTP. The sender must be accepted by that provider.
Until these settings are present, the API returns a clear temporary-unavailable
error and the form keeps the entered report so users can retry.

Each email has a `[CyberPlatform][category]` subject prefix, a unique reference,
and labeled fields for the report, reproduction steps, expected and actual
results, page, and device. Inbox filters can sort by category prefix or the
`X-CyberPlatform-Category` header. Replying uses the reporter's email address.
The contact endpoint accepts at most five submissions per client per five-minute
window. As with account limits, configure trusted proxy headers correctly in
production so the client address is accurate.

## Homepage ads

Ads are controlled site-wide through the frontend deployment's environment
settings. They are off by default and appear only on the public homepage,
between **How it works** and **The Sandbox**. Set these values in Render's
frontend service environment settings, then redeploy the frontend:

```text
VITE_ADS_ENABLED=true
VITE_ADSENSE_CLIENT=ca-pub-your-publisher-id
VITE_ADSENSE_SLOT=your-display-ad-slot-id
```

Set `VITE_ADS_ENABLED=false` and redeploy to turn ads off for everyone. These
Vite values are included in the built frontend, so changing them needs a new
build. With ads enabled in local development, the homepage shows a labelled
preview instead of requesting a real ad. Production shows no empty ad space
if the publisher or slot ID is missing.

Create a responsive display ad unit in AdSense and copy its client and slot
IDs into these settings. After Google supplies your `ads.txt` line, add it as
`frontend/public/ads.txt` so it is served at `https://your-domain/ads.txt`.
The live site must be approved by AdSense before Google serves ads.

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
