# Edge Case — Modal Cancel Re-trigger on OthersSelect

## The Problem

When a user selects a modal-triggered item (Boiled Eggs, Syabhale, Chicken Sausage, Buff Sausage) from `OthersSelect`:

1. User selects "Boiled Eggs" → modal opens
2. User cancels the modal
3. Dropdown visually stays on "Boiled Eggs"
4. User selects "Boiled Eggs" again
5. `OthersSelect.callback` fires with `self.values = []` → `chosen = None`
6. Modal does **not** re-open — nothing happens

The root cause is Discord firing the callback with an empty values list when the dropdown is re-selected after a modal cancel, rather than the selected item's value.

---

## Suggestions

### Option 1 — Silently ignore `None` (simplest)

If `chosen` is `None`, return early without touching `self.votes`. The existing vote (if any) stays intact.

```python
chosen = self.values[0] if self.values else None
if chosen is None:
    await interaction.response.defer_update()
    return
```

- No error shown, no vote change
- Silent — user gets no feedback that their cancel was registered
- Works correctly when user had a prior order (preserves it)

---

### Option 2 — Ephemeral error on `None`

Same early return but with a visible ephemeral message.

```python
if chosen is None:
    await interaction.response.send_message(
        "⚠️ No item selected.", ephemeral=True
    )
    return
```

- Also fires when user deliberately deselects — may feel noisy

---

### Option 3 — Re-open modal on `None` using `pending_modal` staging key

Store the chosen modal item into a temporary `pending_modal` key before opening the modal. If `chosen` is `None` on the next callback, read `pending_modal` to know which modal to re-open.

```python
# Before opening modal — stage the item
view.votes[uid]["pending_modal"] = chosen
await interaction.response.send_modal(ModalForBoiledEggs(view))
return

# On None — re-open using staged value
if chosen is None:
    pending = view.votes.get(uid, {}).get("pending_modal")
    if pending == "Boiled Eggs":
        await interaction.response.send_modal(ModalForBoiledEggs(view))
        return
    if pending == "Syabhale":
        await interaction.response.send_modal(ModalForSyabhale(view))
        return
    if pending in ("Chicken Sausage", "Buff Sausage"):
        await interaction.response.send_modal(ModalForSausages(view, pending))
        return
    await interaction.response.defer_update()
    return
```

On successful modal submit, clear `pending_modal`:
```python
self.khaja_view.votes[interaction.user.id].pop("pending_modal", None)
```

- Most intuitive UX — modal re-opens as expected
- Slightly more state to manage (`pending_modal` key in votes dict)
- Need to ensure `pending_modal` is excluded from summary logic

---

## User Input

> "Or, if a user selects an item again after selecting, modal pop, cancelling.. the modal should pop up again"

Preferred direction is **Option 3** — re-opening the modal on cancel is the expected behavior. Decision on implementation deferred.

---

## Status

Pending — decision deferred. To be revisited.
