# FastAPI Test Suite

This directory contains comprehensive tests for the High School Management System FastAPI application.

## Test Structure

### `test_api.py`
Main API endpoint tests covering:
- Root endpoint redirection
- Activities retrieval 
- Activity signup functionality
- Participant unregistration
- Integration scenarios and complete workflows

### `test_data_models.py`
Data model and edge case tests covering:
- Data structure validation
- Additional activities merging
- Edge cases (special characters, unicode, case sensitivity)
- Participant limits validation
- Concurrency scenarios

### `test_performance.py`
Performance and load tests covering:
- Response time validation
- Load handling with many participants
- Concurrent access scenarios
- Memory usage patterns
- Large activity list performance

### `conftest.py`
Test configuration and fixtures:
- FastAPI test client setup
- Activity data reset functionality
- Sample data fixtures

## Running Tests

### Run all tests:
```bash
python -m pytest tests/ -v
```

### Run with coverage:
```bash
python -m pytest tests/ --cov=src --cov-report=term-missing
```

### Run specific test files:
```bash
python -m pytest tests/test_api.py -v
python -m pytest tests/test_performance.py -v
```

### Run without slow tests:
```bash
python -m pytest tests/ -m "not slow" -v
```

### Run only slow tests:
```bash
python -m pytest tests/ -m "slow" -v
```

## Test Features

- **100% Code Coverage**: All application code is covered by tests
- **Fixture-based Setup**: Clean test isolation with data reset between tests
- **Performance Testing**: Response time and load testing included
- **Edge Case Testing**: Comprehensive validation of error conditions
- **Concurrent Testing**: Multi-threaded scenarios for race conditions
- **Integration Testing**: End-to-end workflow validation

## Dependencies

The following packages are required for testing:
- `pytest`: Test framework
- `httpx`: HTTP client for FastAPI testing
- `pytest-cov`: Coverage reporting

These are included in `requirements.txt`.