import type { CandidateRow } from '../types/match';

export interface VerdictData {
  label: string;
  count: number;
  color: string;
  percentage: number;
}

export interface ExperienceData {
  label: string;
  count: number;
  percentage: number;
  color: string;
}

export interface ScoreDistributionData {
  range: string;
  count: number;
  color: string;
}

export interface TopTalentMetrics {
  avgExperience: number;
  avgStability: number;
  highestScore: number;
  topCandidateName: string;
}

export interface AnalysisData {
  verdictBreakdown: VerdictData[];
  experienceDistribution: ExperienceData[];
  scoreDistribution: ScoreDistributionData[];
  topTalentStats: TopTalentMetrics;
  totalCandidates: number;
}

// Helper to parse experience string "5 yrs" -> 5
function parseExperience(expStr: string | null | undefined): number {
  if (!expStr) return 0;
  const match = expStr.match(/(\d+(\.\d+)?)/);
  return match ? parseFloat(match[0]) : 0;
}

export function calculateAnalysis(candidates: CandidateRow[]): AnalysisData {
  const total = candidates.length;
  if (total === 0) {
    return {
      verdictBreakdown: [],
      experienceDistribution: [],
      scoreDistribution: [],
      topTalentStats: { avgExperience: 0, avgStability: 0, highestScore: 0, topCandidateName: '' },
      totalCandidates: 0
    };
  }

  // 1. Verdict Breakdown
  const verdicts = {
    recommended: 0,
    shortlist: 0,
    concern: 0,
    reject: 0
  };

  candidates.forEach(c => {
    const score = c.match ?? 0;
    const v = c.llm_verdict?.toLowerCase() || '';
    
    if (v.includes('recommend') || score >= 85) verdicts.recommended++;
    else if (v.includes('shortlist') || score >= 75) verdicts.shortlist++;
    else if (v.includes('reject') || score < 60) verdicts.reject++;
    else verdicts.concern++; // Default/Middle ground
  });

  const verdictBreakdown: VerdictData[] = [
    { label: 'Highly Recommended', count: verdicts.recommended, color: '#10b981', percentage: Math.round((verdicts.recommended / total) * 100) },
    { label: 'Shortlist Potential', count: verdicts.shortlist, color: '#3b82f6', percentage: Math.round((verdicts.shortlist / total) * 100) },
    { label: 'Requires Review', count: verdicts.concern, color: '#f59e0b', percentage: Math.round((verdicts.concern / total) * 100) },
    { label: 'Not a Match', count: verdicts.reject, color: '#ef4444', percentage: Math.round((verdicts.reject / total) * 100) },
  ].filter(v => v.count > 0);

  // 2. Experience Level Distribution
  const expLevels = {
    junior: 0, // 0-2
    mid: 0,    // 3-5
    senior: 0, // 6-9
    expert: 0  // 10+
  };

  candidates.forEach(c => {
    const years = parseExperience(c.experience);
    if (years < 3) expLevels.junior++;
    else if (years < 6) expLevels.mid++;
    else if (years < 10) expLevels.senior++;
    else expLevels.expert++;
  });

  const experienceDistribution: ExperienceData[] = [
    { label: 'Junior (0-2y)', count: expLevels.junior, percentage: Math.round((expLevels.junior / total) * 100), color: '#94a3b8' },
    { label: 'Mid-Level (3-5y)', count: expLevels.mid, percentage: Math.round((expLevels.mid / total) * 100), color: '#60a5fa' },
    { label: 'Senior (6-9y)', count: expLevels.senior, percentage: Math.round((expLevels.senior / total) * 100), color: '#3b82f6' },
    { label: 'Expert (10y+)', count: expLevels.expert, percentage: Math.round((expLevels.expert / total) * 100), color: '#1d4ed8' },
  ].filter(e => e.count > 0); // Only show relevant levels

  // 3. Score Distribution
  const distribution = {
    '90-100': 0,
    '80-89': 0,
    '70-79': 0,
    '60-69': 0,
    '<60': 0
  };

  candidates.forEach(c => {
    const s = c.match ?? 0;
    if (s >= 90) distribution['90-100']++;
    else if (s >= 80) distribution['80-89']++;
    else if (s >= 70) distribution['70-79']++;
    else if (s >= 60) distribution['60-69']++;
    else distribution['<60']++;
  });

  const scoreDistribution: ScoreDistributionData[] = [
    { range: '90-100', count: distribution['90-100'], color: '#10b981' },
    { range: '80-89', count: distribution['80-89'], color: '#3b82f6' },
    { range: '70-79', count: distribution['70-79'], color: '#6366f1' },
    { range: '60-69', count: distribution['60-69'], color: '#f59e0b' },
    { range: '<60', count: distribution['<60'], color: '#ef4444' },
  ];

  // 4. Top Talent Metrics (Top 5)
  const sortedCandidates = [...candidates].sort((a, b) => (b.match ?? 0) - (a.match ?? 0));
  const top5 = sortedCandidates.slice(0, 5);
  
  const avgExperience = top5.length 
    ? top5.reduce((sum, c) => sum + parseExperience(c.experience), 0) / top5.length 
    : 0;
    
  const avgStability = top5.length
    ? top5.reduce((sum, c) => sum + (c.stability_score ?? 0), 0) / top5.length
    : 0;

  const topTalentStats: TopTalentMetrics = {
    avgExperience: parseFloat(avgExperience.toFixed(1)),
    avgStability: Math.round(avgStability),
    highestScore: top5.length > 0 ? (top5[0].match ?? 0) : 0,
    topCandidateName: top5.length > 0 ? (top5[0].candidate || 'Unknown') : '-'
  };

  return {
    verdictBreakdown,
    experienceDistribution,
    scoreDistribution,
    topTalentStats,
    totalCandidates: total
  };
}
