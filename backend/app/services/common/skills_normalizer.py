# app/services/common/skills_normalizer.py
"""Central skills normalizer - single source of truth for canonicalizing tech skill names:
maps variations (Node/nodejs/Node.js) to standard forms, ensures perfect consistency across resumes, jobs, and matching.

OLD DESCRIPTION:
Central Skills Normalizer - Single source of truth for skill name normalization.

This module ensures perfect consistency across the entire system:
- Resume extraction (deterministic & LLM)
- Job extraction
- Matching algorithm

ALL skill names must pass through normalize_skill() to ensure:
1. Perfect matching between resumes and jobs
2. No false negatives due to spelling variations
3. Consistent display names across the UI

CRITICAL: This is the ONLY place where skill normalization logic should exist.
"""
from __future__ import annotations

import re
from typing import Optional, Set, Dict, List

# ============================================================================
# COMPREHENSIVE SKILL NORMALIZATION DICTIONARY
# ============================================================================
# Keys: ALL possible variations (lowercase, with spaces/dots/hyphens)
# Values: Canonical display name (proper capitalization)
#
# Design principles:
# 1. Cover ALL common variations (typos, abbreviations, versions)
# 2. Use industry-standard capitalization for display
# 3. Map variations to ONE canonical name
# 4. Include popular misspellings
# ============================================================================

SKILL_NORMALIZATION_MAP: Dict[str, str] = {
    # ========== JAVASCRIPT ECOSYSTEM ==========
    # JavaScript
    "javascript": "JavaScript",
    "java script": "JavaScript",
    "js": "JavaScript",
    "ecmascript": "JavaScript",
    "es6": "JavaScript",
    "es2015": "JavaScript",
    "es2020": "JavaScript",
    
    # TypeScript
    "typescript": "TypeScript",
    "type script": "TypeScript",
    "ts": "TypeScript",
    
    # Node.js
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "node js": "Node.js",
    "node-js": "Node.js",
    "nodej": "Node.js",
    
    # React
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "react js": "React",
    "react-js": "React",
    
    # Angular
    "angular": "Angular",
    "angularjs": "Angular",
    "angular.js": "Angular",
    "angular js": "Angular",
    "angular2": "Angular",
    "angular 2": "Angular",
    "angular 4": "Angular",
    "angular 8": "Angular",
    "angular 10": "Angular",
    "angular 12": "Angular",
    "angular 14": "Angular",
    "angular 15": "Angular",
    "angular 16": "Angular",
    "angular 17": "Angular",
    
    # Vue
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "vue js": "Vue.js",
    "vue2": "Vue.js",
    "vue3": "Vue.js",
    
    # Express
    "express": "Express",
    "expressjs": "Express",
    "express.js": "Express",
    "express js": "Express",
    
    # NestJS
    "nest": "NestJS",
    "nestjs": "NestJS",
    "nest.js": "NestJS",
    "nest js": "NestJS",
    
    # Next.js
    "next": "Next.js",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "next js": "Next.js",
    
    # ========== PYTHON ECOSYSTEM ==========
    # Python
    "python": "Python",
    "py": "Python",
    "python3": "Python",
    "python 3": "Python",
    "python2": "Python",
    "python 2": "Python",
    "python 3.7": "Python",
    "python 3.8": "Python",
    "python 3.9": "Python",
    "python 3.10": "Python",
    "python 3.11": "Python",
    "python 3.12": "Python",
    
    # Django
    "django": "Django",
    "django rest": "Django",
    "djangorestframework": "Django REST Framework",
    "django rest framework": "Django REST Framework",
    "drf": "Django REST Framework",
    
    # Flask
    "flask": "Flask",
    
    # FastAPI
    "fastapi": "FastAPI",
    "fast api": "FastAPI",
    "fast-api": "FastAPI",
    
    # Data Science libs
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scipy": "SciPy",
    "matplotlib": "Matplotlib",
    "scikit-learn": "Scikit-learn",
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    
    # ML frameworks
    "tensorflow": "TensorFlow",
    "tensor flow": "TensorFlow",
    "tf": "TensorFlow",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "keras": "Keras",
    
    # ========== DATABASES ==========
    # MongoDB
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "mongo db": "MongoDB",
    "mongo-db": "MongoDB",
    
    # PostgreSQL
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "postgre": "PostgreSQL",
    "psql": "PostgreSQL",
    "postgres sql": "PostgreSQL",
    "postgres-sql": "PostgreSQL",
    
    # MySQL
    "mysql": "MySQL",
    "my sql": "MySQL",
    "my-sql": "MySQL",
    
    # Redis
    "redis": "Redis",
    
    # SQL
    "sql": "SQL",
    "t-sql": "T-SQL",
    "tsql": "T-SQL",
    "pl/sql": "PL/SQL",
    "plsql": "PL/SQL",
    
    # NoSQL
    "nosql": "NoSQL",
    "no sql": "NoSQL",
    "no-sql": "NoSQL",
    
    # Elasticsearch
    "elasticsearch": "Elasticsearch",
    "elastic search": "Elasticsearch",
    "elastic": "Elasticsearch",
    
    # ========== DEVOPS & INFRASTRUCTURE ==========
    # Docker
    "docker": "Docker",
    
    # Kubernetes
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "k8": "Kubernetes",
    
    # Git
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "bitbucket": "Bitbucket",
    
    # CI/CD
    "jenkins": "Jenkins",
    "circleci": "CircleCI",
    "circle ci": "CircleCI",
    "travis": "Travis CI",
    "travis ci": "Travis CI",
    "github actions": "GitHub Actions",
    "gitlab ci": "GitLab CI",
    "bamboo": "Bamboo",
    "teamcity": "TeamCity",
    "azure devops": "Azure DevOps",
    
    # Cloud platforms
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "azure": "Azure",
    "microsoft azure": "Azure",
    
    # OpenShift
    "openshift": "OpenShift",
    "open shift": "OpenShift",
    
    # Linux
    "linux": "Linux",
    "ubuntu": "Linux",
    "centos": "Linux",
    "redhat": "Red Hat",
    "red hat": "Red Hat",
    
    # ========== C# / .NET ==========
    # C#
    "c#": "C#",
    "csharp": "C#",
    "c sharp": "C#",
    "c-sharp": "C#",
    
    # .NET
    ".net": ".NET",
    "dotnet": ".NET",
    "dot net": ".NET",
    ".net core": ".NET Core",
    "dotnet core": ".NET Core",
    ".net framework": ".NET Framework",
    
    # ASP.NET
    "asp.net": "ASP.NET",
    "asp net": "ASP.NET",
    "aspnet": "ASP.NET",
    
    # ========== JAVA ECOSYSTEM ==========
    # Java
    "java": "Java",
    "java8": "Java",
    "java 8": "Java",
    "java11": "Java",
    "java 11": "Java",
    "java17": "Java",
    "java 17": "Java",
    
    # Spring
    "spring": "Spring",
    "spring boot": "Spring Boot",
    "springboot": "Spring Boot",
    "spring framework": "Spring",
    
    # ========== MOBILE ==========
    # React Native
    "react native": "React Native",
    "react-native": "React Native",
    "reactnative": "React Native",
    
    # Flutter
    "flutter": "Flutter",
    
    # Swift
    "swift": "Swift",
    "swiftui": "SwiftUI",
    
    # Kotlin
    "kotlin": "Kotlin",
    
    # Android
    "android": "Android",
    
    # iOS
    "ios": "iOS",
    
    # ========== WEB TECHNOLOGIES ==========
    # HTML
    "html": "HTML",
    "html5": "HTML",
    "html 5": "HTML",
    
    # CSS
    "css": "CSS",
    "css3": "CSS",
    "css 3": "CSS",
    
    # Tailwind
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "tailwind css": "Tailwind CSS",
    
    # Bootstrap
    "bootstrap": "Bootstrap",
    
    # SASS/SCSS
    "sass": "SASS",
    "scss": "SCSS",
    
    # ========== STATE MANAGEMENT ==========
    # Redux
    "redux": "Redux",
    "react-redux": "Redux",
    "react redux": "Redux",
    
    # NgRx
    "ngrx": "NgRx",
    
    # MobX
    "mobx": "MobX",
    
    # ========== MAPPING & GIS ==========
    # Cesium
    "cesium": "Cesium",
    "cesiumjs": "Cesium",
    "cesium.js": "Cesium",
    
    # OpenLayers
    "openlayers": "OpenLayers",
    "open layers": "OpenLayers",
    
    # Leaflet
    "leaflet": "Leaflet",
    "leafletjs": "Leaflet",
    
    # GIS
    "gis": "GIS",
    "gis pro": "ArcGIS Pro",
    "arcgis": "ArcGIS",
    "arcgis pro": "ArcGIS Pro",
    "arc gis": "ArcGIS",
    "arc gis pro": "ArcGIS Pro",
    "qgis": "QGIS",
    
    # ========== TESTING ==========
    # Jest
    "jest": "Jest",
    
    # Mocha
    "mocha": "Mocha",
    
    # Cypress
    "cypress": "Cypress",
    "cypress.io": "Cypress",
    
    # Selenium
    "selenium": "Selenium",
    
    # Pytest
    "pytest": "Pytest",
    
    # ========== OTHER LANGUAGES ==========
    # Go
    "go": "Go",
    "golang": "Go",
    
    # Rust
    "rust": "Rust",
    
    # PHP
    "php": "PHP",
    "php7": "PHP",
    "php8": "PHP",
    
    # Ruby
    "ruby": "Ruby",
    "ruby on rails": "Ruby on Rails",
    "rails": "Ruby on Rails",
    "ror": "Ruby on Rails",
    
    # C++
    "c++": "C++",
    "cpp": "C++",
    "cplusplus": "C++",
    
    # C
    "c": "C",
    
    # R
    "r": "R",
    "rstudio": "R",
    
    # Scala
    "scala": "Scala",
    
    # ========== NETWORKING & SECURITY ==========
    # Wireshark
    "wireshark": "Wireshark",
    
    # Scapy
    "scapy": "Scapy",
    
    # Mission Planner
    "mission planner": "Mission Planner",
    "missionplanner": "Mission Planner",
    
    # Splunk
    "splunk": "Splunk",
    
    # ========== GRAPHQL & APIS ==========
    # GraphQL
    "graphql": "GraphQL",
    "graph ql": "GraphQL",
    
    # REST
    "rest": "REST",
    "rest api": "REST API",
    "restful": "REST",
    "restful api": "REST API",
    
    # ========== MESSAGE QUEUES ==========
    # RabbitMQ
    "rabbitmq": "RabbitMQ",
    "rabbit mq": "RabbitMQ",
    
    # Kafka
    "kafka": "Kafka",
    "apache kafka": "Kafka",
    
    # ========== BIG DATA ==========
    # Spark
    "spark": "Apache Spark",
    "apache spark": "Apache Spark",
    "pyspark": "PySpark",
    
    # Hadoop
    "hadoop": "Hadoop",
    "apache hadoop": "Hadoop",
    
    # Airflow
    "airflow": "Apache Airflow",
    "apache airflow": "Apache Airflow",
    
    # ========== OTHER TOOLS ==========
    # Jira
    "jira": "Jira",
    "atlassian jira": "Jira",
    
    # Confluence
    "confluence": "Confluence",
    "atlassian confluence": "Confluence",
    
    # Bamboo
    "bamboo": "Bamboo",
    "atlassian bamboo": "Bamboo",
    
    # Figma
    "figma": "Figma",
    
    # Postman
    "postman": "Postman",
}

# Additional patterns for version number removal
VERSION_PATTERNS = [
    r'\s+v?\d+(\.\d+)*\s*$',  # "Angular 8", "Python 3.9", "Node v14.5"
    r'\s+\d{4}\s*$',           # "ES2020"
]


def normalize_skill(raw_skill: str) -> str:
    """
    Normalize a skill name to its canonical form.
    
    This is the SINGLE source of truth for skill normalization.
    ALL skills in the system (resumes, jobs, matching) must pass through this function.
    
    Args:
        raw_skill: Any variation of a skill name (e.g., "node", "nodejs", "Node.js 14")
    
    Returns:
        Canonical skill name (e.g., "Node.js")
    
    Examples:
        normalize_skill("node") -> "Node.js"
        normalize_skill("Node.js 14") -> "Node.js"
        normalize_skill("angular 8") -> "Angular"
        normalize_skill("PYTHON 3.9") -> "Python"
        normalize_skill("mongo") -> "MongoDB"
        normalize_skill("k8s") -> "Kubernetes"
    """
    if not raw_skill or not isinstance(raw_skill, str):
        return raw_skill
    
    # Step 1: Remove version numbers
    cleaned = raw_skill.strip()
    for pattern in VERSION_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    
    # Step 2: Normalize to lowercase for lookup
    lookup_key = cleaned.lower()
    
    # Step 3: Try exact match in dictionary
    if lookup_key in SKILL_NORMALIZATION_MAP:
        return SKILL_NORMALIZATION_MAP[lookup_key]
    
    # Step 4: Try with common suffixes removed (.js, js, etc.)
    # "angular.js" -> "angular"
    for suffix in ['.js', 'js', '.ts', 'ts']:
        if lookup_key.endswith(suffix):
            base = lookup_key[:-len(suffix)].strip()
            if base in SKILL_NORMALIZATION_MAP:
                return SKILL_NORMALIZATION_MAP[base]
    
    # Step 5: If no match, return title-cased version (fallback)
    # This preserves unknowns skills but makes them look nice
    return cleaned.title()


def normalize_skill_list(skills: List[str]) -> List[str]:
    """
    Normalize a list of skills and remove duplicates.
    
    Args:
        skills: List of raw skill names
    
    Returns:
        List of normalized, deduplicated skill names
    
    Example:
        normalize_skill_list(["Node", "nodejs", "Node.js 14", "React"])
        -> ["Node.js", "React"]
    """
    if not skills:
        return []
    
    seen: Set[str] = set()
    normalized: List[str] = []
    
    for skill in skills:
        if not skill:
            continue
        
        canonical = normalize_skill(skill)
        
        # Deduplicate by canonical name (case-insensitive)
        canonical_lower = canonical.lower()
        if canonical_lower not in seen:
            seen.add(canonical_lower)
            normalized.append(canonical)
    
    return normalized


def are_skills_equivalent(skill1: str, skill2: str) -> bool:
    """
    Check if two skill names refer to the same skill.
    
    Args:
        skill1: First skill name
        skill2: Second skill name
    
    Returns:
        True if they normalize to the same canonical form
    
    Examples:
        are_skills_equivalent("node", "Node.js") -> True
        are_skills_equivalent("angular 8", "Angular 14") -> True
        are_skills_equivalent("mongo", "MongoDB") -> True
        are_skills_equivalent("React", "Vue") -> False
    """
    return normalize_skill(skill1).lower() == normalize_skill(skill2).lower()


def get_all_canonical_skills() -> Set[str]:
    """
    Get all canonical skill names defined in the system.
    
    Useful for:
    - Autocomplete
    - Validation
    - Analytics
    
    Returns:
        Set of all canonical skill names
    """
    return set(SKILL_NORMALIZATION_MAP.values())


# ============================================================================
# UTILITY FUNCTIONS FOR SPECIFIC USE CASES
# ============================================================================

def normalize_skill_dict(skill_dict: Dict[str, any]) -> Dict[str, any]:
    """
    Normalize the 'name' field in a skill dictionary (for extraction results).
    
    Args:
        skill_dict: Dict with at least a 'name' key
    
    Returns:
        Same dict with normalized 'name'
    
    Example:
        normalize_skill_dict({"name": "nodejs", "weight": 1.0})
        -> {"name": "Node.js", "weight": 1.0}
    """
    if isinstance(skill_dict, dict) and 'name' in skill_dict:
        skill_dict['name'] = normalize_skill(skill_dict['name'])
    return skill_dict


def normalize_tech_array(tech: List[str]) -> List[str]:
    """
    Normalize a 'tech' array from experience/job (removes versions, deduplicates).
    
    Args:
        tech: List of technology names
    
    Returns:
        Normalized, deduplicated list
    
    Example:
        normalize_tech_array(["Angular 8", "Node.js", "node", "MongoDB"])
        -> ["Angular", "Node.js", "MongoDB"]
    """
    return normalize_skill_list(tech)
