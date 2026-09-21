# Provenance and Build Record — Home Build

**Date:** 2026-09-20
**Part of:** Engine Specification Package (operational)
**Copyright:** © 2026 Casey Houle. All rights reserved. Confidential — not for distribution.

---

## 0. The one idea

A record made **while the work happens** is strong. The same record assembled afterward, from
memory, is weak — and it is weak precisely when it matters, which is after someone has a reason to
question it.

Everything below is mechanical and takes about twenty minutes to set up once. After that it runs by
itself and you never think about it again. That is the whole point: the record has to be a
by-product of working, not a separate chore, or it will not exist.

---

## 1. Set up once, before the first commit

### 1.1 A separate identity for this repository

Do not inherit a global git identity. Set it locally so every commit in this repo is
unambiguously yours, on your terms.

```sh
cd ~/engine            # the home build
git init
git config user.name  "Casey Houle"
git config user.email "c.j.houle75@gmail.com"     # personal, not work
```

Check it took, because a global config will silently win if you skip the local set:

```sh
git config --get user.email     # must print the personal address
```

### 1.2 Signed commits

Signing is what turns "these timestamps say I wrote it" into "these commits are cryptographically
attributable to a key I control." SSH signing is the least friction:

```sh
ssh-keygen -t ed25519 -C "engine-signing" -f ~/.ssh/engine_signing
git config gpg.format ssh
git config user.signingkey ~/.ssh/engine_signing.pub
git config commit.gpgsign true
git config tag.gpgsign true
```

To make signatures verifiable later on your own machine:

```sh
mkdir -p ~/.config/git
echo "c.j.houle75@gmail.com $(cat ~/.ssh/engine_signing.pub)" >> ~/.config/git/allowed_signers
git config gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
```

Verify it works before you rely on it — this is the same rule as everything else in this package,
a mechanism you have not watched succeed is not a mechanism:

```sh
git commit --allow-empty -m "provenance: signing check"
git log --show-signature -1        # must show a good signature
```

### 1.3 License and headers from commit one

- `LICENSE` at the root, first commit, before any code.
- Every file you author carries a one-line copyright header. Cheap, and it means no file ever exists
  in an unmarked state.
- Add it to the file template the build loop uses (spec 07), so it happens without you remembering.

### 1.4 A private remote, pushed often

Push to a private remote on a regular cadence. The value is not backup — it is that the remote holds
an **independent record of when each commit was received**, which does not depend on your local
clock and which you did not create.

```sh
git remote add origin <your private remote>
git push -u origin main
```

---

## 2. The environment record

Write this once, at the start, and update it if the machine changes. It is the file that says where
the work happened.

`PROVENANCE.md` at the repo root:

```markdown
# Provenance

This repository is developed independently:

- **Hardware:** <machine, purchased by me, not furnished by any employer or customer>
- **Network:** <personal network>
- **Accounts:** personal accounts throughout. No employer-provided credentials,
  licenses, subscriptions or infrastructure are used.
- **Time:** outside of any employer's duty hours.
- **Inputs:** the behavioral specification package (documents 00-09), authored
  by me. No source code from any other repository is copied, imported,
  adapted or referenced during this build.
- **Method:** implementation written from the specified behavior. Where the
  specification names a concrete artifact, that naming is illustrative
  (spec 06, REQ-8.2); implementation choices here are made independently.

Commits are signed. See `.build-log.md` for the contemporaneous record.

© 2026 Casey Houle. All rights reserved.
```

Commit it first, sign it, and do not rewrite it later. If something changes, append a dated entry
rather than editing history — an amended provenance file reads worse than an honest one that
records a change.

---

## 3. The build log

Append-only, one short entry per session, committed with the work. Three lines is enough.

`.build-log.md`:

```markdown
## 2026-10-04 · 19:40–22:15 · home workstation

Implemented REQ-1.1 through REQ-1.4 (failure semantics). Wrote negative
fixtures for each, watched all four fail, then pass. Receipts committed.
Nothing carried over from any other repository.
```

Rules that make it worth keeping:

- **Commit it with the work**, in the same commit, not in a batch at the end of the week. A log
  committed separately proves less than one that rides along with what it describes.
- **Keep it boring.** It is a log, not a narrative. Boring is more credible.
- **Never backfill.** A missed session gets no entry. A gap is honest; an invented entry poisons
  everything around it.
- **Say it explicitly when nothing was carried in.** The sentence is short and it is the one that
  matters.

This is the same discipline as the journal in spec 07 §2.3, serving a second purpose. Do not keep
two files — one log, both jobs.

---

## 4. The input rule

**The specification package is the only input.** That is what makes the independence claim true
rather than asserted, and it costs nothing because the package was built to be sufficient.

In practice:

- Do not open the other repository while working on this one. Not for reference, not to check how
  something was done, not "just to look."
- Do not paste from it. Ever.
- Do not clone it onto this machine. If it is not there, the question does not come up.
- If the specification is unclear, the answer is an amendment to the specification (spec 07 §5.3) —
  not a look at the old implementation. That path already exists precisely so you never need this
  one.

The amendment log does double duty here: it is a record of every point where you resolved an
ambiguity **from the spec and your own judgment**, rather than by consulting anything else.

---

## 5. What not to do

| Don't | Why |
|---|---|
| Work on it from a work laptop, "just this once" | One session on the wrong machine contaminates the record for the whole project |
| Use a work network or VPN | It is logged, by them |
| Reuse an SSH key that is registered to a work account | The key ties the commit to that account |
| Reference the other repository in a commit message or comment | It is a written link between the two |
| Rewrite history to tidy the log | The tidy version is worth less than the messy one |
| Let the assistant commit as itself | Author is you, always (spec 03, REQ-4.5) |

---

## 6. Monthly, five minutes

```sh
git log --show-signature --since="1 month ago" | grep -c "Good .* signature"   # all signed?
git log --format='%an <%ae>' | sort -u                                        # only you?
git push                                                                       # remote timestamp
```

Three commands. If the second one ever prints a name that is not yours, find out why that day, not
in six months.

---

## 7. If someone else contributes

The moment a second person commits, the single-holder position needs an agreement in writing —
before their code lands, not after. A two-line contributor agreement signed by email is enough to
keep the position clean; nothing is not.

This is not a reason to avoid collaborators. It is a reason to handle it in the five minutes before
the first pull request instead of the several hours after the hundredth.

---

## 8. Summary

| Do | When |
|---|---|
| Local identity, signing, LICENSE, `PROVENANCE.md` | Once, before the first commit |
| One log entry, committed with the work | Every session |
| Copyright header on every file authored | Automatic, via the file template |
| Push to the private remote | Every session |
| Three-command check | Monthly |

Total ongoing cost: three lines of typing per session. That is the entire price of having a record
that was made at the time rather than reconstructed after the fact.
