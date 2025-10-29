# Test Organize Routes - Usage Examples

## Basic Usage

The test script can be run in several modes:

### 1. Default Test (tests both endpoints with dummy data)
```bash
cd tests
python test_organize.py
```

### 2. Test with specific server host/port
```bash
cd tests
python test_organize.py --host localhost --port 5000
```

### 3. Test single torrent organization with specific hash
```bash
cd tests
python test_organize.py --single-hash abc123def456789...
```

### 4. Test batch organization only
```bash
cd tests
python test_organize.py --batch
```

### 5. Auto-detect mode (reads metadata.json and tests intelligently)
```bash
cd tests
python test_organize.py --auto
```

## Example Output

The script will show:
- Server connectivity check
- Metadata file analysis (if available)
- Request/response details for each endpoint
- JSON formatted responses
- Summary of batch organization results

## What it tests

1. **Single torrent organization** (`POST /organize/<hash>`)
   - Tests organizing a specific torrent by hash
   - Shows success/failure status and detailed messages

2. **Batch organization** (`POST /organize`)
   - Tests organizing all unorganized torrents
   - Shows statistics: total, succeeded, failed, skipped
   - Displays details for each processed torrent

## Dependencies

The script uses `httpx` for async HTTP requests. Install with:
```bash
pip install httpx
```