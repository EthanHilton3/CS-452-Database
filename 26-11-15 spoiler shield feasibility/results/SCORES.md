# Spoiler classifier scores

Labels: 170 comments, **0 reviewed by Ethan**, 170 still Claude drafts (PROVISIONAL)

Simulated viewers at positions S1E1..S2E11 = 23 positions x 170 comments.

| Run | Spoilers caught | Safe comments blurred | Spoiler/no-spoiler recall | precision | Exact episode | Within 1 ep | Under-called | Cost | Cost per 1k comments |
|---|---|---|---|---|---|---|---|---|---|
| keyword | 36% | 13% | 70% | 66% | 50% | 51% | 54 | $0.0000 | $0.000 |
| none_gpt-6-luna | 69% | 3% | 71% | 96% | 69% | 72% | 32 | $0.0238 | $0.140 |
| sheets_gpt-6-luna | 77% | 3% | 76% | 93% | 81% | 84% | 24 | $0.0155 | $0.091 |
| sheets_gpt-6-luna_low | 76% | 3% | 74% | 96% | 81% | 84% | 24 | $0.0085 | $0.050 |
| sheets_gpt-6-luna_low_ctx | 74% | 6% | 70% | 81% | 75% | 76% | 28 | $0.0095 | $0.056 |
| sheets_gpt-6-luna_none | 60% | 7% | 56% | 79% | 72% | 74% | 31 | $0.0041 | $0.024 |
| sheets_gpt-6-luna_none_ctx | 68% | 8% | 68% | 80% | 74% | 76% | 28 | $0.0063 | $0.037 |
| sheets_gpt-6-sol_low | 75% | 2% | 71% | 92% | 81% | 82% | 27 | $0.1271 | $0.747 |
| tmdb_gpt-6-luna | 74% | 4% | 70% | 94% | 72% | 77% | 29 | $0.0218 | $0.128 |

## General threads only (50 comments)

The realistic case: browsing r/andor (not an episode megathread) partway through the show.

| Run | Spoilers caught | Safe comments blurred | Exact episode | Under-called |
|---|---|---|---|---|
| keyword | 39% | 15% | 54% | 12 |
| none_gpt-6-luna | 77% | 4% | 76% | 4 |
| sheets_gpt-6-luna | 90% | 6% | 88% | 2 |
| sheets_gpt-6-luna_low | 91% | 4% | 90% | 2 |
| sheets_gpt-6-luna_low_ctx | 88% | 15% | 78% | 2 |
| sheets_gpt-6-luna_none | 70% | 10% | 82% | 4 |
| sheets_gpt-6-luna_none_ctx | 70% | 14% | 78% | 4 |
| sheets_gpt-6-sol_low | 99% | 7% | 88% | 1 |
| tmdb_gpt-6-luna | 86% | 2% | 88% | 2 |

Under-called = the model said the comment reveals an earlier episode than it does (or nothing), so some viewers would see a spoiler.

<details><summary>keyword: 54 under-called</summary>

- #0: label 3, predicted 0 — 
- #3: label 3, predicted 2 — Team
- #12: label 5, predicted 2 — Time
- #16: label 25, predicted 13 — Great
- #19: label 6, predicted 0 — 
- #21: label 6, predicted 0 — 
- #25: label 7, predicted 0 — 
- #26: label 8, predicted 0 — 
- #28: label 7, predicted 0 — 
- #33: label 10, predicted 0 — 
- #37: label 11, predicted 2 — Time
- #40: label 11, predicted 0 — 
- #41: label 11, predicted 0 — 
- #43: label 12, predicted 0 — 
- #49: label 13, predicted 9 — Level
- #54: label 14, predicted 8 — Chandrila
- #60: label 15, predicted 13 — Inside
- #62: label 15, predicted 1 — Brasso
- #63: label 15, predicted 0 — 
- #64: label 15, predicted 0 — 
- #65: label 14, predicted 4 — Dedra
- #67: label 16, predicted 0 — 
- #78: label 18, predicted 0 — 
- #79: label 18, predicted 9 — Gorst
- #80: label 18, predicted 0 — 
- #83: label 18, predicted 4 — Cinta
- #85: label 19, predicted 0 — 
- #86: label 21, predicted 5 — Interest
- #91: label 20, predicted 13 — Tarkin
- #92: label 20, predicted 4 — Dedra
- #93: label 20, predicted 13 — Following
- #100: label 20, predicted 18 — Plaza
- #101: label 15, predicted 2 — Luthen
- #102: label 22, predicted 4 — Jung
- #103: label 22, predicted 0 — 
- #106: label 22, predicted 4 — Kleya
- #109: label 23, predicted 4 — Coruscant, Kleya
- #110: label 23, predicted 0 — 
- #113: label 20, predicted 12 — Death
- #117: label 24, predicted 18 — Bail
- #118: label 24, predicted 0 — 
- #119: label 24, predicted 0 — 
- #121: label 22, predicted 2 — Luthen
- #122: label 25, predicted 13 — Following
- #129: label 24, predicted 18 — Bail, Organa
- #130: label 22, predicted 4 — Kleya
- #132: label 22, predicted 2 — Luthen
- #133: label 22, predicted 4 — Dedra, Kleya
- #135: label 22, predicted 14 — Yavin
- #136: label 22, predicted 14 — Yavin
- #163: label 18, predicted 12 — Death
- #166: label 16, predicted 3 — Wilmon
- #167: label 18, predicted 2 — Luthen
- #169: label 16, predicted 4 — Dedra

</details>

<details><summary>none_gpt-6-luna: 32 under-called</summary>

- #0: label 3, predicted 0 — 
- #12: label 5, predicted 0 — 
- #19: label 6, predicted 3 — definitely got shot and dropped like a stone
- #21: label 6, predicted 0 — reaction to a line, with no plot detail
- #24: label 7, predicted 0 — 
- #25: label 7, predicted 0 — 
- #28: label 7, predicted 3 — “Hang.”
- #30: label 8, predicted 0 — 
- #33: label 10, predicted 0 — 
- #37: label 11, predicted 0 — 
- #39: label 8, predicted 0 — 
- #43: label 12, predicted 0 — 
- #54: label 14, predicted 0 — 
- #57: label 14, predicted 4 — her political and funding-wise resistance
- #60: label 15, predicted 13 — the girl’s mother told her to go inside
- #63: label 15, predicted 0 — 
- #64: label 15, predicted 0 — 
- #67: label 16, predicted 0 — 
- #78: label 18, predicted 10 — removing the listening device
- #79: label 18, predicted 10 — Lonni ... presumably to tell Luthen
- #80: label 18, predicted 13 — pull a gun; the theft
- #83: label 18, predicted 15 — Vel ... making out
- #85: label 19, predicted 15 — looked at each other in the elevator
- #91: label 20, predicted 0 — 
- #101: label 15, predicted 7 — Luthen implies they have to kill him
- #102: label 22, predicted 12 — Jung was already dead
- #103: label 22, predicted 0 — unspecified, explicitly speculative sibling theory
- #118: label 24, predicted 10 — ISB field agent defecting to the Rebellion
- #121: label 22, predicted 0 — 
- #129: label 24, predicted 0 — 
- #166: label 16, predicted 0 — 
- #169: label 16, predicted 15 — moment between Dedra and Syril

</details>

<details><summary>sheets_gpt-6-luna: 24 under-called</summary>

- #0: label 3, predicted 0 — 
- #12: label 5, predicted 4 — the heist ain’t happening tonight
- #19: label 6, predicted 0 — 
- #21: label 6, predicted 0 — “thank you for trying”
- #24: label 7, predicted 0 — designed the Niamos beach
- #25: label 7, predicted 0 — 
- #28: label 7, predicted 3 — “Hang.”
- #30: label 8, predicted 0 — “Melshi from Rouge One”
- #33: label 10, predicted 0 — References the Imitation Game scene
- #37: label 11, predicted 0 — No specific plot detail
- #40: label 11, predicted 0 — 
- #41: label 11, predicted 7 — Vel and Cinta are staking out his home
- #54: label 14, predicted 0 — 
- #57: label 14, predicted 7 — “funding-wise resistance”
- #60: label 15, predicted 0 — 
- #63: label 15, predicted 0 — 
- #64: label 15, predicted 0 — 
- #67: label 16, predicted 0 — 
- #85: label 19, predicted 18 — could kiss but don't
- #103: label 22, predicted 7 — siblings surviving the same genocide
- #110: label 23, predicted 0 — “she” and “the leak” are unidentified
- #118: label 24, predicted 10 — “ISB field agents defecting to the Rebellion”
- #122: label 25, predicted 0 — 
- #169: label 16, predicted 14 — moment between Dedra and Syria

</details>

<details><summary>sheets_gpt-6-luna_low: 24 under-called</summary>

- #0: label 3, predicted 0 — 
- #21: label 6, predicted 0 — 
- #24: label 7, predicted 0 — 
- #25: label 7, predicted 0 — 
- #28: label 7, predicted 3 — “Hang.”
- #30: label 8, predicted 0 — Melshi from Rogue One
- #33: label 10, predicted 0 — 
- #37: label 11, predicted 0 — 
- #40: label 11, predicted 0 — 
- #41: label 11, predicted 7 — Val and Cintra are staking out his home
- #43: label 12, predicted 0 — 
- #54: label 14, predicted 0 — comments on score
- #57: label 14, predicted 7 — resistance, funding-wise
- #60: label 15, predicted 0 — 
- #63: label 15, predicted 0 — 
- #64: label 15, predicted 0 — 
- #67: label 16, predicted 0 — 
- #80: label 18, predicted 13 — pull a gun; pushing past him
- #85: label 19, predicted 18 — pure love ... could kiss
- #103: label 22, predicted 0 — 
- #110: label 23, predicted 0 — No character or event identifies the alleged death
- #118: label 24, predicted 10 — An ISB field agent defecting to the Rebellion
- #121: label 22, predicted 0 — 
- #169: label 16, predicted 14 — between Dedra and Syria

</details>

<details><summary>sheets_gpt-6-luna_low_ctx: 28 under-called</summary>

- #0: label 3, predicted 1 — Dead is dead.
- #10: label 3, predicted 0 — 
- #11: label 4, predicted 0 — 
- #12: label 5, predicted 0 — 
- #18: label 6, predicted 0 — 
- #24: label 7, predicted 0 — 
- #25: label 7, predicted 0 — 
- #28: label 7, predicted 0 — 
- #30: label 8, predicted 0 — 
- #37: label 11, predicted 7 — the scene ... got arrested
- #41: label 11, predicted 7 — Cassian was a loose end; Vel should kill him
- #43: label 12, predicted 0 — 
- #49: label 13, predicted 0 — 
- #54: label 14, predicted 0 — 
- #57: label 14, predicted 7 — funding-wise resistance
- #63: label 15, predicted 0 — 
- #64: label 15, predicted 0 — 
- #65: label 14, predicted 0 — 
- #67: label 16, predicted 0 — 
- #86: label 21, predicted 19 — the place he needs to be wasn’t with her
- #91: label 20, predicted 17 — Tarkin did kill his dad
- #101: label 15, predicted 0 — 
- #103: label 22, predicted 0 — 
- #110: label 23, predicted 0 — speculates that she dies
- #117: label 24, predicted 21 — Bail almost handed Mon to the ISB
- #118: label 24, predicted 10 — ISB field agent defecting
- #166: label 16, predicted 0 — 
- #169: label 16, predicted 0 — 

</details>

<details><summary>sheets_gpt-6-luna_none: 31 under-called</summary>

- #0: label 3, predicted 0 — Dead is dead
- #3: label 3, predicted 0 — Sgt. Kostek ... corpo assault team
- #12: label 5, predicted 4 — this heist ain’t happening tonight
- #21: label 6, predicted 0 — “thank you for trying” lacks plot context
- #24: label 7, predicted 0 — Niamos beach design
- #25: label 7, predicted 0 — “she’ll probably never know” is unspecified
- #28: label 7, predicted 0 — “Hang” is too contextless to identify a plot reveal
- #33: label 10, predicted 0 — 
- #37: label 11, predicted 0 — 
- #40: label 11, predicted 0 — ship sprouted laser wings
- #43: label 12, predicted 0 — Space Gestapo romance
- #49: label 13, predicted 0 — criticism of dialogue, scenes, and ship
- #54: label 14, predicted 0 — 
- #57: label 14, predicted 0 — 
- #60: label 15, predicted 0 — 
- #63: label 15, predicted 0 — 
- #64: label 15, predicted 0 — 
- #67: label 16, predicted 0 — comparing Saw
- #80: label 18, predicted 0 — no identifiable Andor event
- #83: label 18, predicted 0 — speculation about Vel and Cinta
- #85: label 19, predicted 0 — relationship interpretation, no event identified
- #92: label 20, predicted 0 — 
- #101: label 15, predicted 0 — 
- #103: label 22, predicted 0 — 
- #106: label 22, predicted 0 — 
- #110: label 23, predicted 22 — She dies, then the Empire thinks the leak is sealed.
- #118: label 24, predicted 0 — 
- #121: label 22, predicted 0 — Kenari and ... flashback
- #122: label 25, predicted 0 — She had valuable intel
- #167: label 18, predicted 0 — 
- #169: label 16, predicted 0 — 

</details>

<details><summary>sheets_gpt-6-luna_none_ctx: 28 under-called</summary>

- #0: label 3, predicted 1 — Dead is dead.
- #11: label 4, predicted 0 — 
- #12: label 5, predicted 0 — 
- #16: label 25, predicted 0 — 
- #18: label 6, predicted 0 — 
- #24: label 7, predicted 0 — 
- #33: label 10, predicted 0 — 
- #37: label 11, predicted 7 — the way he got arrested
- #41: label 11, predicted 7 — Vel and Cinta staking out Cassian’s home
- #43: label 12, predicted 0 — 
- #49: label 13, predicted 0 — 
- #54: label 14, predicted 0 — 
- #57: label 14, predicted 0 — 
- #63: label 15, predicted 0 — 
- #64: label 15, predicted 0 — 
- #67: label 16, predicted 0 — 
- #83: label 18, predicted 0 — speculates Vel might be pregnant
- #85: label 19, predicted 0 — 
- #86: label 21, predicted 19 — Bix knows he needs to leave her
- #91: label 20, predicted 17 — Tarkin did kill his dad
- #103: label 22, predicted 0 — 
- #110: label 23, predicted 22 — She's the loose end. She dies
- #117: label 24, predicted 0 — 
- #118: label 24, predicted 23 — agents defecting to the Rebellion
- #122: label 25, predicted 0 — 
- #129: label 24, predicted 0 — 
- #166: label 16, predicted 0 — 
- #169: label 16, predicted 0 — 

</details>

<details><summary>sheets_gpt-6-sol_low: 27 under-called</summary>

- #0: label 3, predicted 0 — 
- #11: label 4, predicted 0 — 
- #12: label 5, predicted 0 — 
- #19: label 6, predicted 0 — 
- #24: label 7, predicted 0 — 
- #25: label 7, predicted 0 — 
- #26: label 8, predicted 7 — You can't stay, and I can't go!
- #28: label 7, predicted 3 — Hang.
- #30: label 8, predicted 0 — 
- #33: label 10, predicted 0 — 
- #37: label 11, predicted 0 — 
- #39: label 8, predicted 0 — 
- #41: label 11, predicted 7 — want to kill him because he had seen his face; Vel and Cinta staking out his mother's home
- #43: label 12, predicted 0 — 
- #46: label 12, predicted 0 — 
- #54: label 14, predicted 0 — 
- #57: label 14, predicted 7 — Mon ... political and funding-wise resistance
- #60: label 15, predicted 0 — 
- #63: label 15, predicted 0 — 
- #64: label 15, predicted 0 — 
- #67: label 16, predicted 0 — 
- #85: label 19, predicted 0 — 
- #91: label 20, predicted 17 — Tarkin did kill his dad
- #103: label 22, predicted 2 — siblings; surviving the same genocide
- #110: label 23, predicted 0 — 
- #118: label 24, predicted 10 — ISB field agent defecting to the Rebellion
- #169: label 16, predicted 14 — “turn off the lights” moment between Dedra and Syria

</details>

<details><summary>tmdb_gpt-6-luna: 29 under-called</summary>

- #0: label 3, predicted 0 — 
- #10: label 3, predicted 0 — 
- #11: label 4, predicted 0 — 
- #12: label 5, predicted 0 — 
- #19: label 6, predicted 0 — 
- #24: label 7, predicted 0 — 
- #25: label 7, predicted 0 — 
- #30: label 8, predicted 0 — 
- #33: label 10, predicted 0 — 
- #37: label 11, predicted 0 — 
- #39: label 8, predicted 0 — 
- #40: label 11, predicted 0 — ship visual only
- #54: label 14, predicted 0 — 
- #57: label 14, predicted 4 — her resistance and funding
- #60: label 15, predicted 0 — Not enough plot detail
- #62: label 15, predicted 14 — Brasso wasn't coming; he was dead
- #63: label 15, predicted 0 — A joke, no plot detail
- #64: label 15, predicted 0 — General commentary about power
- #65: label 14, predicted 13 — Dedra and Syril pretending to be dating
- #67: label 16, predicted 0 — Comparison to another film and character
- #80: label 18, predicted 6 — “they’re going to advertise they did it anyways”
- #85: label 19, predicted 18 — “looked at each other in the elevator”
- #91: label 20, predicted 0 — 
- #101: label 15, predicted 14 — blackmail to keep Tay quiet
- #103: label 22, predicted 1 — siblings surviving the same genocide
- #110: label 23, predicted 22 — She dies; the Empire thinks the leak is sealed
- #118: label 24, predicted 10 — ISB field agents defecting to the Rebellion
- #121: label 22, predicted 0 — 
- #166: label 16, predicted 0 — 

</details>

