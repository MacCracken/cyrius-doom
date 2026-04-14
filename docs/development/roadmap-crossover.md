# AgentWorld / DOOM Crossover Roadmap

> Spatial threat visualization — security agents navigate infrastructure topology as DOOM levels.
> Integration point: [secureyeoman](https://github.com/MacCracken/secureyeoman) agent platform.

## Concept

An agent walks through a door and becomes Doomguy. Network topology becomes map geometry. Threats become monsters. Credentials become key cards. Remediation is shooting.

The WAD format is a spatial data container. Nothing requires the lumps to be id Software's maps. Generate WADs from live infrastructure — the DOOM engine renders them, the agent navigates them, secureyeoman acts on the results.

## Threat → Enemy Mapping

| DOOM Enemy | Threat Class | Behavior |
|-----------|-------------|----------|
| Zombieman | Low-severity CVE | Static. Easy cleanup. |
| Imp | Medium severity | Ranged attack. Needs attention. |
| Demon | Privilege escalation | Charges. Fast. Close range. |
| Spectre | Stealth threat | Invisible demon. You don't see it coming. |
| Cacodemon | Remote code execution | Flying. Can reach you from anywhere. |
| Lost Soul | Lateral movement | Flies through walls. Hard to contain. |
| Baron of Hell | APT actor | Tanky. Sustained effort to eliminate. |
| Cyberdemon | Zero-day | Boss. Requires BFG (incident response team). |
| Barrel | Misconfigured service | Harmless until hit — then blast radius takes out neighbors. |

## Asset → Item Mapping

| DOOM Item | Security Asset |
|----------|---------------|
| Health potion | Patch (minor fix) |
| Stimpack | Hotfix |
| Medikit | Patch bundle |
| Soulsphere | Full remediation |
| Green armor | Basic monitoring |
| Blue armor | Full SIEM coverage |
| Blue key | Read access credential |
| Yellow key | Write access credential |
| Red key | Admin credential |
| Shotgun | Automated scanner |
| Chaingun | Continuous scanning |
| Rocket launcher | Incident response tool |
| BFG | Full IR team engagement |

## Infrastructure → Geometry Mapping

| Network Concept | DOOM Geometry |
|----------------|--------------|
| Network zone | Sector (floor/ceiling = trust level) |
| Firewall rule | Linedef (one-sided = blocked, two-sided = filtered) |
| Open port | Door (walk-through trigger) |
| ACL check | Locked door (key card required) |
| DMZ | Outdoor sector (sky ceiling) |
| Internal network | Indoor sector (low ceiling, high light) |
| Compromised zone | Sector with low light level (dark) |
| Honeypot | Sector with barrel traps |

## Phase 1: WAD Generator

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Topology → sector graph | Not started | Parse secureyeoman zone definitions into connected sectors |
| 2 | Firewall → linedef rules | Not started | ACL rules become wall/door types with appropriate specials |
| 3 | Threat spawn | Not started | Active CVEs from scanner output placed as things at correct positions |
| 4 | Credential gates | Not started | Access tier boundaries become key-locked doors |
| 5 | WAD binary writer | Not started | Generate valid IWAD/PWAD from sector graph (header, directory, lumps) |
| 6 | BSP builder | Not started | Compute BSP tree, segs, subsectors, nodes from linedef geometry |

## Phase 2: Agent Interface

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Headless navigation API | Not started | Agent sends move/turn/use/fire commands, receives PPM frame + state |
| 2 | Spatial query interface | Not started | "What threats are in this sector?" → list things in subsector |
| 3 | BSP path planning | Not started | Agent uses BSP tree for reachability reasoning |
| 4 | Kill → remediate | Not started | Firing at threat thing triggers remediation action in secureyeoman |
| 5 | Door → access request | Not started | Using locked door triggers credential validation |
| 6 | Pickup → asset claim | Not started | Collecting items maps to claiming security tools |

## Phase 3: Live Integration

| # | Item | Status | Detail |
|---|------|--------|--------|
| 1 | Real-time WAD regen | Not started | Infrastructure changes trigger WAD rebuild, new threats spawn |
| 2 | Multi-agent coop | Not started | Multiple agents in same WAD, different roles/spawn points |
| 3 | Incident replay | Not started | Record navigation as DEMO lump, replay threat response timeline |
| 4 | Operator dashboard | Not started | Render agent POV as live PPM stream for human operators |
| 5 | Threat heatmap | Not started | Overlay kill/damage stats on automap as zone-level threat density |

## Dependencies

- **cyrius-doom v1.0.0+**: PWAD support required for loading generated WADs
- **secureyeoman**: Zone/threat/credential data source
- **bsp library**: BSP tree construction for generated geometry
- **WAD spec**: Binary format writer (inverse of current WAD parser)

## Why DOOM

1. The WAD format is documented, simple, and proven over 30 years
2. BSP spatial partitioning is the same algorithm used for network zone reasoning
3. The DOOM engine is already headless (`--ppm`) — no display needed for agent use
4. 3.9ms per frame means real-time response even on embedded hardware
5. The threat-to-enemy mapping is intuitive — security people already think in DOOM terms
6. Generated WADs are reproducible artifacts — diff two WADs to see what changed
7. It's cool. Agents should have cool interfaces.
