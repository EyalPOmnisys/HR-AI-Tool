"""
Tech Roles Knowledge Base - Static mappings for high-tech job titles.

This module provides comprehensive mappings of job titles, synonyms, and related terms
across all major tech roles to improve semantic matching accuracy.

Used by: title_matcher.py for keyword-based boost calculations.
"""

from typing import Dict, Set, List
from dataclasses import dataclass


@dataclass
class RoleCategory:
    """Represents a category of related job roles."""
    canonical_name: str
    synonyms: Set[str]
    related_terms: Set[str]
    seniority_levels: Set[str]
    technologies: Set[str]


# =============================================================================
# CORE ROLE CATEGORIES
# =============================================================================

ROLE_CATEGORIES = {
    # -------------------------------------------------------------------------
    # SOFTWARE DEVELOPMENT
    # -------------------------------------------------------------------------
    "software_engineer": RoleCategory(
        canonical_name="Software Engineer",
        synonyms={
            "software engineer", "software developer", "programmer",
            "coder", "application developer", "software dev",
            "swe", "engineer", "developer"
        },
        related_terms={
            "software", "development", "coding", "programming",
            "application", "system"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr",
            "lead", "principal", "staff", "distinguished"
        },
        technologies={
            "java", "python", "javascript", "c++", "c#", "go", "rust",
            "typescript", "kotlin", "swift", "scala", "ruby"
        }
    ),
    
    "full_stack": RoleCategory(
        canonical_name="Full Stack Developer",
        synonyms={
            "full stack developer", "full stack engineer", "fullstack developer",
            "fullstack engineer", "full-stack developer", "full-stack engineer",
            "fs developer", "fs engineer", "full stack dev"
        },
        related_terms={
            "full stack", "fullstack", "full-stack", "frontend", "backend",
            "front-end", "back-end", "web development", "web dev"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr", "lead", "principal"
        },
        technologies={
            "react", "angular", "vue", "node", "express", "django", "flask",
            "spring", "mongodb", "postgresql", "mysql", "redis"
        }
    ),
    
    "frontend": RoleCategory(
        canonical_name="Frontend Developer",
        synonyms={
            "frontend developer", "frontend engineer", "front-end developer",
            "front-end engineer", "front end developer", "ui developer",
            "web developer", "client-side developer", "fe developer"
        },
        related_terms={
            "frontend", "front-end", "front end", "ui", "user interface",
            "web", "client-side", "browser", "spa", "responsive"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr", "lead", "principal"
        },
        technologies={
            "react", "angular", "vue", "javascript", "typescript", "html", "css",
            "sass", "webpack", "nextjs", "redux", "tailwind", "bootstrap"
        }
    ),
    
    "backend": RoleCategory(
        canonical_name="Backend Developer",
        synonyms={
            "backend developer", "backend engineer", "back-end developer",
            "back-end engineer", "server-side developer", "api developer",
            "be developer", "backend dev"
        },
        related_terms={
            "backend", "back-end", "back end", "server-side", "api",
            "microservices", "rest", "graphql", "database"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr", "lead", "principal"
        },
        technologies={
            "node", "python", "java", "go", "c#", "ruby", "php",
            "spring", "django", "flask", "express", "fastapi",
            "postgresql", "mongodb", "redis", "kafka", "rabbitmq"
        }
    ),
    
    "mobile": RoleCategory(
        canonical_name="Mobile Developer",
        synonyms={
            "mobile developer", "mobile engineer", "mobile app developer",
            "ios developer", "android developer", "mobile dev",
            "app developer", "mobile software engineer"
        },
        related_terms={
            "mobile", "ios", "android", "app", "application",
            "mobile app", "cross-platform", "native", "hybrid"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr", "lead", "principal"
        },
        technologies={
            "swift", "kotlin", "react native", "flutter", "ios", "android",
            "xcode", "objective-c", "java", "dart", "xamarin"
        }
    ),
    
    # -------------------------------------------------------------------------
    # DATA & AI
    # -------------------------------------------------------------------------
    "data_scientist": RoleCategory(
        canonical_name="Data Scientist",
        synonyms={
            "data scientist", "ds", "data science engineer",
            "applied scientist", "research scientist", "ai scientist"
        },
        related_terms={
            "data science", "machine learning", "ml", "ai", "analytics",
            "statistics", "modeling", "prediction", "algorithm"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr", "lead",
            "principal", "staff", "chief"
        },
        technologies={
            "python", "r", "sql", "pandas", "numpy", "scikit-learn",
            "tensorflow", "pytorch", "spark", "jupyter", "tableau"
        }
    ),
    
    "ml_engineer": RoleCategory(
        canonical_name="Machine Learning Engineer",
        synonyms={
            "machine learning engineer", "ml engineer", "mle",
            "ai engineer", "deep learning engineer", "ml ops engineer"
        },
        related_terms={
            "machine learning", "ml", "ai", "deep learning", "neural networks",
            "nlp", "computer vision", "mlops", "model deployment"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr", "lead",
            "principal", "staff"
        },
        technologies={
            "python", "tensorflow", "pytorch", "keras", "scikit-learn",
            "spark", "mlflow", "kubeflow", "aws sagemaker", "cuda"
        }
    ),
    
    "data_engineer": RoleCategory(
        canonical_name="Data Engineer",
        synonyms={
            "data engineer", "de", "big data engineer",
            "data platform engineer", "analytics engineer"
        },
        related_terms={
            "data engineering", "etl", "data pipeline", "big data",
            "data warehouse", "data lake", "batch processing", "streaming"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr", "lead",
            "principal", "staff"
        },
        technologies={
            "python", "sql", "spark", "kafka", "airflow", "hadoop",
            "snowflake", "redshift", "bigquery", "databricks", "aws", "gcp"
        }
    ),
    
    "data_analyst": RoleCategory(
        canonical_name="Data Analyst",
        synonyms={
            "data analyst", "business analyst", "bi analyst",
            "analytics specialist", "reporting analyst"
        },
        related_terms={
            "data analysis", "analytics", "business intelligence", "bi",
            "reporting", "visualization", "dashboards", "metrics"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr", "lead"
        },
        technologies={
            "sql", "excel", "python", "r", "tableau", "power bi",
            "looker", "google analytics", "metabase", "superset"
        }
    ),
    
    # -------------------------------------------------------------------------
    # DEVOPS & INFRASTRUCTURE
    # -------------------------------------------------------------------------
    "devops": RoleCategory(
        canonical_name="DevOps Engineer",
        synonyms={
            "devops engineer", "devops", "site reliability engineer", "sre",
            "infrastructure engineer", "platform engineer", "cloud engineer"
        },
        related_terms={
            "devops", "sre", "infrastructure", "automation", "ci/cd",
            "deployment", "monitoring", "orchestration", "cloud"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr", "lead",
            "principal", "staff"
        },
        technologies={
            "kubernetes", "docker", "terraform", "ansible", "jenkins",
            "aws", "azure", "gcp", "linux", "bash", "python", "prometheus"
        }
    ),
    
    "cloud_architect": RoleCategory(
        canonical_name="Cloud Architect",
        synonyms={
            "cloud architect", "cloud solutions architect",
            "aws architect", "azure architect", "gcp architect"
        },
        related_terms={
            "cloud", "architecture", "aws", "azure", "gcp", "cloud native",
            "serverless", "infrastructure", "scalability"
        },
        seniority_levels={
            "mid-level", "senior", "sr", "lead", "principal", "chief"
        },
        technologies={
            "aws", "azure", "gcp", "kubernetes", "terraform", "cloudformation",
            "lambda", "s3", "ec2", "rds", "dynamodb", "api gateway"
        }
    ),
    
    # -------------------------------------------------------------------------
    # SECURITY
    # -------------------------------------------------------------------------
    "security_engineer": RoleCategory(
        canonical_name="Security Engineer",
        synonyms={
            "security engineer", "cybersecurity engineer", "infosec engineer",
            "application security engineer", "appsec engineer"
        },
        related_terms={
            "security", "cybersecurity", "infosec", "appsec", "devsecops",
            "penetration testing", "vulnerability", "encryption"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr", "lead",
            "principal", "chief"
        },
        technologies={
            "siem", "ids", "ips", "firewall", "vpn", "ssl", "tls",
            "oauth", "jwt", "kali", "metasploit", "burp suite"
        }
    ),
    
    # -------------------------------------------------------------------------
    # QA & TESTING
    # -------------------------------------------------------------------------
    "qa_engineer": RoleCategory(
        canonical_name="QA Engineer",
        synonyms={
            "qa engineer", "quality assurance engineer", "test engineer",
            "sdet", "qa automation engineer", "qa tester", "quality engineer"
        },
        related_terms={
            "qa", "quality assurance", "testing", "test automation",
            "manual testing", "automated testing", "test cases"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr", "lead"
        },
        technologies={
            "selenium", "cypress", "jest", "junit", "pytest", "testng",
            "postman", "jmeter", "appium", "cucumber", "robot framework"
        }
    ),
    
    # -------------------------------------------------------------------------
    # PRODUCT & DESIGN
    # -------------------------------------------------------------------------
    "product_manager": RoleCategory(
        canonical_name="Product Manager",
        synonyms={
            "product manager", "pm", "product owner", "po",
            "technical product manager", "senior product manager"
        },
        related_terms={
            "product management", "product", "roadmap", "backlog",
            "user stories", "agile", "scrum", "feature", "requirements"
        },
        seniority_levels={
            "associate", "mid-level", "senior", "sr", "lead",
            "principal", "director", "vp", "head", "chief"
        },
        technologies={
            "jira", "confluence", "asana", "trello", "miro",
            "figma", "analytics", "sql", "api"
        }
    ),
    
    "ux_designer": RoleCategory(
        canonical_name="UX Designer",
        synonyms={
            "ux designer", "user experience designer", "ux/ui designer",
            "product designer", "interaction designer", "ui/ux designer"
        },
        related_terms={
            "ux", "ui", "user experience", "user interface", "design",
            "wireframes", "prototypes", "user research", "usability"
        },
        seniority_levels={
            "junior", "jr", "mid-level", "senior", "sr", "lead",
            "principal", "head", "director"
        },
        technologies={
            "figma", "sketch", "adobe xd", "invision", "miro",
            "photoshop", "illustrator", "html", "css", "prototyping"
        }
    ),
    
    # -------------------------------------------------------------------------
    # ARCHITECTURE & LEADERSHIP
    # -------------------------------------------------------------------------
    "solutions_architect": RoleCategory(
        canonical_name="Solutions Architect",
        synonyms={
            "solutions architect", "software architect", "system architect",
            "enterprise architect", "technical architect"
        },
        related_terms={
            "architecture", "system design", "design patterns",
            "scalability", "microservices", "distributed systems"
        },
        seniority_levels={
            "mid-level", "senior", "sr", "lead", "principal",
            "chief", "distinguished"
        },
        technologies={
            "aws", "azure", "gcp", "microservices", "rest", "graphql",
            "kafka", "kubernetes", "docker", "system design"
        }
    ),
    
    "engineering_manager": RoleCategory(
        canonical_name="Engineering Manager",
        synonyms={
            "engineering manager", "em", "development manager",
            "software engineering manager", "team lead", "tech lead"
        },
        related_terms={
            "management", "leadership", "team", "agile", "scrum",
            "people management", "technical leadership"
        },
        seniority_levels={
            "mid-level", "senior", "sr", "director", "vp",
            "head", "chief", "cto"
        },
        technologies={
            "agile", "scrum", "kanban", "jira", "git",
            "technical stack varies"
        }
    ),
}


# =============================================================================
# REVERSE MAPPINGS
# =============================================================================

def build_term_to_category_map() -> Dict[str, List[str]]:
    """Build a map from terms to category names for fast lookup."""
    term_map = {}
    
    for category_name, category in ROLE_CATEGORIES.items():
        # Add all synonyms
        for synonym in category.synonyms:
            if synonym not in term_map:
                term_map[synonym] = []
            term_map[synonym].append(category_name)
        
        # Add related terms
        for term in category.related_terms:
            if term not in term_map:
                term_map[term] = []
            if category_name not in term_map[term]:
                term_map[term].append(category_name)
    
    return term_map


# Pre-built lookup map
TERM_TO_CATEGORY = build_term_to_category_map()


# =============================================================================
# CROSS-ROLE SIMILARITIES
# =============================================================================

SIMILAR_ROLES = {
    # Software Development similarities
    "software_engineer": ["full_stack", "backend", "frontend", "mobile"],
    "full_stack": ["software_engineer", "backend", "frontend"],
    "backend": ["software_engineer", "full_stack", "data_engineer", "devops"],
    "frontend": ["software_engineer", "full_stack", "ux_designer"],
    "mobile": ["software_engineer", "frontend"],
    
    # Data & AI similarities
    "data_scientist": ["ml_engineer", "data_analyst", "data_engineer"],
    "ml_engineer": ["data_scientist", "data_engineer", "backend"],
    "data_engineer": ["data_scientist", "ml_engineer", "backend", "devops"],
    "data_analyst": ["data_scientist", "data_engineer"],
    
    # Infrastructure similarities
    "devops": ["cloud_architect", "backend", "security_engineer", "data_engineer"],
    "cloud_architect": ["devops", "solutions_architect"],
    "security_engineer": ["devops", "backend"],
    
    # QA similarities
    "qa_engineer": ["backend", "frontend", "devops"],
    
    # Product & Design similarities
    "product_manager": ["ux_designer"],
    "ux_designer": ["frontend", "product_manager"],
    
    # Architecture & Leadership
    "solutions_architect": ["cloud_architect", "backend", "devops"],
    "engineering_manager": ["software_engineer", "solutions_architect"],
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_role_category(title: str) -> str:
    """
    Identify the role category for a given job title.
    
    Args:
        title: Job title string
        
    Returns:
        Category name or "unknown"
    """
    title_lower = title.lower()
    
    # Check direct matches
    for category_name, category in ROLE_CATEGORIES.items():
        if any(syn in title_lower for syn in category.synonyms):
            return category_name
    
    return "unknown"


def are_roles_similar(role1: str, role2: str) -> bool:
    """
    Check if two role categories are similar/related.
    
    Args:
        role1: First role category name
        role2: Second role category name
        
    Returns:
        True if roles are related
    """
    if role1 == role2:
        return True
    
    if role1 in SIMILAR_ROLES:
        return role2 in SIMILAR_ROLES[role1]
    
    return False


def extract_all_terms_from_title(title: str) -> Set[str]:
    """
    Extract all known terms from a job title.
    
    Args:
        title: Job title string
        
    Returns:
        Set of matched terms
    """
    title_lower = title.lower()
    matched_terms = set()
    
    # Check against all known terms
    for term in TERM_TO_CATEGORY.keys():
        if term in title_lower:
            matched_terms.add(term)
    
    return matched_terms


def get_role_similarity_boost(job_title: str, resume_title: str) -> float:
    """
    Calculate similarity boost based on role category matching.
    
    Args:
        job_title: Job title from job posting
        resume_title: Job title from resume
        
    Returns:
        Boost value (0-15)
    """
    job_category = get_role_category(job_title)
    resume_category = get_role_category(resume_title)
    
    if job_category == "unknown" or resume_category == "unknown":
        return 0.0
    
    # Same category - strong boost
    if job_category == resume_category:
        return 15.0
    
    # Similar categories - moderate boost
    if are_roles_similar(job_category, resume_category):
        return 10.0
    
    return 0.0


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test role category detection
    test_cases = [
        ("Software Engineer", "Senior Full Stack Developer"),
        ("DevOps Engineer", "Site Reliability Engineer"),
        ("Data Scientist", "Machine Learning Engineer"),
        ("Backend Developer", "Python Developer"),
        ("Frontend Developer", "React Developer"),
        ("QA Engineer", "Test Automation Engineer"),
        ("Product Manager", "Technical Product Manager"),
        ("Cloud Architect", "AWS Solutions Architect"),
    ]
    
    print("=" * 80)
    print("TECH ROLES KNOWLEDGE BASE - Test Results")
    print("=" * 80)
    
    for job_title, resume_title in test_cases:
        job_cat = get_role_category(job_title)
        resume_cat = get_role_category(resume_title)
        boost = get_role_similarity_boost(job_title, resume_title)
        
        print(f"\nJob: {job_title:40s} → {job_cat}")
        print(f"Resume: {resume_title:37s} → {resume_cat}")
        print(f"Boost: {boost:.1f} points")
    
    print("\n" + "=" * 80)
