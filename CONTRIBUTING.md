# Contributing to Moneta Personal Finance

Thank you for your interest in contributing to **Moneta Personal Finance**! We welcome contributions from developers, designers, financial enthusiasts, and open-source advocates of all skill levels.

---

## 🌟 How You Can Help
* 🐛 **Report Bugs**: Open a detailed issue if you spot a bug or unexpected financial calculation.
* 💡 **Suggest Features**: Share ideas for new banking, portfolio, or tax tools.
* 💻 **Submit Code**: Add new capabilities, fix bugs, or optimize performance.
* 📖 **Improve Documentation**: Enhance guides, add tutorials, or fix typos in `docs/`.
* 🌍 **Translate**: Add new languages in `i18n/`.

---

## 🛠️ Local Development Setup

### Option A: Using Docker (Recommended - 1 Command)
```bash
git clone https://github.com/lohwswilson/moneta_finance.git
cd moneta_finance
docker compose up -d
```
Access Odoo at `http://localhost:8069` (login: `admin` / `admin`).

### Option B: Native Odoo 18 Setup
1. Clone the repository into your custom addons directory:
   ```bash
   git clone -b 18.0 https://github.com/lohwswilson/moneta_finance.git
   ```
2. Install Python dependencies:
   ```bash
   pip install yfinance pandas numpy matplotlib
   ```
3. Run Odoo with the module enabled:
   ```bash
   ./odoo-bin -c odoo.conf -d <your_db> -u moneta_finance
   ```

---

## 🧪 Running Automated Tests

Before submitting a Pull Request, ensure the full automated test suite passes:

```bash
./odoo-bin -c odoo.conf -d <your_db> -u moneta_finance \
  --test-enable --test-tags=moneta_finance --stop-after-init
```

---

## 🌿 Branching & Commit Message Guidelines

We follow the **Conventional Commits** specification:

* `feat(module)`: A new feature (e.g. `feat(investment): add dividend yield calculation`)
* `fix(module)`: A bug fix (e.g. `fix(dashboard): correct foreign currency conversion`)
* `docs(topic)`: Documentation updates (e.g. `docs(fire): add Trinity study formulas`)
* `style(ui)`: Code style or visual UI improvements without logic changes
* `refactor(core)`: Code refactoring
* `test(models)`: Adding or updating tests
* `chore(repo)`: Maintenance tasks or dependency updates

---

## 🚀 Pull Request Checklist

When opening a Pull Request:
1. [ ] Target branch is set to `18.0`.
2. [ ] All existing and new automated tests pass (`--test-enable`).
3. [ ] Code adheres to PEP 8 and Odoo coding guidelines.
4. [ ] Relevant documentation in `docs/` is updated if adding or modifying features.
5. [ ] Commit messages follow Conventional Commits.
