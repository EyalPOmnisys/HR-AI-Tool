# Match Service Debugging Guide

## Quick Start - Viewing Match Logs

### 1. Run the Backend with Visible Logs

Make sure your backend is running with proper logging output:

```bash
cd backend
uvicorn app.main:app --reload --log-level info
```

### 2. Trigger a Match

Call the match endpoint:

```bash
POST http://localhost:8000/match/run
{
    "job_id": "your-job-uuid",
    "top_n": 10,
    "min_threshold": 40
}
```

### 3. Read the Logs

You'll see structured logs like:

```
2025-11-11 14:23:45 | INFO     | match.service | ================================================================================
2025-11-11 14:23:45 | INFO     | match.service | Starting match run for job_id=abc-123, top_n=10, min_threshold=40
2025-11-11 14:23:45 | INFO     | match.service | Job loaded: title='Senior Python Developer', status='published'
2025-11-11 14:23:45 | INFO     | match.service | Step 1: Loading job chunks with embeddings
2025-11-11 14:23:45 | INFO     | match.service | Loaded 23 job chunks
2025-11-11 14:23:46 | INFO     | match.service | Selected 18 total query chunks across tracks:
2025-11-11 14:23:46 | INFO     | match.service |   Track 'requirements': 8 queries
2025-11-11 14:23:46 | INFO     | match.service |   Track 'tech': 6 queries
2025-11-11 14:23:46 | INFO     | match.service |   Track 'respons': 4 queries
2025-11-11 14:23:46 | INFO     | match.service | Step 2: Running ANN searches
2025-11-11 14:23:46 | INFO     | match.service |   Track 'requirements' total hits: 1200
2025-11-11 14:23:47 | INFO     | match.service |   Track 'tech' total hits: 800
2025-11-11 14:23:47 | INFO     | match.service |   Track 'respons' total hits: 600
2025-11-11 14:23:47 | INFO     | match.service | Step 3: Aggregating results per resume
2025-11-11 14:23:47 | INFO     | match.service | Total unique resumes found: 45
2025-11-11 14:23:47 | INFO     | match.service | Step 4: Loading job requirements and resume data
2025-11-11 14:23:47 | INFO     | match.service | Job requirements: 5 must-have skills, 3 nice-to-have
2025-11-11 14:23:47 | INFO     | match.service | Step 5: Calculating final scores
2025-11-11 14:23:47 | INFO     | match.service | Step 6: Sorting and selecting top 10 candidates
2025-11-11 14:23:47 | INFO     | match.service | Results: 12 above threshold, 33 below threshold
2025-11-11 14:23:47 | INFO     | match.service | Selected 10 candidates for LLM judging
2025-11-11 14:23:47 | INFO     | match.service | Step 7: Running LLM judge on selected candidates
2025-11-11 14:23:47 | INFO     | match.judge  | Starting LLM judge for 10 candidates
2025-11-11 14:23:48 | INFO     | match.judge  | LLM response received, parsing JSON
2025-11-11 14:23:48 | INFO     | match.judge  | Processing 10 LLM results
2025-11-11 14:23:48 | INFO     | match.judge  | Judge completed: Top 5 final scores: [88, 85, 82, 79, 76]
2025-11-11 14:23:48 | INFO     | match.service | Step 8: Building final response
2025-11-11 14:23:48 | INFO     | match.service | ================================================================================
2025-11-11 14:23:48 | INFO     | match.service | Match run completed: 10 candidates returned
2025-11-11 14:23:48 | INFO     | match.service | Top 5 scores: [88, 85, 82, 79, 76]
2025-11-11 14:23:48 | INFO     | match.service | ================================================================================
```

## Enable Debug Logging

For even more detailed output, edit `backend/app/main.py`:

```python
# Change these lines:
logging.getLogger("match.service").setLevel(logging.DEBUG)
logging.getLogger("match.judge").setLevel(logging.DEBUG)
```

Debug logs include:
- Per-section chunk counts
- Individual query hit counts
- Per-resume score breakdowns with bonuses/penalties
- Detailed LLM verdict reasons

Example debug output:
```
2025-11-11 14:23:47 | DEBUG    | match.service |   Section 'requirement': 8 chunks
2025-11-11 14:23:47 | DEBUG    | match.service |   Section 'tech_stack': 6 chunks
2025-11-11 14:23:47 | DEBUG    | match.service |   Resume abc-123: Missing 2 required skills, penalty=10
2025-11-11 14:23:47 | DEBUG    | match.service |   Resume abc-123: Matched 4 skills, bonus=8
2025-11-11 14:23:47 | DEBUG    | match.service |   Resume abc-123: RAG=78.0 (req=82.5, tech=90.0, resp=75.0, bonus=8, penalty=10)
```

## Checking for Problems

### ❌ No query chunks selected
```
Track 'requirements': 0 queries
```
**Problem**: Job chunks don't have embeddings
**Solution**: Re-run job analysis or check embedding pipeline

### ❌ Very few hits
```
Track 'tech' total hits: 3
```
**Problem**: Not enough resumes, or embedding mismatch
**Solution**: Check resume processing status, verify embedding model consistency

### ❌ All scores bunched together
```
Top 5 scores: [52, 51, 51, 50, 50]
```
**Problem**: Poor discrimination in matching
**Solution**: Adjust `min_cosine_for_evidence` or track weights in `config.py`

### ❌ LLM judge failed
```
WARNING  | match.judge  | Failed to parse JSON from LLM
```
**Problem**: OpenAI API issue or rate limit
**Solution**: Check API key, increase timeout, or temporarily disable judge

## Log Files (Production)

For production, consider logging to file:

```python
# In app/main.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/match.log', mode='a')  # ADD THIS
    ]
)
```

## Performance Metrics

Watch for these in logs:
- **Total execution time**: From "Starting match" to "completed"
- **ANN search time**: Between Step 2 start and Step 3
- **LLM judge time**: Step 7 duration
- **Number of unique resumes**: Should match DB resume count for small datasets

Typical performance:
- 100 resumes: ~2-4 seconds
- 1000 resumes: ~5-10 seconds
- 10000 resumes: ~20-30 seconds

## Troubleshooting Common Issues

### Issue: Scores too low (all below 50)
**Check logs for**:
- Missing required skills causing high penalties
- Low cosine similarities (< 0.4) indicating poor semantic match
- Very few evidences per track

**Fix**: 
- Review job description quality
- Check if resume skills are being extracted correctly
- Lower `min_threshold` temporarily to see distribution

### Issue: Wrong candidates ranked high
**Check logs for**:
- Track score breakdown - which track is dominating?
- Bonus/penalty values - are they appropriate?
- LLM verdict - does it disagree with RAG?

**Fix**:
- Adjust track weights in config.py
- Review penalty/bonus calculations
- Improve job requirements specificity

### Issue: No results returned
**Check logs for**:
- "Total unique resumes found: 0" - no matches at all
- All results below threshold

**Fix**:
- Verify resumes are processed and have embeddings
- Lower threshold temporarily
- Check job requirements aren't too restrictive

---

## Quick Diagnostics

Run this to check system health:

```sql
-- Check if jobs have chunks
SELECT j.id, j.title, COUNT(jc.id) as chunk_count
FROM jobs j
LEFT JOIN job_chunks jc ON jc.job_id = j.id
GROUP BY j.id, j.title;

-- Check if resumes have embeddings
SELECT COUNT(*) as total_resumes,
       COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embeddings
FROM resumes;

-- Check chunk embeddings
SELECT COUNT(*) as total_chunks,
       COUNT(CASE WHEN re.embedding IS NOT NULL THEN 1 END) as with_embeddings
FROM resume_chunks rc
LEFT JOIN resume_embeddings re ON re.chunk_id = rc.id;
```

All counts should be non-zero for the system to work properly.
