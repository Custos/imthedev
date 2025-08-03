# Known Issues - imthedev Project

## 🐛 Test Suite Conflicts
**Severity: MEDIUM**
**Status: Has Workaround**

When running all TUI tests together, module-level patches cause interference between test files.

**Symptoms:**
- Tests pass individually but fail when run together
- Mock conflicts between test modules
- Unexpected behavior in event handling tests

**Workaround:**
```bash
# Run test suites separately
poetry run pytest tests/ui/tui/components -v
poetry run pytest tests/ui/tui/test_facade.py -v
```

**Root Cause:** Module-level patching in conftest.py affects global state

---

## 🎯 Textual Generic Types
**Severity: LOW**
**Status: Has Solution**

Textual 5.0.1 doesn't support generic App types like `App[None]`.

**Error:**
```
TypeError: 'type' object is not subscriptable
```

**Solution:**
```python
# Instead of: class MyApp(App[None]):
class ImTheDevApp(App):  # Use non-generic form
    pass
```

---

## 🔒 AI Provider Lock-in
**Severity: MEDIUM**
**Status: Planned Fix**

Currently locked to Google Gemini after removing Claude/OpenAI support.

**Impact:**
- No fallback if Gemini has issues
- Limited model selection
- Reduced flexibility for users

**Future Fix:** Re-implement adapter pattern for multi-provider support

---

## ⚡ Performance Considerations
**Severity: LOW**
**Status: Monitoring**

- Event bus can accumulate memory with many subscribers
- Large context windows may slow down AI responses
- No pagination for project lists (fine for MVP)

---

## 📝 Documentation Gaps
**Severity: LOW**
**Status: Ongoing**

- API documentation incomplete
- No user guide yet
- Missing architecture decision records (ADRs)