# linkedin-cli

A command-line interface for LinkedIn — built for agents and humans.

## Quick Start

```bash
# 1. Install (editable mode)
pip install -e .

# 2. Configure credentials
cp .env.example .env
# Edit .env with your LinkedIn app credentials

# 3. Authenticate
linkedin auth login

# 4. Post something
linkedin post text "Hello from the CLI!"
```

## Commands

### Auth
| Command | Description |
|---|---|
| `linkedin auth login` | OAuth2 login flow (opens browser) |
| `linkedin auth login --code <url-or-code>` | Non-interactive login (agent-friendly) |
| `linkedin auth status` | Check token validity & auto-refresh status |
| `linkedin auth logout` | Remove saved token |

Token auto-refresh is built in — when your access token expires, the CLI silently uses the refresh token to get a new one. You only need to re-login when the refresh token expires (~365 days).

### Posts
| Command | Description |
|---|---|
| `linkedin post text "message"` | Publish a text-only post |
| `linkedin post image "message" --image photo.jpg` | Post with an image |
| `linkedin post article "message" --url https://... [--title "Title"]` | Post with a link/article preview |
| `linkedin post video "message" --video clip.mp4` | Post with a video |
| `linkedin post poll "Question?" -o "Option A" -o "Option B"` | Create a poll (2-4 options) |
| `linkedin post comment <post-id> "Great post!"` | Comment on a post |
| `linkedin post react <post-id> --type LIKE` | React to a post |
| `linkedin post list` | List your recent posts |
| `linkedin post list --count 5` | List N recent posts |
| `linkedin post delete <post-id>` | Delete a post by ID |

#### Poll options

```bash
# Duration: ONE_DAY, THREE_DAYS (default), ONE_WEEK, TWO_WEEKS
linkedin post poll "Best language?" -o Python -o Rust -o Go --duration ONE_WEEK
```

#### Reaction types

`LIKE` (default), `CELEBRATE`, `SUPPORT`, `LOVE`, `INSIGHTFUL`, `FUNNY`

```bash
linkedin post react urn:li:share:123456 --type CELEBRATE
```

### Profile
| Command | Description |
|---|---|
| `linkedin profile me` | Display your LinkedIn profile info |

## Global Options

| Flag | Description |
|---|---|
| `--json` / `-j` | Output JSON (for agent/script consumption) |
| `--version` / `-V` | Show version |

## Agent Usage

Every command supports `--json` for structured output:

```bash
# Get profile as JSON
linkedin --json profile me

# Post and capture the result
linkedin --json post text "Automated post"

# Check auth status programmatically
linkedin --json auth status

# Post an article and get the ID back
linkedin --json post article "Read this" --url https://example.com

# Comment on a post
linkedin --json post comment urn:li:share:123456 "Insightful!"
```

Non-interactive login (pass the code directly):

```bash
linkedin auth login --code "AQT..."
```

## Configuration

Set these in `.env` or as environment variables:

| Variable | Required | Default |
|---|---|---|
| `LINKEDIN_CLIENT_ID` | Yes | — |
| `LINKEDIN_CLIENT_SECRET` | Yes | — |
| `LINKEDIN_REDIRECT_URI` | No | `https://greenmountaincomputing.com/` |
| `LINKEDIN_SCOPES` | No | `w_member_social openid profile` |
| `LINKEDIN_API_VERSION` | No | `202506` |
| `LINKEDIN_TOKEN_FILE` | No | `linkedin_token.json` |

## API Scope Reference

The default scopes (`w_member_social openid profile`) support:

| Feature | Supported |
|---|---|
| Text / image / video / article posts | Yes |
| Polls | Yes |
| Comments & reactions | Yes |
| Delete your posts | Yes |
| List your posts | Yes |
| View your profile | Yes |
| Look up other people | No (API not available) |
| Connection requests | No (API not available) |
| Messaging / DMs | No (restricted to partners) |
| Read your feed | No (API not available) |
