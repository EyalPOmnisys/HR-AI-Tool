#!/usr/bin/env python3
"""
Test script for resume processing improvements.
Demonstrates validation, quality checks, and enhanced embeddings.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.resumes.validation import (
    validate_extraction,
    validate_embedding_quality,
    create_quality_report
)


def test_extraction_validation():
    """Test validation of extracted resume data."""
    print("\n" + "="*60)
    print("Testing Extraction Validation")
    print("="*60)
    
    # Example 1: Good quality extraction
    good_extraction = {
        "person": {
            "name": "John Doe",
            "emails": [{"value": "john@example.com"}],
            "phones": [{"value": "+972501234567"}],
            "languages": ["English", "Hebrew"]
        },
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Tech Corp",
                "start_date": "2020-01",
                "end_date": "present",
                "bullets": ["Led team of 5", "Built scalable APIs"],
                "tech": ["Python", "FastAPI", "PostgreSQL", "Docker"]
            },
            {
                "title": "Software Engineer",
                "company": "StartupX",
                "start_date": "2018-06",
                "end_date": "2019-12",
                "bullets": ["Developed features", "Code reviews"],
                "tech": ["JavaScript", "React", "Node.js"]
            }
        ],
        "education": [
            {
                "degree": "B.Sc.",
                "field": "Computer Science",
                "institution": "Tel Aviv University",
                "end_date": "2018"
            }
        ],
        "skills": [
            {"name": "Python"},
            {"name": "React"},
            {"name": "PostgreSQL"},
            {"name": "Docker"},
            {"name": "AWS"}
        ],
        "experience_meta": {
            "totals_by_category": {
                "tech": 5.5,
                "military": 0,
                "hospitality": 0,
                "other": 0
            }
        }
    }
    
    result = validate_extraction(good_extraction)
    print(f"\n✅ Good Quality Resume:")
    print(f"   Valid: {result.is_valid}")
    print(f"   Quality Score: {result.quality_score:.2f}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Warnings: {len(result.warnings)}")
    if result.info:
        print(f"   Info: {result.info[0]}")
    
    # Example 2: Poor quality extraction
    poor_extraction = {
        "person": {"name": None},
        "experience": [
            {
                "title": None,
                "company": None,
                "start_date": "2020",
                "end_date": "2018"  # Invalid: end before start!
            }
        ],
        "education": [],
        "skills": [],
        "experience_meta": {}
    }
    
    result = validate_extraction(poor_extraction)
    print(f"\n❌ Poor Quality Resume:")
    print(f"   Valid: {result.is_valid}")
    print(f"   Quality Score: {result.quality_score:.2f}")
    print(f"   Errors: {result.errors}")
    print(f"   Warnings: {result.warnings}")


def test_embedding_validation():
    """Test validation of embedding vectors."""
    print("\n" + "="*60)
    print("Testing Embedding Validation")
    print("="*60)
    
    # Example 1: Good embedding
    import random
    good_embedding = [random.uniform(-1, 1) for _ in range(1536)]
    
    result = validate_embedding_quality(good_embedding)
    print(f"\n✅ Good Quality Embedding:")
    print(f"   Valid: {result.is_valid}")
    print(f"   Quality Score: {result.quality_score:.2f}")
    if result.info:
        print(f"   {result.info[0]}")
    
    # Example 2: Degenerate embedding (all zeros)
    bad_embedding = [0.0] * 1536
    
    result = validate_embedding_quality(bad_embedding)
    print(f"\n❌ Degenerate Embedding:")
    print(f"   Valid: {result.is_valid}")
    print(f"   Quality Score: {result.quality_score:.2f}")
    print(f"   Errors: {result.errors}")


def test_quality_report():
    """Test comprehensive quality report generation."""
    print("\n" + "="*60)
    print("Testing Quality Report")
    print("="*60)
    
    extraction = {
        "person": {
            "name": "Jane Smith",
            "emails": [{"value": "jane@example.com"}],
            "languages": ["English"]
        },
        "experience": [
            {
                "title": "Data Scientist",
                "company": "AI Labs",
                "start_date": "2021-03",
                "end_date": "present",
                "tech": ["Python", "TensorFlow", "Pandas"]
            }
        ],
        "education": [
            {
                "degree": "M.Sc.",
                "field": "Data Science",
                "institution": "MIT"
            }
        ],
        "skills": [
            {"name": "Python"},
            {"name": "Machine Learning"},
            {"name": "SQL"}
        ],
        "experience_meta": {
            "totals_by_category": {"tech": 3.7}
        }
    }
    
    import random
    embedding = [random.uniform(-1, 1) for _ in range(1536)]
    
    report = create_quality_report(extraction, embedding)
    
    print(f"\n📊 Quality Report:")
    print(f"   Overall Status: {report['overall']['status']}")
    print(f"   Overall Quality: {report['overall']['quality_score']}")
    print(f"\n   Extraction:")
    print(f"      Valid: {report['extraction']['valid']}")
    print(f"      Quality: {report['extraction']['quality_score']}")
    if report['extraction']['warnings']:
        print(f"      Warnings: {report['extraction']['warnings']}")
    print(f"\n   Embedding:")
    print(f"      Valid: {report['embedding']['valid']}")
    print(f"      Quality: {report['embedding']['quality_score']}")
    
    if report['recommendations']:
        print(f"\n   💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"      - {rec}")


def demo_chunking_improvements():
    """Demonstrate chunking improvements."""
    print("\n" + "="*60)
    print("Demonstrating Chunking Improvements")
    print("="*60)
    
    sample_resume = """
John Doe
john@example.com | +972-50-123-4567
Tel Aviv, Israel

PROFESSIONAL EXPERIENCE

Senior Software Engineer | Tech Corp | 2020 - Present
• Led development of microservices architecture serving 1M+ users
• Implemented CI/CD pipeline reducing deployment time by 70%
• Mentored team of 5 junior engineers
Technologies: Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS

Software Engineer | StartupX | 2018 - 2019
• Developed RESTful APIs for mobile application
• Optimized database queries improving performance by 40%
Technologies: Node.js, Express, MongoDB, React

EDUCATION

B.Sc. Computer Science | Tel Aviv University | 2014 - 2018
Focus: Algorithms and Data Structures

SKILLS

Languages: Python, JavaScript, TypeScript, Go
Frameworks: FastAPI, React, Node.js
Databases: PostgreSQL, MongoDB, Redis
DevOps: Docker, Kubernetes, Jenkins, AWS
"""
    
    print("\n📄 Sample Resume (truncated):")
    print(sample_resume[:200] + "...")
    
    print("\n🔧 Old Chunking Strategy:")
    print("   - Fixed size chunks (1200 chars)")
    print("   - Small overlap (160 chars)")
    print("   - No section awareness")
    print("   - No context enrichment")
    
    print("\n✨ New Chunking Strategy:")
    print("   - Header extraction (name, contact)")
    print("   - Section-aware chunking:")
    print("     • Experience: 2000 chars (keep roles together)")
    print("     • Skills: 1200 chars")
    print("     • Default: 1500 chars")
    print("   - Larger overlap (200-300 chars)")
    print("   - Language detection per chunk")
    print("   - Context enrichment:")
    print("     • Section prefixes ('Professional Experience:')")
    print("     • Candidate name")
    print("     • Years of experience metadata")


def demo_embedding_enrichment():
    """Demonstrate embedding enrichment."""
    print("\n" + "="*60)
    print("Demonstrating Embedding Enrichment")
    print("="*60)
    
    print("\n📝 Old Embedding Approach:")
    print("   Plain chunk text → embedding")
    print("   Example: 'Led development of microservices...'")
    
    print("\n✨ New Embedding Approach:")
    print("   Enriched text → embedding")
    print("   Example:")
    print("   '''")
    print("   Professional Experience:")
    print("   Candidate: John Doe")
    print("   Total Tech Experience: 5.5 years")
    print("   Led development of microservices...")
    print("   '''")
    
    print("\n🎯 Benefits:")
    print("   • Embeddings understand context (what type of info)")
    print("   • Identity matching (whose resume)")
    print("   • Better semantic similarity")
    print("   • More accurate job-candidate matching")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Resume Processing Improvements - Test Suite")
    print("="*60)
    
    try:
        test_extraction_validation()
        test_embedding_validation()
        test_quality_report()
        demo_chunking_improvements()
        demo_embedding_enrichment()
        
        print("\n" + "="*60)
        print("✅ All tests completed successfully!")
        print("="*60)
        print("\n💡 Next Steps:")
        print("   1. Re-process existing resumes with new pipeline")
        print("   2. Monitor quality scores")
        print("   3. Compare match results before/after")
        print("   4. Fine-tune prompts based on feedback")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
