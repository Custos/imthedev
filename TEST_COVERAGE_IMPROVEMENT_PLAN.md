# Test Coverage Improvement Plan for imthedev

## Current Status

### Overall Test Results
- **Total Tests**: 271
- **Passing Tests**: 185 (all non-UI tests)
- **Failing Tests**: ~86 (primarily UI component tests)
- **Overall Coverage**: 63.29%

### Test Suite Health by Module

#### ✅ Fully Passing Modules (185 tests)
- `tests/app/` - Application bootstrap tests
- `tests/core/` - Core domain and services tests
- `tests/infrastructure/` - Persistence and configuration tests
- `tests/unit/` - Unit tests for domain models and interfaces

#### ❌ Failing Modules (86 tests)
- `tests/ui/tui/` - UI component and integration tests

### Coverage Analysis

#### High Coverage Areas (>80%)
- Core domain models and services
- Infrastructure components
- Application bootstrap

#### Low Coverage UI Files
| File | Lines | Missed | Coverage |
|------|-------|--------|----------|
| `ui/tui/app.py` | 121 | 87 | 28.10% |
| `ui/tui/components/approval_controls.py` | 167 | 128 | 23.35% |
| `ui/tui/components/command_dashboard.py` | 170 | 137 | 19.41% |
| `ui/tui/components/project_selector.py` | 72 | 50 | 30.56% |
| `ui/tui/components/status_bar.py` | 130 | 97 | 25.38% |
| `ui/tui/facade.py` | 109 | 74 | 32.11% |
| `ui/tui/__main__.py` | 4 | 4 | 0.00% |

## Root Cause Analysis

### Issues Fixed
1. ✅ **CommandStatus enum** - Updated test to expect 7 members (including CANCELLED)
2. ✅ **Project model instantiation** - Fixed tests using outdated constructor
3. ✅ **Reactive type annotations** - Created proper mock supporting `reactive[type]` syntax
4. ✅ **isinstance checks** - Updated tests to avoid isinstance with mocked classes

### Remaining Issues
1. **Complex Textual mocking** - UI components require deep integration with Textual framework
2. **Event system mocking** - Button.Pressed and other nested event classes need proper mocking
3. **Widget lifecycle** - compose(), on_mount(), and other lifecycle methods need proper simulation

## Improvement Strategy

### Phase 1: Stabilize UI Test Infrastructure (Priority: High)
1. **Create comprehensive Textual mock library**
   - Mock all Textual event types (Button.Pressed, ListView.Selected, etc.)
   - Implement proper widget lifecycle (compose, mount, focus, etc.)
   - Support reactive properties and bindings

2. **Implement UI test base classes**
   ```python
   class UIComponentTestCase:
       """Base class for UI component tests with proper setup/teardown"""
       
   class UIIntegrationTestCase:
       """Base class for UI integration tests with event simulation"""
   ```

### Phase 2: Fix Existing UI Tests (Priority: High)
1. **Update test imports** to use new mock infrastructure
2. **Refactor tests** to use proper widget lifecycle
3. **Add event simulation** for user interactions

### Phase 3: Improve UI Coverage (Priority: Medium)
Target coverage goals for each file:

#### ui/tui/app.py (Current: 28% → Target: 70%)
- Test all key bindings
- Test autopilot mode toggle
- Test focus navigation
- Test event handlers

#### ui/tui/components/approval_controls.py (Current: 23% → Target: 70%)
- Test button states (enabled/disabled)
- Test command approval/rejection flow
- Test keyboard shortcuts
- Test visual updates

#### ui/tui/components/command_dashboard.py (Current: 19% → Target: 70%)
- Test command display
- Test output streaming
- Test status updates
- Test error handling

#### ui/tui/components/project_selector.py (Current: 31% → Target: 70%)
- Test project list updates
- Test selection events
- Test keyboard navigation
- Test empty state

#### ui/tui/components/status_bar.py (Current: 25% → Target: 70%)
- Test status updates
- Test model display
- Test connection status
- Test project info

#### ui/tui/facade.py (Current: 32% → Target: 70%)
- Test event routing
- Test state synchronization
- Test error handling
- Test initialization

### Phase 4: Add Integration Tests (Priority: Low)
1. **End-to-end workflows**
   - Project selection → Command proposal → Approval → Execution
   - Autopilot mode operation
   - Multi-model switching
   - Error recovery

2. **Performance tests**
   - Large project lists
   - Long command outputs
   - Rapid state changes

## Implementation Approach

### Quick Wins (Can be done immediately)
1. Skip UI tests temporarily with `@pytest.mark.skip("UI mocking in progress")`
2. Focus on maintaining 100% pass rate for non-UI tests
3. Add simple unit tests for UI component methods that don't require Textual

### Medium-term (1-2 weeks)
1. Implement proper Textual mock infrastructure
2. Gradually re-enable and fix UI tests
3. Add new tests for uncovered UI functionality

### Long-term (1+ month)
1. Achieve 70%+ coverage across all UI files
2. Add comprehensive integration tests
3. Implement visual regression tests

## Testing Best Practices

### For UI Components
1. **Test behavior, not implementation**
   - Focus on user interactions and outcomes
   - Don't test Textual framework internals

2. **Use test fixtures**
   ```python
   @pytest.fixture
   def mock_facade():
       """Provide a properly configured facade mock"""
       
   @pytest.fixture
   def sample_projects():
       """Provide test project data"""
   ```

3. **Simulate real workflows**
   - Test complete user journeys
   - Include error cases and edge conditions

### For Coverage Improvement
1. **Prioritize critical paths**
   - Focus on main user workflows first
   - Add edge cases incrementally

2. **Use parameterized tests**
   ```python
   @pytest.mark.parametrize("input,expected", [
       ("valid", True),
       ("invalid", False),
   ])
   def test_validation(input, expected):
       assert validate(input) == expected
   ```

3. **Monitor coverage trends**
   - Set up CI to track coverage over time
   - Fail builds if coverage decreases

## Success Metrics

### Short-term (1 week)
- All non-UI tests passing (✅ Achieved: 185/185)
- UI tests properly skipped or fixed
- No StopIteration or TypeError errors

### Medium-term (1 month)
- UI test infrastructure complete
- 50% of UI tests passing
- Overall coverage >70%

### Long-term (3 months)
- All tests passing (100%)
- UI coverage >70% for all files
- Comprehensive integration test suite

## Conclusion

The test suite has been significantly improved with all non-UI tests now passing. The remaining work focuses on the UI layer, which requires specialized mocking infrastructure for the Textual framework. By following this plan, the project can achieve comprehensive test coverage while maintaining code quality and reliability.