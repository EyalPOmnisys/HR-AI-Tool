import {
  FiSearch,
  FiCpu,
  FiZap,
  FiTrendingUp,
  FiCheckCircle,
  FiLayers,
  FiTarget,
  FiBarChart2,
  FiDatabase,
  FiFilter,
  FiUsers,
  FiGlobe,
  FiBriefcase,
  FiAward,
  FiTrendingDown,
  FiSliders,
  FiRefreshCw,
  FiEye,
  FiShuffle,
  FiActivity,
  FiFileText,
  FiGrid,
  FiList,
} from 'react-icons/fi';
import type { IconType } from 'react-icons';

export const loadingMessages = [
  'Initiating deep search across candidate database…',
  'Loading job requirements and company culture parameters…',
  'Processing AI analysis on skills and experience patterns…',
  'Filtering candidates based on qualification criteria…',
  'Analyzing multi-layer compatibility factors…',
  'Matching candidates to role-specific requirements…',
  'Running comprehensive analytics on top performers…',
  'Ranking candidates by relevance and potential fit…',
  'Optimizing recommendations with machine learning…',
  'Evaluating soft skills and cultural alignment…',
  'Cross-referencing industry experience and certifications…',
  'Assessing career trajectory and growth patterns…',
  'Analyzing communication styles and team dynamics…',
  'Calculating location preferences and availability…',
  'Processing education background and specializations…',
  'Reviewing portfolio quality and project complexity…',
  'Scoring technical proficiency across multiple domains…',
  'Identifying hidden talents and transferable skills…',
  'Calibrating salary expectations with market data…',
  'Generating personalized candidate profiles…',
  'Running final validation checks…',
  'Compiling comprehensive match reports…',
  'Preparing detailed insights and recommendations…',
  'Organizing results by priority tiers…',
  'Creating data visualizations and charts…',
  'Finalizing results and preparing insights dashboard…',
] as const;

export const loadingIcons: readonly IconType[] = [
  FiSearch,      // Search
  FiDatabase,    // Database loading
  FiCpu,         // AI processing
  FiFilter,      // Filtering
  FiLayers,      // Layer analysis
  FiTarget,      // Matching
  FiBarChart2,   // Analytics
  FiTrendingUp,  // Ranking
  FiZap,         // Optimization
  FiUsers,       // Soft skills analysis
  FiGlobe,       // Industry experience
  FiBriefcase,   // Career
  FiActivity,    // Communication
  FiSliders,     // Preferences
  FiFileText,    // Education
  FiGrid,        // Portfolio
  FiAward,       // Technical skills
  FiEye,         // Talent identification
  FiTrendingDown, // Salary
  FiShuffle,     // Profiles
  FiRefreshCw,   // Validation
  FiList,        // Reports
  FiBarChart2,   // Insights
  FiLayers,      // Priority sorting
  FiGrid,        // Visualizations
  FiCheckCircle, // Completion
];
