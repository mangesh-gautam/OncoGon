# OncoGonApp

OncoGon Voice — a hands-free lab assistant for oncology researchers. A **React Native app** talks to an **OMI necklace** over Bluetooth and to a **Python FastAPI backend** that stores accounts in **PostgreSQL**.

This folder holds four projects that work together:

| Folder | What it is | Tech | Details |
|---|---|---|---|
| [`OncoGon/`](OncoGon) | Mobile app (iOS + Android) | React Native 0.87, TypeScript | [README](OncoGon/README.md) |
| [`OncoGonAPI/`](OncoGonAPI) | Backend microservices: API gateway + auth service | Python 3.12, FastAPI, Docker | [README](OncoGonAPI/README.md) |
| [`OncoGonDB/`](OncoGonDB) | Database server | PostgreSQL 16, Docker | [README](OncoGonDB/README.md) |
| [`OmiconnectionPackage/`](OmiconnectionPackage) | OMI necklace SDK (Bluetooth discovery, connection, audio) | TypeScript library | [README](OmiconnectionPackage/README.md) |

---

## How they connect

```
                                   ┌───────────────────────────┐
                                   │  OMI necklace (hardware)  │
                                   └─────────────┬─────────────┘
                                                 │ Bluetooth LE (audio, battery, codec)
                                                 ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ OncoGon  (React Native app — on a phone, simulator or emulator)                  │
│                                                                                  │
│   src/omi/OmiDeviceContext.tsx ──imports──► @omiai/omi-react-native              │
│                                              = ../OmiconnectionPackage (local)   │
│   src/api/authApi.ts  ──HTTP──┐                                                  │
└───────────────────────────────┼──────────────────────────────────────────────────┘
                                │  http://<dev machine>:8000/api/v1/auth/...
                                ▼
┌──────────────────────────── Docker network: oncogon-net ─────────────────────────┐
│                                                                                  │
│  OncoGonAPI                                                                      │
│  ┌──────────────────────┐   /auth/...   ┌───────────────────────┐                │
│  │ gateway   :8000      │ ────────────► │ auth-service  :8001   │                │
│  │ (published to host)  │               │ (internal only)       │                │
│  └──────────────────────┘               └───────────┬───────────┘                │
│                                                     │ SQL as role oncogon_auth   │
│  OncoGonDB                                          ▼                            │
│                                       ┌──────────────────────────────┐           │
│                                       │ oncogon-postgres  :5432      │           │
│                                       │ db "oncogon", schema "auth"  │           │
│                                       │ (published to host as 5433)  │           │
│                                       └──────────────────────────────┘           │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 1. App ↔ OMI SDK — a local package link

The app uses the SDK as an npm dependency that points at the sibling folder:

```jsonc
// OncoGon/package.json
"@omiai/omi-react-native": "file:../OmiconnectionPackage"
```

`npm install` creates a symlink at `OncoGon/node_modules/@omiai/omi-react-native → ../OmiconnectionPackage`. Because the SDK ships its own `node_modules` (with its own copy of React), three configs keep the app using **one** React and the SDK's **source**:

| File | What it does |
|---|---|
| `OncoGon/metro.config.js` | Watches `../OmiconnectionPackage`, **ignores its `node_modules`**, resolves its peers (react, react-native, react-native-ble-plx) from the app |
| `OncoGon/tsconfig.json` | Type-checks against `../OmiconnectionPackage/src` (its prebuilt type files are out of date) |
| `OncoGon/jest.config.js` | Same mapping for tests, plus a Bluetooth mock |

The SDK needs `react-native-ble-plx`, which is installed in the **app** (it's a native module, so it must be linked into the app's iOS/Android builds).

**Rule:** keep `OncoGon/` and `OmiconnectionPackage/` side by side. After changing the SDK, Metro picks it up automatically; re-run `npm install` in `OncoGon/` only if the SDK's `package.json` changes.

### 2. App ↔ API — HTTP through the gateway

- The app only ever calls the **gateway** on port **8000**: `POST /api/v1/auth/login`, `/register`, `/refresh`, `GET /api/v1/auth/me`, etc. The gateway forwards `/api/v1/auth/*` to the auth service.
- **Which host?** `OncoGon/src/config/env.ts` uses the host the app loaded its JavaScript from (the Metro dev server), on port 8000:

  | Where the app runs | Metro host | API URL used |
  |---|---|---|
  | iOS simulator | `localhost` | `http://localhost:8000` |
  | Android emulator | `10.0.2.2` | `http://10.0.2.2:8000` |
  | Android phone with `adb reverse` (USB or wireless debugging) | `localhost` | `http://localhost:8000` (forwarded to the Mac) |
  | Phone on the same Wi-Fi | Mac's LAN IP | `http://<LAN IP>:8000` |
  | Release build / deployed API | — | set `OVERRIDE_GATEWAY` in `env.ts` |

- **Login state:** the API returns a 15-minute access token and a refresh token. The app keeps the refresh token in the iOS Keychain / Android Keystore and silently renews the session on launch (`OncoGon/src/auth/AuthContext.tsx`).
- **Errors:** every API error is `{"detail": "<message>"}`; the app shows `detail` directly.

### 3. API ↔ Database — a shared Docker network and matching credentials

- **Network:** `OncoGonDB/docker-compose.yml` **creates** the Docker network `oncogon-net`. `OncoGonAPI/docker-compose.yml` **joins** it as an external network. That's why the database must be started first.
- **Hostname:** inside the network the auth service reaches Postgres at **`oncogon-postgres:5432`** (the container name). Port 5433 on your machine is only for you and your database tools.
- **Credentials that must match** between the two `.env` files:

  | Variable | `OncoGonDB/.env` | `OncoGonAPI/.env` |
  |---|---|---|
  | `POSTGRES_DB` | creates the database | used in the connection string |
  | `AUTH_DB_USER` | creates the role (first start only) | connects as this role |
  | `AUTH_DB_PASSWORD` | sets its password (first start only) | uses this password |

- **Who creates what:** OncoGonDB creates the `auth` **schema** and the `oncogon_auth` **role** (`init/01-init.sh`, first start only). The auth service creates and upgrades the **tables** itself with Alembic migrations each time it starts. Each future microservice gets its own schema + role the same way.

### 4. Ports at a glance

| Port (on your machine) | Service | Who uses it |
|---|---|---|
| **8000** | API gateway | The app, curl, tests |
| 8001 | auth-service | Internal only (not published) |
| **5433** | PostgreSQL | You / DB tools (`5432` inside Docker) |
| **8081** | Metro bundler | The app in development (JavaScript bundle) |

---

## Run everything

Order matters: **database → API → app**.

```sh
# 1. Database (creates the oncogon-net network)
cd OncoGonDB && docker compose up -d && cd ..

# 2. API
cd OncoGonAPI && docker compose up -d --build && cd ..
curl localhost:8000/health        # {"status":"ok","services":{"auth":"ok"}}

# 3. App
cd OncoGon
npm install                       # also links ../OmiconnectionPackage
cd ios && pod install && cd ..    # iOS, after native dependency changes
npx react-native start            # Metro — leave running

# in a second terminal
npx react-native run-ios          # or: npx react-native run-android
```

**Android phone** (USB or wireless debugging) — forward Metro and the API to the phone first:

```sh
adb devices                                   # e.g. 192.168.1.4:46265
adb -s <device> reverse tcp:8081 tcp:8081
adb -s <device> reverse tcp:8000 tcp:8000
npx react-native run-android --deviceId <device>
```

Test account: `nomsa@oncogon.org` / `Oncology2026`, or create one in the app.

**Stop:** `docker compose down` in `OncoGonAPI/` and `OncoGonDB/` (data is kept in the `oncogon-pgdata` volume). `docker compose down -v` in `OncoGonDB/` deletes all data.

---

## A request end to end — signing in

1. User taps **Sign In** → `authApi.login()` sends `POST http://<host>:8000/api/v1/auth/login`.
2. **Gateway** checks the per-IP rate limit, adds `X-Request-ID` and `X-Forwarded-For`, and forwards to `http://auth-service:8001/auth/login`.
3. **Auth service** looks up the user in `auth.users`, checks the Argon2 password hash and lockout, then writes a new row to `auth.refresh_tokens`.
4. Response `{user, tokens}` returns through the gateway (with `X-Request-ID`).
5. The **app** stores the refresh token in the Keychain/Keystore, keeps the access token in memory, and switches from the sign-in screens to the lab flow.

On the next launch the app calls `/auth/refresh` (rotating the token) and `/auth/me` to restore the session without asking for the password.

## The OMI path (no backend involved)

Profile → **Pair device** → the app scans over Bluetooth through `OmiconnectionPackage` → connect → reads battery and codec. While the Listening or Research Note screen is open, the app streams audio from the necklace and uses it only to drive the on-screen waveform. Audio isn't stored or sent to the API yet; speech-to-text will be a future backend service.

---

## Configuration files to know

| File | Purpose | Commit it? |
|---|---|---|
| `OncoGonDB/.env` | DB superuser + per-service role passwords | **No** (git-ignored) |
| `OncoGonAPI/.env` | DB connection, `JWT_SECRET`, token lifetimes | **No** (git-ignored) |
| `*/.env.example` | Templates with placeholder values | Yes |
| `OncoGon/src/config/env.ts` | API URL resolution / `OVERRIDE_GATEWAY` | Yes |

## Current scope

| Area | Status |
|---|---|
| Sign up, sign in, sessions, forgot/reset password | Real (app + API + DB) |
| OMI pairing, battery, codec, audio streaming | Real (app + SDK + hardware) |
| Projects, notes, evidence, analysis, OncoGon Next, meetings | Research service serving mock data (`mock_data.json`) |
| Speech-to-text, AI analysis, email delivery | Not built yet |

## Adding a feature that needs data

1. **DB:** add a schema + role for the new service (`OncoGonDB/init/`, see its README).
2. **API:** add `OncoGonAPI/services/<name>/`, put it on `oncogon-net`, register its prefix in the gateway's `SERVICES` map, and verify the access token from the auth service.
3. **App:** add a client next to `src/api/authApi.ts` and call it through `useAuth().withAccessToken(...)` so expired tokens refresh automatically.
