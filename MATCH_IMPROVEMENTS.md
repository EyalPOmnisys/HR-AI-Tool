# Match Service Improvements & Fixes

## Critical Bugs Fixed

### 1. **Data Structure Mismatch (CRITICAL)**
**Problem**: The code was looking for fields that don't exist in `job.analysis_json`:
- Looking for `required_skills` at root level → Actually at `skills.must_have`
- Looking for `nice_to_have` at root level → Actually at `skills.nice_to_have`  
- Looking for `seniority` → Doesn't exist in schema at all
- Looking for `tech_stack` as list → Actually a dict with nested structure

**Impact**: Job requirements were not being properly loaded, causing incorrect skill matching and penalties.

**Fix**: Updated data extraction to use correct nested paths from `JobAnalysis` schema.

---

### 2. **Incorrect Cosine Similarity Normalization**
**Problem**: `cosine_to_0_100()` was mapping 0.2-0.8 range to 0-100, which:
- Severely compressed the scoring range
- Made most matches appear mediocre (40-60 range)
- Lost important distinctions between good and great matches

**Fix**: 
- Changed to map 0.3-0.95 range (more realistic for semantic similarity)
- Returns float instead of int for better precision
- Scores now spread across 0-100 more naturally

---

### 3. **Flawed Evidence Aggregation**
**Problem**: The original code:
- Mixed evidences from all tracks into one list per resume
- Calculated track score from global evidences, not track-specific ones
- Duplicated evidences across different tracks

**Impact**: Scores didn't properly reflect track-specific matches.

**Fix**: 
- Properly group evidences by resume AND track
- Deduplicate chunks per resume per track
- Calculate track scores only from track-specific evidences
- Store evidences separately by track

---

### 4. **Hardcoded OpenAI Model**
**Problem**: Code hardcoded `gpt-4o-mini` instead of using config.

**Fix**: Now uses `settings.OPENAI_MODEL` from config for flexibility.

---

### 5. **Skills Comparison Case Sensitivity**
**Problem**: Skills matching was case-sensitive:
- Job requires "Python" but resume has "python" → Counted as missing

**Fix**: Normalize all skills to lowercase before comparison.

---

### 6. **Poor Experience Priority Application**
**Problem**: Experience sections were boosted (×1.5) but:
- Applied too late in the pipeline
- Didn't significantly impact final scores
- Value too high (1.5x) causing imbalance

**Fix**: Reduced to 1.3x and applied correctly during evidence scoring.

---

### 7. **Removed Threshold Complexity**
**Problem**: Complex logic for `min_threshold` filtering added unnecessary complexity.

**Fix**: Removed threshold filtering entirely - simpler and cleaner logic.

---

## Scoring Improvements

### Updated Configuration (`config.py`)
```python
k_per_track: 200           # reduced from 300 for better precision
m_evidence_per_track: 8    # increased from 5 for more context
w_requirements: 0.50       # adjusted from 0.55
w_tech: 0.35              # adjusted from 0.30
w_resp: 0.15              # kept same
experience_priority: 1.3   # reduced from 1.5
min_cosine_for_evidence: 0.3  # NEW: filter weak matches
rag_weight: 0.65          # RAG contribution to final score
llm_weight: 0.35          # LLM contribution to final score
```

### Improved Penalty/Bonus System
- **Missing required skill**: 5 points each, max 25
- **Matched skill bonus**: 2 points each, max 15
- **LLM verdict penalties**: 
  - `no_fit`: -10 points
  - `weak_fit`: -5 points

---

## Comprehensive Logging Added

### Step-by-Step Logging
All major stages now log:

1. **Initialization**: Job info, parameters
2. **Chunk Loading**: Count and breakdown by section
3. **Query Selection**: Queries per track
4. **ANN Search**: Hits per track, query performance
5. **Aggregation**: Unique resumes per track
6. **Scoring**: Individual score breakdowns
7. **LLM Judge**: API calls, results, verdicts
8. **Final Results**: Top scores summary

### Log Format
```
2025-11-11 14:23:45 | INFO     | match.service | Starting match run for job_id=...
2025-11-11 14:23:45 | INFO     | match.service | Loaded 23 job chunks
2025-11-11 14:23:45 | INFO     | match.service | Track 'requirements': 8 queries
...
```

### Debug Logging
Enable detailed per-resume scoring with:
```python
logging.getLogger("match.service").setLevel(logging.DEBUG)
```

---

## Simplified API Behavior

### User-Specified Top N (1-20)
- User selects how many candidates they want (1-20)
- No more `min_threshold` filtering
- Returns exactly the number requested (or fewer if not enough candidates)
- Clean, predictable behavior

### Request
```json
{
  "job_id": "uuid",
  "top_n": 10,       // User-selected, 1-20
  "min_threshold": 0  // ignored
}
```

### Response
```json
{
  "job_id": "uuid",
  "requested_top_n": 10,
  "min_threshold": 0,
  "returned": 10,     // May be less if fewer candidates available
  "candidates": [...]
}
```

---

## Enhanced API Response

### New Fields in `CandidateRow`
```python
{
    "resume_id": "...",
    "match": 85,           # Final score
    "candidate": "John Doe",
    "experience": "5 yrs",
    "email": "...",
    "phone": "...",
    
    # NEW: Scoring transparency
    "rag_breakdown": {
        "requirements": 82.5,
        "tech": 90.0,
        "responsibility": 75.0,
        "bonuses": 10,
        "penalties": 5
    },
    "llm_score": 88,
    "llm_verdict": "strong_fit"
}
```

**Removed**: `below_threshold` field (not needed anymore)

---

## Frontend Updates

### Dashboard Changes
- Shows "Found X candidates (requested: Y)"
- Added verdict emojis:
  - 💪 strong_fit
  - 🤔 partial_fit
  - ⚠️ weak_fit
  - ❌ no_fit

### Form Changes
- User can select 1-20 candidates
- Input field validates range (1-20)
- Default: 10 candidates

---

## LLM Judge Improvements

### Uses Config Model
- Now uses `settings.OPENAI_MODEL` instead of hardcoded value
- Easy to switch between models (gpt-4o-mini, gpt-4o, etc.)

### Better Context Provided
- Correct nested structure for job requirements
- Top 5 evidence scores per candidate
- RAG breakdown for informed evaluation
- Cleaner prompt with specific output format

### Enhanced Output
```json
{
    "resume_id": "...",
    "llm_score": 85,
    "verdict": "strong_fit",
    "missing_critical": ["Kubernetes", "AWS"],
    "strengths": "Strong Python and React experience",
    "concerns": "Limited cloud experience"
}
```

---

## Configuration Tuning Guide

### Model Selection
Update in `backend/app/core/config.py` or `.env`:
```bash
OPENAI_MODEL=gpt-4o-mini      # Fast, cheaper
OPENAI_MODEL=gpt-4o           # Better quality
```

### Increase Precision (fewer but better matches)
```python
k_per_track: 100                  # reduce
min_cosine_for_evidence: 0.4      # increase
```

### Increase Recall (more candidates considered internally)
```python
k_per_track: 300                  # increase
min_cosine_for_evidence: 0.25     # decrease
m_evidence_per_track: 10          # increase
```

### Balance Track Importance
```python
# For tech-heavy roles
w_tech: 0.45
w_requirements: 0.40

# For leadership roles
w_resp: 0.25
w_requirements: 0.50
```

### Adjust LLM Influence
```python
# Trust RAG more
rag_weight: 0.75
llm_weight: 0.25

# Trust LLM more (if using GPT-4)
rag_weight: 0.55
llm_weight: 0.45
```

---

## Files Modified

### Backend
- `backend/app/services/match/service.py` - Main matching logic + logging
- `backend/app/services/match/config.py` - Configuration parameters  
- `backend/app/services/match/llm/judge.py` - LLM judging, uses config model
- `backend/app/schemas/match.py` - API response schema
- `backend/app/main.py` - Logging configuration

### Frontend
- `client/src/types/match.ts` - Updated types, removed `below_threshold`
- `client/src/screens/AISearch/AISearch.tsx` - Simplified to always request top 3
- `client/src/components/ai-search/Form/Form.tsx` - Hidden candidate count input
- `client/src/components/ai-search/Dashboard/Dashboard.tsx` - Updated display logic

---

**Date**: November 11, 2025  
**Status**: ✅ Ready for testing
