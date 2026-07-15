// Single source of truth for the app version and the "What's New" list
// shown in the About modal. Update this file on every release.
// Display content is in Hebrew (recruiter-facing); tech names stay in English.

export type ChangelogEntry = {
  version: string
  date: string
  highlights: string[]
}

export const APP_VERSION = '1.3.0'

export const CHANGELOG: readonly ChangelogEntry[] = [
  {
    version: '1.3.0',
    date: 'יולי 2026',
    highlights: [
      'תובנות חכמות אחרי חיפוש — המערכת מזהה דרישת חובה שחוסמת מועמדים רבים וממליצה להפוך אותה ליתרון',
      'נימוקי ה-AI (חוזקות וחששות) מוצגים כעת בעברית',
      'בחירת אייקון אוטומטית למשרה לפי תחום התפקיד',
      'עמודת "תאריך הגשה" בטבלת ההתאמות',
      'חיפוש כישורים עם וגם/או (ALL/ANY) בעמוד המועמדים',
      'חיפוש וסינון משרה בהקלדה במסך ה-Candidate Search',
      'שיפור התאמת תפקיד למחליפי קריירה — התחשבות בהיסטוריה התעסוקתית',
      'מסך "אודות" עם גרסה ורשימת שינויים',
    ],
  },
  {
    version: '1.2.0',
    date: 'יולי 2026',
    highlights: [
      'מנוע ה-AI שודרג ל-Gemma 4 — ניתוח קורות חיים מהיר פי 4–5',
      'דירוג התאמות חכם יותר — טכנולוגיות קונקרטיות ודרישות רכות מוערכות בנפרד',
      'ניסיון מעבר לנדרש נחשב יתרון — מועמדים בכירים כבר לא נענשים',
      'קליטת קורות חיים עמידה יותר — פלט AI פגום לא מפיל קבצים שלמים',
      'ייעול ה-backend — הסרת שכבת החיפוש הווקטורי (RAG) הישנה',
    ],
  },
  {
    version: '1.1.0',
    date: 'יוני 2026',
    highlights: [
      'התאמה חכמה (Smart Backfill) — שופט ה-AI בוחן מועמדים עד שנמצאות מספיק התאמות חזקות',
      'לוח משרות עם ניתוח דרישות AI (חובה מול יתרון)',
      'קליטת קורות חיים אוטומטית עם תמיכה בעברית',
    ],
  },
]
