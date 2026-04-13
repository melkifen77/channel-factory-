# ChannelFactory — Account Roster

## Active (V1)
| Account | Niche | Status | Launch |
|---|---|---|---|
| `dr-wei/` | Sleep optimization | ✅ Fully defined | Now |

## Pending (V2 — launch after Dr. Wei hits 30+ posts + first conversion)
| Account | Niche | Persona | Status |
|---|---|---|---|
| `rabbi/` | Personal finance / wealth building | Elder wisdom, "we vs you" framing | Character spec ready |
| `swiss-banker/` | Wealth preservation / private banking | Cold European authority, Jean Dujardin style | Character spec ready |
| `elite-insider/` | Elite financial thinking / mindset | Implied proximity to power, insider perspective | Character spec ready |

## Adding a New Account

Every new account needs:
1. `character-spec.json` — persona, voice, system_prompt, affiliate_strategy, hook_system
2. `brand-voice-guidelines.md` — the human-readable guidelines doc
3. `hook-library.md` — seed hook templates + body structures for this niche

The n8n pipeline is account-agnostic — it reads the character spec and runs the same workflow for any account. Adding a new account = adding a new character spec + connecting platform accounts in Postiz.

## Niche Expansion Strategy

Each niche combination: **authority archetype + wisdom tradition + platform-native angle**

| Account | Authority | Tradition | Angle |
|---|---|---|---|
| Dr. Wei | Medical physician | TCM / Eastern medicine | Ancient + modern synthesis |
| Rabbi | Cultural/religious elder | Jewish financial wisdom | "We" insider community |
| Swiss Banker | Private banking professional | European wealth preservation | Cold control vs. chaos |
| Elite Insider | Proximity to HNW circles | Observed elite behavior | Implied insider knowledge |

Future accounts can follow the same pattern in other niches (fitness, relationships, longevity, productivity).
