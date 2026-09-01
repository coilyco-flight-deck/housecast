# Overlay

How estate-specific acts reach a seat without leaving the shipped roster.

## Why it exists

The core roster must be runnable by a stranger, so a test refuses any act naming a tool only
one estate has. That keeps a bundle portable, and it is why the sharpest acts had nowhere to
live: `aosguard ops kubectl` is most of what the sysadmin own side does, and it cannot ship.

## The two rules

**Append, never replace.** A seat on a host carrying both gets six acts per attribute,
three portable and three estate. Replacing would give it three and drop the portable
fallback, which is the half that still works when the estate tool is absent.

**Per boundary side.** An appended boundary act names its side. Owning, scoping, and
deferring are three different acts, and `scoped` is a real third position - an overlay
knowing only two would silently drop a scoped seat's acts.

## The format

```yaml
overlay: kai-estate
roles:
  sysadmin:
    - {tool: aosguard, text: "...get -o wide and paste the before state"}
personalities:
  outward:
    - {tool: WebSearch, text: "...and one other modality, naming which you ran"}
boundaries:
  modify-live-backend:
    own:   [{tool: aosguard, text: "...rollout status, then the same get again"}]
    defer: [{tool: SendMessage, text: "...the sysadmin seat while it is live"}]
```

`housecast.overlay.apply(roster, path)` returns a new roster, never mutating its input.
Acts and nothing else, so redefining a role, a personality, or a meld is unexpressible rather
than forbidden. Every name is checked: a misspelled role raises rather than appending nothing,
because an act that never arrives looks like one nobody wrote.
