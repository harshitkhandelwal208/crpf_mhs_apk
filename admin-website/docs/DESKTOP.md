# CRPF MHS Admin desktop build

The Windows desktop application is a secure Electron shell around the existing
Next.js standalone server. It does not load the admin console from a public web
origin:

1. Electron selects an available high port and starts Next on
   `127.0.0.1` only.
2. Electron waits for an HTTP response from that loopback address.
3. A single sandboxed renderer loads that local URL.
4. Closing the application stops the Next process and its child processes.

The packaged application includes the Electron runtime and the traced Next
standalone output. Node.js is not required on the destination computer.

## Commands

Install dependencies and run the desktop application in development:

```powershell
npm install
npm run desktop:dev
```

`desktop:dev` starts `next dev` automatically on `127.0.0.1`; do not start a
second development server in another terminal.

Build the server/CI artifact:

```powershell
npm run build
```

Build an x64 Windows NSIS installer:

```powershell
npm run desktop:dist
```

The installer is written to `dist-desktop/` and installs per user without
requiring administrative elevation. The package is unsigned unless code
signing is configured by the release pipeline, so Windows SmartScreen may warn
on an internally distributed build.

## Runtime API configuration

The desktop server is expected to call the cloud API through
`BACKEND_API_URL`. Use an HTTPS URL in production. `BACKEND_API_URL` is a
server environment variable; do not rename it to `NEXT_PUBLIC_BACKEND_API_URL`
or otherwise expose credentials or privileged configuration to browser code.

The preferred deployment option is a user or system environment variable that
exists before the application starts. The launcher passes inherited server
environment variables to Next unchanged, except that it always controls
`NODE_ENV`, `HOSTNAME`, and `PORT`.

For managed installations that cannot set an environment variable, create:

`%APPDATA%\CRPF MHS Admin\desktop-config.json`

with this content:

```json
{
  "BACKEND_API_URL": "https://api.example.gov.in"
}
```

The optional file is limited to 16 KiB, must contain a JSON object, and accepts
only `BACKEND_API_URL`. Its URL must use HTTPS, except that loopback HTTP is
accepted for local testing. If both sources define the value, the system
environment takes precedence. Invalid or unknown settings stop startup with an
actionable error instead of being silently ignored.

Other server-only settings required by deployed features can be supplied as
system environment variables and are inherited by the local server. Never use
`NEXT_PUBLIC_*` for secrets: those values are compiled into renderer assets.
Do not embed `DATABASE_URL`, database passwords, API secrets, signing secrets,
or service-account credentials in the renderer or installer. The desktop
console should use `BACKEND_API_URL` rather than connecting directly to a
database.

## Network and firewall behavior

Every listener created by the launcher or Next binds explicitly to
`127.0.0.1`. The application never listens on `0.0.0.0`, a LAN interface, or a
public interface, and the installer does not disable Windows Firewall or add
firewall rules. Consequently, no inbound/public listener is opened and a
recurring inbound firewall permission should not be required.

Calls from the local Next server to `BACKEND_API_URL` are outbound HTTPS
connections. Enterprise proxy, certificate, endpoint-security, and firewall
policy can still govern or block that outbound traffic.

## Security properties

- Renderer Node integration is disabled.
- Context isolation and Chromium sandboxing are enabled.
- No preload bridge or remote module is exposed.
- Popups are denied; validated HTTP/HTTPS external links open in the default
  system browser.
- Unexpected top-level navigation and all permission requests are denied.
- Production developer tools and the application menu are disabled.
- Spellcheck is disabled and only one renderer window is created.
- A single-instance lock prevents duplicate local servers.
- Application source and the project's general `node_modules` tree are not
  packaged; only Electron files and the traced standalone server are included.
- `.env` files, source maps, and build caches are excluded from
  `extraResources`.

Do not add unsafe Chromium command-line switches to suppress security features.
If a startup dialog appears, verify `desktop-config.json`, confirm that endpoint
security has not blocked the executable, and review the bounded server output
included in the dialog.
