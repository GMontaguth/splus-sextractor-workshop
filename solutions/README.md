# Solutions

Worked versions of every configuration file, with the reasoning in the comments.

**Use these if you are stuck for more than ten minutes.** Being stuck is not the
exercise.

But do the thinking first. Copying a config file takes ten seconds and teaches you
nothing. The value is in knowing *why* `SATUR_LEVEL` is 1606 and not 50000.

| File | For |
|---|---|
| `default.sex` | the main run |
| `default.param` | the science catalog columns |
| `prepsfex.param` | SExtractor pass 1 — the PSFEx feed. Note `VIGNET`. |
| `default.psfex` | PSFEx |
| `final.param` | SExtractor pass 2 — adds `SPREAD_MODEL`, `MAG_PSF` |

Two markers in `default.sex`:

- **`[FACT]`** — this came out of the image header. It is not a choice. Get it wrong
  and things break quietly.
- **`[DECISION]`** — this is a choice. There is no correct value. There is a value
  correct for your science, and you should be able to say what it is and why.

The whole point of the session is learning to tell those two apart.
