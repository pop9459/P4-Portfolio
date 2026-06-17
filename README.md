# NHL Stenden Computer Science Y1 P4 Portfolio

This repository aggregates the Period 4 (*AI Odyssey — AI2nnovate: Transforming Tomorrow*)
project repositories using **Git submodules**.

- Name: Peter Kapsiar
- Student ID: 5486866
- Main repository: https://github.com/pop9459/P4-Portfolio

## Quick Links

- [Computer Science Portfolio](P4-ComputerScience/portfolio.md)
- [Professional Skills Portfolio](P4-ProfessionalSkills/portfolio.md)
- [Combined Portfolio](PORTFOLIO.md)

## Cloning this repository

Because the subprojects are Git submodules, clone with `--recurse-submodules`:

```bash
git clone --recurse-submodules https://github.com/pop9459/P4-Portfolio.git
```

If you already cloned without that flag:

```bash
git submodule update --init --recursive
```

## Updating the Combined Portfolio

Run these commands from the root of this repository.

### 1. Pull the latest submodule content

```bash
git submodule update --remote --merge
```

### 2. Regenerate the combined portfolio

```bash
python combine_portfolios.py
```

The script auto-discovers every top-level folder that contains a `portfolio.md`
(submodule or plain folder), rebuilds the table of contents, and writes `PORTFOLIO.md`.

### 3. Commit the changes

```bash
git add .
git commit -m "Update subprojects and regenerate portfolio"
git push
```

### 4. Generate PDF (optional)

`export_pdf.py` renders `PORTFOLIO.md` to `PORTFOLIO.pdf` with footer page numbers and a
book-style table of contents (each entry shows the target page number with dotted
leaders). It uses [WeasyPrint](https://weasyprint.org/) and `markdown-it-py`.

One-time setup (the WeasyPrint system libraries — pango, cairo, gdk-pixbuf — must be
installed; on most Linux distros they already are):

```bash
python -m venv --system-site-packages .venv
.venv/bin/pip install weasyprint markdown-it-py
```

Then, after regenerating the combined portfolio:

```bash
.venv/bin/python export_pdf.py
```

## Adding a New Subproject Repository

### 1. Add the new submodule

Replace `PROJECT_NAME` and `GITHUB_URL` with your values:

```bash
git submodule add GITHUB_URL PROJECT_NAME
```

### 2. Update the "Quick Links" section above

```markdown
- [My New Project Portfolio](PROJECT_NAME/portfolio.md)
```

### 3. Regenerate and commit

```bash
python combine_portfolios.py
git add .
git commit -m "Add PROJECT_NAME as submodule"
```

The script automatically detects and merges the new project's `portfolio.md`
(if it exists) into `PORTFOLIO.md`.
