# Server Setup Flow

## Goal

One command should rapidly provision a clean Shaheen Discord server.

## Flow

/setup
  -> permission preflight
  -> configuration selection
  -> confirmation
  -> roles
  -> categories
  -> channels
  -> permissions
  -> branding embeds
  -> welcome/rules/roles messages
  -> verification
  -> report

## Modes

### Development
- public community channels can remain restricted
- DEVELOPMENT is visible only to authorized staff
- test commands are enabled for authorized users

### Launch
- public onboarding is enabled
- DEVELOPMENT is hidden from normal members
- welcome/rules/role selection are deployed
- final permission verification runs

## Idempotency

Setup must be safe to re-run.

For every resource:
1. find existing resource using stored ID if available
2. otherwise use a safe deterministic name/type match
3. verify configuration
4. update where safe
5. create only if missing

Never blindly delete and recreate the entire server.

## Destructive operations

Anything that could delete channels, roles or messages requires an explicit
confirmation and should be excluded from the normal setup path.

## Verification

Final report should include:
- roles created/found
- categories created/found
- channels created/found
- permission mismatches
- messages deployed
- warnings
- errors
