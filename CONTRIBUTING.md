# Contributing to claude-content-workflow

Thank you for contributing to `claude-content-workflow`!

## Contribution Guidelines

1. **Keep Implementations Generic**: Design components, scripts, and workflows to adapt across diverse creators, genres, and video styles.
2. **Repository Hygiene**: Never commit personal audio/video footage, finished renders, API tokens, `.env` files, or personal local file paths.
3. **Verify Licenses**: Ensure all third-party code and assets have clear, permissive open-source licenses.
4. **Run Tests**: Before submitting pull requests, ensure all unit tests and hygiene scans pass:
   ```powershell
   python -m pytest engine/tests/ -v
   python scripts/hygiene_check.py
   ```
5. **Clear Commit Messages**: Provide clear descriptions of modifications, bug fixes, or new features in pull requests.
