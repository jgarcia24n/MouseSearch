# Tests Directory

This directory contains test scripts for the MyAnonamouse Search organize functionality.

## 📁 Structure

```
tests/
├── __init__.py                  # Python package marker
├── test_organize.py             # Comprehensive test script
├── quick_test_organize.py       # Simple test with real data
├── run_tests.py                 # Test runner script
├── TEST_ORGANIZE_README.md      # Detailed usage documentation
└── README.md                    # This file
```

## 🚀 Quick Start

### Run all tests:
```bash
cd tests
python run_tests.py
```

### Run quick test only:
```bash
cd tests
python quick_test_organize.py
```

### Run comprehensive tests:
```bash
cd tests
python test_organize.py --auto
```

## 🧪 What gets tested

- **Server connectivity** - Verifies the app is running
- **Single torrent organization** - `POST /organize/<hash>`
- **Batch organization** - `POST /organize`
- **Error handling** - Tests with invalid data
- **Real data testing** - Uses actual hashes from metadata.json

## 📋 Test Scripts

### `quick_test_organize.py`
- Simple test using real data from metadata.json
- Tests both single and batch organization endpoints
- Perfect for quick verification

### `test_organize.py`
- Comprehensive testing with multiple modes
- Command-line options for different test scenarios
- Detailed output and analysis

### `run_tests.py`
- Automated test runner
- Runs multiple test scenarios
- Captures and displays all output

## 🔧 Requirements

All tests use the existing project dependencies:
- `httpx` (already in requirements.txt)
- Python 3.12+ (your current environment)

## 📊 Example Output

The tests will show:
- ✅ Server status and connectivity
- 📚 Torrent metadata from your data files
- 📡 HTTP request/response details
- 📄 JSON responses with organization results
- 📈 Statistics for batch operations

Run the tests to verify your organize endpoints are working correctly!