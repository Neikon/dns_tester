# Flatpak Repository Setup — Replicable Guide for Agents

This document describes exactly how the dual Flatpak OSTree repositories (`beta` for `develop`, `stable` for `main`) were created for DNS Tester. Any agent should be able to replicate it in another project by following the steps below.

## 1. Goal

- Host two Flatpak repositories on GitHub Pages from a single `gh-pages` branch:
  - `https://<user>.github.io/<repo>/beta/` → built from `develop` (pre-releases)
  - `https://<user>.github.io/<repo>/stable/` → built from `main` (stable releases)
- Each push to `develop` or `main`:
  - Builds a Flatpak bundle via `flatpak-builder`
  - Generates an OSTree repository (`repo/`)
  - Generates a `.flatpakrepo` file and `index.html`
  - Deploys to `gh-pages/<channel>/`
  - (For `develop` only) Publishes a GitHub pre-release tagged with the app version

Users install with (signed repositories — no `--no-gpg-verify` needed):

```bash
flatpak remote-add --if-not-exists dns_tester-beta https://neikon.github.io/dns_tester/beta/dns_tester.flatpakrepo
flatpak install dns_tester-beta es.neikon.dns_tester

flatpak remote-add --if-not-exists dns_tester-stable https://neikon.github.io/dns_tester/stable/dns_tester.flatpakrepo
flatpak install dns_tester-stable es.neikon.dns_tester
```

## 2. Prerequisites

- Flatpak manifest (e.g. `es.neikon.dns_tester.json`) with:
  - `id`, `runtime` (e.g. `org.gnome.Platform` `50`), `sdk`, `command`, `finish-args`
  - At least one `modules` entry for the app built with `meson`
  - **Important:** The manifest in the repository may contain a non-portable source like `file:///home/...` for local development. The CI workflow patches it to `type: dir` / `path: .` at build time. If you want Flathub compatibility, use a `git` source pointing to `https://github.com/<user>/<repo>.git` instead.

- Version is defined in `meson.build` as `version: 'YY.MM.DD.hhmm'` and mirrored in `src/main.py` (AboutDialog) and `data/*.metainfo.xml.in`. The workflow reads `meson.build` to tag releases.

- GitHub repository with `develop` and `main` branches following GitFlow.

## 3. GitHub Actions Workflow

File: `.github/workflows/flatpak.yml`

### 3.1 Triggers and Permissions

```yaml
name: Flatpak
on:
  push:
    branches: [main, develop]
  workflow_dispatch:

permissions:
  contents: write  # needed for gh-pages push and softprops/action-gh-release
```

`contents: write` is required — without it, both `peaceiris/actions-gh-pages` and `softprops/action-gh-release` fail with `403`.

### 3.2 Install Dependencies and Import GPG

Ubuntu runners do **not** ship `flatpak-builder`. Install it, add Flathub, and import the signing key:

```yaml
- name: Install Flatpak and flatpak-builder
  run: |
    sudo apt-get update
    sudo apt-get install -y flatpak flatpak-builder xvfb

- name: Add Flathub remote
  run: |
    sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
    sudo flatpak install -y --noninteractive flathub org.gnome.Platform//50 org.gnome.Sdk//50 || true

- name: Import GPG key for Flatpak repo signing
  run: |
    echo "${{ secrets.FLATPAK_GPG_PRIVATE_KEY }}" | gpg --batch --import
    echo "${{ secrets.FLATPAK_GPG_KEY_ID }}:6:" | gpg --import-ownertrust
    gpg --list-keys
```

Pre-installing `Platform` and `Sdk` avoids `Flatpak system operation Deploy not allowed for user` when `flatpak-builder --install-deps-from=flathub` runs as non-root.

The GPG key is a 2048-bit RSA key (`DNS Tester Flatpak <flatpak@neikon.es>`) stored as repository secrets:
- `FLATPAK_GPG_PRIVATE_KEY` — ASCII-armored private key (`gpg --armor --export-secret-keys`)
- `FLATPAK_GPG_KEY_ID` — key fingerprint (`C54B2799388C8DC49EC61979...`)
- `FLATPAK_GPG_PUBLIC_B64` — base64-encoded public key (`gpg --export | base64 -w0`) for `GPGKey=` in the `.flatpakrepo`

Generate once locally:

```bash
cat > /tmp/genkey <<'EOF'
%no-protection
Key-Type: RSA
Key-Length: 2048
Name-Real: DNS Tester Flatpak
Name-Email: flatpak@neikon.es
Expire-Date: 0
EOF
GNUPGHOME=/tmp/gpg gpg --batch --generate-key /tmp/genkey
gpg --armor --export-secret-keys <ID> > private.asc
gpg --export <ID> | base64 -w0 > public.b64
gh secret set FLATPAK_GPG_PRIVATE_KEY < private.asc
gh secret set FLATPAK_GPG_KEY_ID --body "<ID>"
gh secret set FLATPAK_GPG_PUBLIC_B64 < public.b64
```

### 3.3 Patch Manifest for CI

```yaml
- name: Patch manifest for CI build
  run: |
    python3 -c "
    import json, pathlib
    p = pathlib.Path('es.neikon.dns_tester.json')
    data = json.loads(p.read_text())
    for mod in data.get('modules', []):
        if isinstance(mod, dict) and mod.get('name') == 'dns_tester':
            mod['sources'] = [{'type': 'dir', 'path': '.'}]
    p.write_text(json.dumps(data, indent=4))
    print(p.read_text())
    "
```

This replaces any `git`/`file` source with a local `dir` source so the builder uses the checked-out commit directly.

### 3.4 Build

```yaml
- name: Build Flatpak bundle
  uses: flatpak/flatpak-github-actions/flatpak-builder@v6
  with:
    bundle: dns_tester.flatpak
    manifest-path: es.neikon.dns_tester.json
    cache-key: flatpak-builder-${{ github.sha }}
    repository-name: flathub
    repository-url: https://flathub.org/repo/flathub.flatpakrepo
    cache: true
    branch: ${{ github.ref == 'refs/heads/main' && 'stable' || 'beta' }}
    gpg-sign: ${{ secrets.FLATPAK_GPG_KEY_ID }}
```

`branch` sets the OSTree branch inside the repository (`beta` vs `stable`). The action internally runs:

```
flatpak-builder --repo=repo --install-deps-from=flathub --force-clean --default-branch=<branch> ...
flatpak build-bundle repo dns_tester.flatpak ...
```

The `repo/` directory is the OSTree repository; `dns_tester.flatpak` is the single-file bundle.

### 3.5 Generate Repository Metadata

```yaml
- name: Generate Flatpak repository metadata
  run: |
    if [ "${{ github.ref }}" = "refs/heads/main" ]; then
      CHANNEL="stable"; TITLE="DNS Tester Stable"; COMMENT="DNS Tester stable channel (main)"; GIT_BRANCH="main"
    else
      CHANNEL="beta"; TITLE="DNS Tester Beta"; COMMENT="DNS Tester beta channel (develop)"; GIT_BRANCH="develop"
    fi
    REPO_URL="https://neikon.github.io/dns_tester/${CHANNEL}/"
    GPGKEY=$(echo "${{ secrets.FLATPAK_GPG_PUBLIC_B64 }}" | tr -d '\n')
    cat > repo/dns_tester.flatpakrepo <<EOF
    [Flatpak Repo]
    Title=${TITLE}
    Url=${REPO_URL}
    Homepage=https://github.com/Neikon/dns_tester
    Comment=${COMMENT}
    Icon=https://raw.githubusercontent.com/Neikon/dns_tester/${GIT_BRANCH}/data/icons/hicolor/scalable/apps/es.neikon.dns_tester.svg
    GPGKey=${GPGKEY}
    EOF
    cat > repo/index.html <<EOF
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>${TITLE} Flatpak Repository</title></head>
    <body><h1>${TITLE} Flatpak Repository</h1>
    <p>URL: <code>${REPO_URL}</code></p>
    <p>Signed repo:</p>
    <pre>flatpak remote-add --if-not-exists dns_tester-${CHANNEL} ${REPO_URL}dns_tester.flatpakrepo
    flatpak install dns_tester-${CHANNEL} es.neikon.dns_tester</pre>
    </body></html>
    EOF
    cp dns_tester.flatpak repo/ || true
    ls -lh repo/
```

Key points:
- `Url` **must** end with `/` and point to the GitHub Pages location for that channel.
- `GPGKey` is the base64-encoded **public** key (raw, not ASCII-armored) from `gpg --export | base64 -w0`. The OSTree commits are signed with the corresponding private key via `gpg-sign: ${{ secrets.FLATPAK_GPG_KEY_ID }}` — the client validates `summary.sig`/`summary.idx.sig` against this key.
- Copying the bundle into `repo/` allows direct download without OSTree (`flatpak install --bundle`).

### 3.6 Extract Version

```yaml
- name: Extract app version
  id: version
  run: |
    VERSION=$(python3 -c "import re; print(re.search(r\"version:\s*'([^']+)'\", open('meson.build').read()).group(1))")
    echo "version=$VERSION" >> $GITHUB_OUTPUT
    echo "App version: $VERSION"
```

No `if:` condition — needed for both `develop` and `main` (used for pre-releases and gh-pages commit messages).

### 3.7 Publish Pre-release (develop only)

```yaml
- name: Publish pre-release on develop
  if: github.ref == 'refs/heads/develop'
  uses: softprops/action-gh-release@v2
  with:
    tag_name: ${{ steps.version.outputs.version }}
    name: ${{ steps.version.outputs.version }}
    prerelease: true
    generate_release_notes: true
    files: dns_tester.flatpak
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

The tag is the app version (e.g. `26.08.31.1536`), which is bumped on every commit per project policy.

### 3.8 Deploy to GitHub Pages

```yaml
- name: Deploy Flatpak repository to GitHub Pages
  uses: peaceiris/actions-gh-pages@v4
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_branch: gh-pages
    publish_dir: repo
    destination_dir: ${{ github.ref == 'refs/heads/main' && 'stable' || 'beta' }}
    keep_files: true
    commit_message: "deploy flatpak repo ${{ github.ref == 'refs/heads/main' && 'stable' || 'beta' }} ${{ steps.version.outputs.version || github.sha }}"
```

- `publish_branch: gh-pages` — single branch hosting both channels
- `destination_dir: beta` or `stable` — keeps repositories isolated
- `keep_files: true` — prevents one channel's deploy from deleting the other
- First deploy creates `gh-pages` automatically; subsequent deploys push incremental commits with the full OSTree objects.

## 4. Enabling GitHub Pages

After the first workflow run creates the `gh-pages` branch, enable Pages **once** manually:

1. GitHub → `Settings` → `Pages`
2. `Build and deployment` → `Source: Deploy from a branch`
3. `Branch: gh-pages` / `(root)` → `Save`

Then verify:
- `https://<user>.github.io/<repo>/beta/dns_tester.flatpakrepo` exists
- `https://<user>.github.io/<repo>/stable/dns_tester.flatpakrepo` exists

If you skip this step, the API `GET /repos/<user>/<repo>/pages` returns `404` and the repo is not served via HTTP.

## 5. Common Pitfalls and Fixes Encountered

| Error | Cause | Fix |
|---|---|---|
| `manifest unknown` on `ghcr.io/flathub-infra/...:fedora-latest` | Container image does not exist | Remove `container:` block; install `flatpak-builder` via `apt` on `ubuntu-latest` |
| `flatpak-builder: not found` | Ubuntu image has no builder | `sudo apt-get install -y flatpak flatpak-builder xvfb` |
| `No remote refs found for 'flathub'` | Flathub remote not added before builder | `sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo` |
| `Flatpak system operation Deploy not allowed for user` | Builder runs `flatpak --system install` as unprivileged user | Pre-install with `sudo flatpak install -y ... Platform//50 Sdk//50` |
| `is not a valid icon: Expected a square icon but got: 256x208` | Scalable SVG not square | Fix SVG to `width=256 height=256 viewBox=0 0 256 256` with centered content |
| `Image too large (1500x1500). Max. size 512x512` | PNG installed under `128x128` but file is `1500x1500` | Resize PNG to its declared directory size (e.g. `128x128` → `128`) |
| `Clave GPG no válida` / `GPGKey=` empty | Flatpak validates `GPGKey` as base64; empty fails | Generate signing key, store secrets, add `gpg-sign: ${{ secrets.FLATPAK_GPG_KEY_ID }}` and `GPGKey=${{ secrets.FLATPAK_GPG_PUBLIC_B64 }}` |
| `No se encontraron referencias remotas` for `beta` | `summary` missing (wrong OSTree branch or unsigned without `--no-gpg-verify`) | Ensure builder `branch:` matches channel (`beta`/`stable`) and use signed repo |
| `Server returned status 404` for `stable` | No `main` push yet, `gh-pages/stable/` never deployed | Merge `develop` → `main` once to populate stable |
| `403` on release/gh-pages | Missing `permissions: contents: write` | Add at workflow top level |
| `404` on Pages API | Pages not enabled | Enable `gh-pages` branch in Settings → Pages |

## 6. Adapting to Another Project

1. Copy `.github/workflows/flatpak.yml` and replace:
   - `es.neikon.dns_tester.json` → your manifest path
   - `dns_tester` → your app id / bundle name
   - `org.gnome.Platform//50` → your runtime/version
   - `Neikon/dns_tester` → your `user/repo` in URLs
   - `ICON` URL to your app icon
2. Ensure `meson.build` contains a parsable `version: '...'` line or adjust the `Extract app version` step to read your version file.
3. Adjust `branch` mapping if you use different GitFlow names.
4. Push a commit to `develop` — workflow will create `gh-pages/beta/` and a pre-release. Merge `develop` → `main` to populate `gh-pages/stable/`.
5. Enable Pages as in section 4.

## 7. Current State (DNS Tester)

- Workflow: `.github/workflows/flatpak.yml` (2026-08-31) — signed repos with GPG `C54B2799388C8DC49EC61979...` (`flatpak@neikon.es`)
- Latest successful runs:
  - `26.08.31.1554` → `https://github.com/Neikon/dns_tester/releases/tag/26.08.31.1554` (pre-release, beta, signed)
  - `gh-pages:beta` contains signed OSTree repo (`summary.sig`) + `dns_tester.flatpakrepo` with `GPGKey=mQENB…` and `dns_tester.flatpak`
  - `gh-pages:stable` populated on next `main` push (signed)
- Versioning: `YY.MM.DD.hhmm` bumped on every commit, synchronized across `meson.build`, `src/main.py`, `data/*.metainfo.xml.in`
- GPG secrets: `FLATPAK_GPG_PRIVATE_KEY`, `FLATPAK_GPG_KEY_ID`, `FLATPAK_GPG_PUBLIC_B64` in GitHub repo settings
