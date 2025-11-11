# Resume Processing Improvements - Summary

## תאריך: 11 בנובמבר 2025

## 🎯 מטרת השיפורים
שיפור משמעותי באיכות המידע המופק מקורות חיים והאמבדינגים שנשמרים ב-DB, כדי לשפר את תוצאות ההתאמה בין מועמדים למשרות.

---

## 📊 שיפורים שבוצעו

### 1️⃣ שיפור Prompts ל-LLM

#### `resume_extraction.prompt.txt` - החלפה מלאה
**לפני:**
- פרומפט קצר ובסיסי (5 שורות)
- הנחיות לא ברורות
- אין הנחיות לטיפול בשגיאות

**אחרי:**
- פרומפט מקיף ומפורט (100+ שורות)
- הנחיות מדויקות לחילוץ כל סוג של מידע:
  - Person: name, location, languages
  - Education: degree, field, institution, dates
  - Experience: title, company, location, dates, bullets, tech stack
  - Skills: categorization and normalization
- כללי איכות ברורים:
  - אל תמציא מידע
  - השתמש ב-null עבור שדות חסרים
  - נרמל טכנולוגיות (JS → JavaScript)
  - טיפול בתאריכים גמיש
- דוגמאות והסברים מפורטים

#### `experience_clustering.prompt.txt` - החלפה מלאה
**לפני:**
- כללים בסיסיים לקיטלוג ניסיון
- לא מספיק הנחיות לזיהוי תפקידים טכניים

**אחרי:**
- הגדרות מדויקות של קטגוריות (tech, military, hospitality, other)
- כללים מפורטים לסיווג:
  - כללי הכללה/הדרה (מה נחשב עבודה רשמית)
  - טיפול בתאריכים חופפים
  - העדפת TECH על פני MILITARY עבור תפקידים טכניים ביחידות צבא
- מערכת confidence scoring
- הנחיות לנרמול תפקידים ותיקון שגיאות כתיב
- quality checks מובנים

**השפעה צפויה:**
- דיוק גבוה יותר בחילוץ מידע
- פחות false positives/negatives
- נתוני ניסיון מדויקים יותר (שנים לפי קטגוריה)

---

### 2️⃣ שיפור אסטרטגיית Chunking

#### קובץ: `parsing_utils.py`

**שיפורים עיקריים:**

1. **זיהוי Header חכם**
   ```python
   def _extract_person_header(text: str) -> tuple[str, str]
   ```
   - מפריד את פרטי הקשר (שם, אימייל, טלפון) לchunk נפרד
   - משפר את האמבדינג של מידע זיהוי

2. **Chunking מותאם לסוג התוכן**
   - Experience: chunks גדולים יותר (2000 chars) - כדי לשמור תפקידים שלמים
   - Skills: chunks בינוניים (1200 chars)
   - כללי: 1500 chars עם overlap של 200
   
3. **טיפול בבולטים (Bullet Points)**
   ```python
   def _chunk_bulleted_text(txt: str, max_chars: int, overlap: int)
   ```
   - שומר רשימות בולטים ביחד
   - מזהה גבולות תפקידים על פי תבניות תאריכים

4. **זיהוי שפה אוטומטי**
   ```python
   def _detect_language(text: str) -> str
   ```
   - מזהה עברית/אנגלית/מעורב
   - מוסיף metadata לכל chunk

5. **הרחבת זיהוי Headers**
   - תמיכה ב-variations רבים יותר:
     - "Professional Experience", "Work Experience"
     - "Technical Skills", "Core Competencies"
     - וריאציות בעברית

**השפעה צפויה:**
- Chunks עם הקשר מלא יותר
- שמירה על מבנה הירארכי של המידע
- Embeddings איכותיים יותר לחיפוש

---

### 3️⃣ העשרת Embeddings עם Metadata

#### קובץ חדש: `embedding_utils.py`

**פונקציות עיקריות:**

1. **`enrich_chunk_for_embedding()`**
   - מוסיף prefix לפי סוג ה-section:
     ```
     "Professional Experience:"
     "Candidate: John Doe"
     "Total Tech Experience: 5.5 years"
     [original chunk text]
     ```
   - העשרה עם:
     - שם המועמד (לזיהוי)
     - סוג ה-section (experience/skills/education)
     - מטא-דאטה רלוונטי (שנות ניסיון)

2. **`create_search_optimized_embedding_text()`**
   - יוצר טקסט ייעודי ל-full-resume embedding
   - מתמקד במידע קריטי לחיפוש:
     - שם ופרטי קשר
     - סיכום ניסיון (שנים לפי תחום)
     - מיומנויות עיקריות (top 20)
     - תפקידים אחרונים
     - השכלה
   - משפר accuracy בחיפושים ראשוניים

3. **`get_embedding_prefix_by_section()`**
   - Prefixes קצרים לפי section
   - תומך בעברית ואנגלית

**השפעה צפויה:**
- Embeddings מבינים את ההקשר
- שיפור ב-semantic similarity
- התאמות מדויקות יותר בין candidates ל-jobs

---

### 4️⃣ מערכת Validation ו-Quality Checks

#### קובץ חדש: `validation.py`

**מודול מקיף לבדיקת איכות:**

1. **`ValidationResult` Class**
   - מעקב אחר errors, warnings, info
   - חישוב quality score (0-1)
   - דוח סיכום מובנה

2. **`validate_extraction()`**
   - בדיקות על Person:
     - שם תקין
     - פורמט אימייל
     - מידע קשר
   - בדיקות על Experience:
     - לפחות 2 תפקידים
     - title או company חובה
     - תאריכים הגיוניים (start < end)
     - tech stack specified
   - בדיקות על Education:
     - degree או institution חובה
   - בדיקות על Skills:
     - מינימום 3 skills
     - זיהוי duplicates
   - בדיקת שלמות כללית

3. **`validate_embedding_quality()`**
   - בדיקת dimensions (1536/3072/768)
   - וידוא שהאמבדינג לא degenerate (all zeros)
   - בדיקת variance (לא כולם אותו ערך)

4. **`create_quality_report()`**
   - דוח מקיף עם:
     - תוצאות validation
     - quality score כולל
     - המלצות לפעולה
     - status label (excellent/good/acceptable/poor/critical)

**אינטגרציה ב-Pipeline:**
- נוסף ל-`parse_and_extract()`:
  - מריץ validation אוטומטי
  - שומר quality report ב-extraction_json
  - מעדכן status בהתאם (warning אם יש בעיות)
  - לוגים warnings לצורך ניטור

**השפעה צפויה:**
- זיהוי מוקדם של בעיות
- מדדי איכות למעקב
- אפשרות ל-re-processing אוטומטי
- ניטור שיפור לאורך זמן

---

## 🔄 שינויים ב-Ingestion Pipeline

### קובץ: `ingestion_pipeline.py`

**שיפורים:**

1. **יבוא מודולים חדשים:**
   ```python
   from app.services.resumes.embedding_utils import (
       enrich_chunk_for_embedding,
       create_search_optimized_embedding_text,
   )
   from app.services.resumes.validation import validate_extraction
   ```

2. **שיפור `parse_and_extract()`:**
   - הוספת validation אחרי extraction
   - שמירת quality report ב-metadata
   - logging של warnings
   - עדכון status בהתאם לתוצאות

3. **שיפור `chunk_and_embed()`:**
   - שימוש ב-`create_search_optimized_embedding_text()` לfull-resume
   - העשרת כל chunk עם `enrich_chunk_for_embedding()`
   - העברת person_name ו-extraction_json לכל chunk

---

## 📈 יתרונות משולבים

### איכות המידע המופק (LLM)
- ✅ פרומפטים מפורטים → תוצאות מדויקות יותר
- ✅ כללי validation מובנים → פחות שגיאות
- ✅ נרמול אחיד → consistency
- ✅ טיפול חכם בתאריכים וקטגוריות

### איכות ה-Embeddings
- ✅ Chunks עם הקשר מלא → semantic similarity טובה יותר
- ✅ העשרה עם metadata → הבנת context
- ✅ Full-resume embedding מותאם → חיפוש ראשוני מדויק
- ✅ Section-aware embeddings → התאמות ממוקדות

### ניטור ואיכות
- ✅ Validation אוטומטי → זיהוי בעיות מוקדם
- ✅ Quality scores → מדדים למעקב
- ✅ Recommendations → הנחיות לפעולה
- ✅ Logging → ניטור שיפור

---

## 🚀 שימוש

### לא נדרש שינוי בקוד קיים!

כל השיפורים משולבים אוטומטית בפייפליין:

```python
# Same API as before
resume = run_full_ingestion(db, path)

# Now with:
# - Better LLM extraction
# - Enhanced embeddings
# - Quality validation
# - Automatic reporting
```

### גישה ל-Quality Report:

```python
extraction = resume.extraction_json
quality_report = extraction.get("meta", {}).get("quality_report", {})

print(f"Quality Score: {quality_report['quality_score']}")
print(f"Status: {quality_report['status']}")
print(f"Errors: {quality_report['errors']}")
print(f"Warnings: {quality_report['warnings']}")
```

---

## 📝 המלצות לשימוש

### 1. Re-process Existing Resumes
- שקול לעבד מחדש קורות חיים קיימים
- השוואת quality scores לפני/אחרי
- זיהוי resumes שצריכים manual review

### 2. Monitoring
- עקוב אחר quality scores
- זיהוי patterns של בעיות
- שיפור prompts בהתאם לממצאים

### 3. Thresholds
- הגדר threshold מינימלי (למשל: 0.7)
- סמן resumes מתחת לthreshold ל-review
- דחה אוטומטית resumes עם critical errors

### 4. Fine-tuning
- איסוף feedback על התאמות
- שיפור prompts בהתאם
- התאמת chunking parameters לפי צורך

---

## 🎯 תוצאות צפויות

### טווח קצר (מיידי)
- ✅ חילוץ מידע מדויק יותר מ-LLM
- ✅ פחות false positives בהתאמות
- ✅ זיהוי בעיות באיכות

### טווח בינוני (שבועות)
- ✅ שיפור ב-match quality scores
- ✅ פחות manual review נדרש
- ✅ מדדי איכות עקביים

### טווח ארוך (חודשים)
- ✅ מערכת self-improving (מבוססת על feedback)
- ✅ ROI גבוה יותר מהמערכת
- ✅ database איכותי של קורות חיים

---

## 🔧 טכנולוגיות ושיטות

- **LLM Prompting**: Few-shot + Detailed instructions
- **RAG Enhancement**: Context-aware embeddings
- **Chunking Strategy**: Semantic + Structural
- **Validation**: Multi-level quality checks
- **Monitoring**: Comprehensive quality metrics

---

## 📞 תמיכה והמשך

אם יש שאלות או צורך בשיפורים נוספים:
1. בדוק את ה-quality reports
2. נתח patterns של warnings/errors
3. שפר prompts בהתאם
4. התאם thresholds לצרכים שלך

**בהצלחה! 🎉**
