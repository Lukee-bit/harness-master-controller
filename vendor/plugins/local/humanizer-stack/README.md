# humanizer-stack

A two-pass pipeline for removing the signs of AI writing from outward-facing text,
packaged as [Claude Code Skills](https://code.claude.com/docs/en/skills).

Most humanizers only fix words. That is the easy half, and it is the half that is
decaying fastest. This repo pairs a surface pass with a structural pass, because the
research says structure is where the durable fingerprint lives.

> **Free community.** I build tools like this in the open inside the
> [Jens AI Community](https://www.skool.com/jens-ai-community-1306), a free Skool group
> for putting AI to work in your business. If this repo is useful to you, come join us:
> https://www.skool.com/jens-ai-community-1306

## Why two passes

The [StoryScope study](https://github.com/jenna-russell/storyscope) (Russell et al.,
2026) classified 61,608 stories from humans and five LLMs using only discourse-level
features, with every style feature withheld. It detected AI text at **93.2% F1**.

Then the authors ran AI text through LAMP, a professional span-level rewriting system
that strips cliche, purple prose, and redundant exposition. Functionally, a very good
surface humanizer.

Detection dropped **1.6 points**.

Meanwhile the surface layer is eroding on its own. GPT 5.4 already cut its em-dash
usage sharply, and fine-tuning drops stylistic detection from 97% to 3%. Word-level
tells are a moving target. Structural tells require structural rewrites.

So: pass 1 fixes the words. Pass 2 fixes the shape. Run them in that order.

## What is in here

```
skills/
  humanizer/                     Pass 1: words and phrasing
    SKILL.md
    references/copy-tells.md     Copy-specific tells (em dash, hype vocab, antithesis)
  structural-humanizer/          Pass 2: discourse structure
    SKILL.md
    references/
      storyscope-findings.md     The study distilled: 30 core features with rates
      genre-calibration.md       Which audits apply per genre
    scripts/structural_scan.py   Deterministic scanner for grep-able structural tells
scripts/
  copy_scan.py                   Deterministic scanner for mechanical copy tells
docs/
  PIPELINE.md                    How the passes chain, and what each one owns
```

### Pass 1: `humanizer`

Vocabulary, punctuation, and phrasing. Inflated symbolism, promotional language,
superficial "-ing" analyses, vague attributions, em dash overuse, rule of three, AI
vocabulary, negative parallelism. Built from Wikipedia's
[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).

The `copy-tells.md` reference adds the tells that show up specifically in public copy,
ranked by a 3.2M-post Reddit analysis of what people actually flag.

### Pass 2: `structural-humanizer`

Six audits run one at a time, because aspect-based checking found 95% of issues in the
study's own pipeline against 68% for a single combined pass:

1. **Theme explicitness.** AI states its lesson. Narrator explains the theme 77% of the
   time against 52% for humans.
2. **Structural tidiness.** Single-track, everything resolved. Humans digress and leave
   threads open.
3. **Emotion mode.** The largest gap in the study. AI performs emotion through the body
   81% of the time against 38% for humans. Humans just name the feeling.
4. **Reference specificity.** Humans name real things (47% against 24%). AI stays at
   vague allusion.
5. **Reader engagement.** Humans acknowledge the reader. AI writes as though no one is
   watching.
6. **Shape convergence.** Does this piece have the same skeleton as your last three?

## The trap

Do not trade one default for another. The study's deepest finding is convergence: all
five models occupy one tight region of structural space while humans are dispersed.
Rarity is the human signal.

If every piece now opens mid-scene, names three feelings, and ends unresolved, you have
built a new detectable cluster. Pick one or two interventions per piece, vary them
across pieces, and be able to say why this piece got this shape.

## Install

```bash
git clone https://github.com/NulightJens/humanizer-stack.git
cd humanizer-stack
./install.sh
```

This symlinks both skills into `~/.claude/skills/`, so updates land with a `git pull`.
Pass `--copy` if you would rather have independent copies than symlinks.

To install manually, copy `skills/humanizer` and `skills/structural-humanizer` into
`~/.claude/skills/` (user-level) or `.claude/skills/` (project-level).

## Use

In Claude Code, the skills trigger on intent:

```
humanize this post
de-slop this lesson
run the structural pass on draft.md
```

Run the surface pass first, then the structural pass. `docs/PIPELINE.md` covers the
order and what each layer owns.

### Scanners

Both scanners are deterministic and hook-friendly. They catch the pattern-matchable
slice only, and neither replaces the judgment work in the skills.

```bash
python3 scripts/copy_scan.py draft.md
python3 skills/structural-humanizer/scripts/structural_scan.py draft.md

python3 scripts/copy_scan.py --json draft.md      # machine-readable
python3 scripts/copy_scan.py --strict draft.md    # exit 1 on any hit
cat draft.md | python3 scripts/copy_scan.py -     # stdin
```

Mark a line `copy-ignore` to suppress an intentional usage.

## Honest limits

- **StoryScope studied roughly 5,000-word fiction.** Applying it to short nonfiction is
  an inference, not a result the paper establishes. The subset that transfers most
  cleanly is audits 1, 3, 4, and 6.
- **Nothing here makes text undetectable, and that is not the goal.** The goal is
  writing that reads as though a person with a specific point of view wrote it, because
  a person did.
- **The scanners catch maybe half.** Cadence, formulaic shape, and polished-but-empty
  filler are only visible to a human reader.
- **Audit 3 contradicts standard writing advice.** "Show, don't tell" is now a machine
  signature. That is what the data says, and it is worth sitting with before applying.

## Attribution

Built on work by [@blader](https://github.com/blader/humanizer) (MIT),
[jcarterjohnson](https://github.com/jcarterjohnson/vibecoded-design-tells) (MIT), and
Wikipedia's WikiProject AI Cleanup (CC BY-SA 4.0). Grounded in Russell et al. 2026.

Full breakdown with license obligations: [ATTRIBUTION.md](ATTRIBUTION.md).

## License

MIT for this repository's own work. Portions carry upstream terms, including CC BY-SA
4.0 material with share-alike obligations. See [ATTRIBUTION.md](ATTRIBUTION.md) before
redistributing.
