# Dependency setup: Linux, Windows and macOS

Installing skills copies instructions and scripts; it does not install Python, Node.js, npm packages or a PDF converter. Install dependencies in the environment where your agent actually runs commands. A Windows-native agent uses Windows tools; an agent running in WSL uses the Linux setup inside WSL.

## What you need

| Component | Required for | Installation |
|---|---|---|
| Python 3.10+ | Financial calculations, market sizing and PPTX audits | OS instructions below; these scripts use the standard library |
| Node.js 22.20+ with npm/npx | Skills CLI and PPTX generation | OS instructions below; current LTS recommended |
| Git | Cloning the repository and Git-based skill installation | OS instructions below |
| PptxGenJS 4.0.0 | Editable PPTX generation | `npm install` in a repository checkout, or the installed-skill instructions below |
| LibreOffice | Optional PDF conversion and visual review | OS instructions below |
| `artifact_tool` | Optional formula-driven Excel export | Requires a compatible artifact environment; see the Excel section |
| Fonts used by your deck | Consistent text layout | Install the selected fonts before rendering |

The agent also needs web/search access to research current markets, competitors and sources. Installing this repository does not add a search service. Microsoft Office is not required to generate PPTX files.

## Windows — PowerShell

Install tools using [Windows Package Manager](https://learn.microsoft.com/windows/package-manager/winget/):

```powershell
winget install --exact --id Python.Python.3.12
winget install --exact --id OpenJS.NodeJS.LTS
winget install --exact --id Git.Git
# Optional: PDF conversion and slide viewing
winget install --exact --id TheDocumentFoundation.LibreOffice
```

If winget is unavailable, use the official installers for [Python](https://www.python.org/downloads/windows/), [Node.js LTS](https://nodejs.org/en/download/), [Git](https://git-scm.com/downloads/win) and [LibreOffice](https://www.libreoffice.org/download/). Ensure Python and Node.js are available on PATH.

Close and reopen PowerShell and your agent app after installation, then check:

```powershell
python --version
node --version
npm.cmd --version
git --version
```

If `python` opens the Microsoft Store or is not found, try `py -3.12 --version`. Use `py -3.12` in place of `python` below, or correct your Python PATH/app execution aliases.

For LibreOffice's default installation, add its executable folder to the current session:

```powershell
$env:Path = "C:\Program Files\LibreOffice\program;$env:Path"
soffice.exe --version
```

To make this persistent, add `C:\Program Files\LibreOffice\program` to your user Path in Windows Environment Variables, then restart the terminal and agent app. Adjust the folder for a custom installation.

Use `npm.cmd` and `npx.cmd` in PowerShell if execution policy blocks the `.ps1` wrappers; no execution-policy change is needed.

## macOS — Terminal

Install [Homebrew](https://brew.sh/) using its official instructions if it is not already available. Complete its shell/PATH setup, then run:

```bash
brew install python node git
# Optional: PDF conversion and slide viewing
brew install --cask libreoffice
```

Alternatively, use the official [Python](https://www.python.org/downloads/macos/), [Node.js LTS](https://nodejs.org/en/download/) and [LibreOffice](https://www.libreoffice.org/download/) installers.

Check the tools:

```bash
python3 --version
node --version
npm --version
git --version
```

Expose the LibreOffice command in your current shell:

```bash
export PATH="/Applications/LibreOffice.app/Contents/MacOS:$PATH"
soffice --version
```

Add that export to `~/.zshrc` if you want it in future zsh sessions. Restart your agent app and verify it can find `soffice`; a desktop app may not inherit interactive shell settings. You can also use the full executable path shown in the PDF section.

## Linux — Bash

Install Python and Git using your distribution's package manager.

Ubuntu / Debian:

```bash
sudo apt update
sudo apt install -y python3 git ca-certificates curl
# Optional: PDF conversion and slide viewing
sudo apt install -y libreoffice-impress
```

Fedora:

```bash
sudo dnf install -y python3 git ca-certificates curl
# Optional: PDF conversion and slide viewing
sudo dnf install -y libreoffice-impress
```

Use a distribution release providing Python 3.10 or later. For other distributions, install equivalent packages.

For Node.js, follow the official [Node.js download instructions](https://nodejs.org/en/download/) for your distribution, or install [nvm](https://github.com/nvm-sh/nvm#installing-and-updating) using its official instructions. With nvm installed and loaded:

```bash
nvm install --lts
nvm use --lts
```

The distribution's `nodejs` package is also suitable if it provides Node.js 22.20 or later; check the version rather than assuming it does. An agent launched outside your shell may not load nvm: ensure `node` and `npm` are on the agent's PATH.

```bash
python3 --version
node --version
npm --version
git --version
# If LibreOffice was installed
soffice --version
```

## Install the skills and their JavaScript dependency

### Project-local installation for Codex

Open the project directory in which you want to use the skills. Copy mode keeps the scripts under that project, so Node can resolve the project's npm dependencies even when the CLI would otherwise use symlinks.

Linux / macOS:

```bash
npx skills add euphoo-01/startup_pitch_skills -a codex --copy
npm install pptxgenjs@4.0.0
node -e "console.log(require.resolve('pptxgenjs', {paths: ['.agents/skills/investor-slides/scripts']}))"
```

Windows PowerShell:

```powershell
npx.cmd skills add euphoo-01/startup_pitch_skills -a codex --copy
npm.cmd install pptxgenjs@4.0.0
node -e "console.log(require.resolve('pptxgenjs', {paths: ['.agents/skills/investor-slides/scripts']}))"
```

The final command should print a path to the installed library. Restart or refresh your agent session if it does not discover the new skills.

For another agent, choose it in the interactive installer by omitting `-a codex`. Adjust the verification path to its installed skill directory.

For a global installation (`-g`), install PptxGenJS in the **actual `investor-slides` skill directory**, or one of its ancestor directories, and verify resolution from the script's location. Do not assume `npm install -g pptxgenjs` makes the library available to Node's `require()`. For example, substitute the real skill path:

```bash
npm install --prefix /absolute/path/to/investor-slides pptxgenjs@4.0.0
```

In PowerShell, use `npm.cmd` and a quoted Windows path. Skill updates may replace that directory, so recheck dependencies after updating.

### Repository checkout — includes the runnable demo

The Skills CLI installs skill folders; the repository-level demo, examples and package.json require a checkout:

```bash
git clone https://github.com/euphoo-01/startup_pitch_skills.git
cd startup_pitch_skills
npm install
```

In PowerShell use `npm.cmd install`. Run the following commands from the checkout root.

Linux / macOS:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build_demo.py --no-excel --no-pdf
```

Windows PowerShell:

```powershell
python -m unittest discover -s tests -v
python scripts/build_demo.py --no-excel --no-pdf
```

This rebuilds the fictional financial JSON files and an editable `demo/investor_pitch.pptx`, then audits the presentation. It deliberately skips optional exports. The tests also include an Excel check that is skipped when `artifact_tool` is unavailable.

## PDF preview and visual review

After building the demo, convert it explicitly using your platform's command. This avoids depending on automatic converter discovery and the demo builder's temporary-profile handling across platforms.

Linux:

```bash
soffice --headless --convert-to pdf --outdir demo demo/investor_pitch.pptx
```

macOS:

```bash
/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to pdf --outdir demo demo/investor_pitch.pptx
```

Windows PowerShell:

```powershell
& "C:\Program Files\LibreOffice\program\soffice.com" --headless --convert-to pdf --outdir demo demo/investor_pitch.pptx
```

Close LibreOffice first if conversion does not complete. Open the generated PDF and review every slide for clipping, wrapping and font substitutions. The numeric audit does not replace visual review. Install the fonts selected by your deck theme if text layout differs between machines. See [LibreOffice's command-line documentation](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html).

## Excel export: current limitation

`export_excel.py` imports `artifact_tool`. This repository does not provide a standalone installer or a tested public pip dependency for it. Do not assume an unrelated package with that name is compatible.

If your agent environment supplies the compatible library, check it using the same Python interpreter used for export:

```bash
python -c "from artifact_tool import Workbook, SpreadsheetFile; print('Excel export dependency available')"
python skills/business-analyst/scripts/export_excel.py examples/sample_b2b.json --out demo/financial_model.xlsx
```

On Linux/macOS use `python3` instead. If the import fails, skip Excel export with `--no-excel`; financial JSON and PPTX generation still work. Installing Microsoft Excel does not satisfy this Python dependency. Portable Excel export without the artifact environment is not currently implemented.

## Verification scope

The commands above are setup instructions, not a claim that every platform has been tested. The current development session verified Linux tests and remote skill discovery; native Windows and macOS setup and PDF conversion still need testing on those systems.
