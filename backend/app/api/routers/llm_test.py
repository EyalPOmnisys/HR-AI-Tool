# LLM Testing endpoint for manual testing and debugging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging
import asyncio
import json
from functools import partial

from app.services.common.llm_client import default_llm_client
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger("api.llm_test")


class LLMTestRequest(BaseModel):
    """Request for testing LLM."""
    prompt: str = Field(min_length=1, max_length=10000)
    system_prompt: str | None = Field(default=None, max_length=5000)
    response_format: str = Field(default="text", pattern="^(text|json)$")


class LLMTestResponse(BaseModel):
    """Response from LLM test."""
    prompt: str
    response: str
    model: str
    provider: str


@router.post("/llm/test", response_model=LLMTestResponse)
async def test_llm(request: LLMTestRequest):
    """
    Test LLM with a custom prompt.
    
    This endpoint is for debugging and testing the LLM configuration.
    You can send a prompt and optionally a system prompt, and get back the LLM response.
    
    Args:
        prompt: The user prompt to send to the LLM
        system_prompt: Optional system prompt (defaults to "You are a helpful assistant")
        response_format: "text" or "json" - determines response parsing
        
    Returns:
        LLMTestResponse with the prompt, response, model, and provider
    """
    logger.info("=" * 80)
    logger.info("LLM TEST ENDPOINT")
    logger.info("=" * 80)
    
    # Determine provider and model
    if not settings.LLM_CHAT_MODEL:
        raise HTTPException(
            status_code=400,
            detail="LLM_CHAT_MODEL not configured. Please set Ollama model in environment."
        )
    
    provider = "Ollama"
    model = settings.LLM_CHAT_MODEL
    
    logger.info(f"Provider: {provider}")
    logger.info(f"Model: {model}")
    logger.info(f"Response format: {request.response_format}")
    logger.info(f"Prompt length: {len(request.prompt)} characters")
    logger.info("")
    
    # Build messages
    system_content = request.system_prompt or "You are a helpful assistant."
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": request.prompt}
    ]
    
    logger.info("📤 Sending to LLM:")
    logger.info(f"   System: {system_content[:100]}...")
    logger.info(f"   User: {request.prompt[:200]}...")
    logger.info("")
    
    try:
        # Call LLM based on response format
        loop = asyncio.get_event_loop()
        
        if request.response_format == "json":
            logger.info("Calling LLM with JSON response format...")
            response = await loop.run_in_executor(
                None,
                partial(default_llm_client.chat_json, messages, timeout=120)
            )
            # Convert JSON response to string for display
            response_text = json.dumps(response.data, ensure_ascii=False, indent=2)
        else:
            logger.info("Calling LLM with text response format...")
            response_text = await loop.run_in_executor(
                None,
                partial(default_llm_client.chat_text, messages, timeout=120)
            )
        
        logger.info("📥 Received from LLM:")
        logger.info(f"   Response length: {len(response_text)} characters")
        logger.info(f"   First 300 chars: {response_text[:300]}...")
        logger.info("")
        logger.info("=" * 80)
        
        return LLMTestResponse(
            prompt=request.prompt,
            response=response_text,
            model=model,
            provider=provider
        )
        
    except Exception as e:
        logger.error(f"❌ LLM call failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"LLM call failed: {str(e)}"
        )


class LLMJudgeTestResponse(BaseModel):
    """Response from LLM Judge simulation."""
    input_data: dict
    llm_response: dict
    model: str
    provider: str
    input_size_chars: int
    response_size_chars: int


@router.post("/llm/test-judge", response_model=LLMJudgeTestResponse)
async def test_llm_judge():
    """
    Simulate the LLM Judge evaluation with example data.
    
    This endpoint shows you EXACTLY what the LLM Judge sends and receives.
    It uses realistic example data (not from your actual DB) to demonstrate the flow.
    
    Returns:
        LLMJudgeTestResponse with the complete input/output data
    """
    logger.info("=" * 80)
    logger.info("LLM JUDGE SIMULATION TEST")
    logger.info("=" * 80)
    
    # Check LLM configuration
    if not settings.LLM_CHAT_MODEL:
        raise HTTPException(
            status_code=400,
            detail="LLM_CHAT_MODEL not configured. Please set Ollama model in environment."
        )
    
    provider = "Ollama"
    model = settings.LLM_CHAT_MODEL
    
    logger.info(f"Provider: {provider}")
    logger.info(f"Model: {model}")
    logger.info("")
    
    # Load the actual prompt used by LLM Judge
    from app.services.common.llm_client import load_prompt
    system_prompt = load_prompt("match/candidate_evaluation.prompt.txt")
    
    # Build EXAMPLE input data (exactly like LLM Judge does)
    example_job_data = {
        "title": "Senior Full Stack Developer",
        "description": "We are looking for an experienced Full Stack Developer to join our growing team. You will work on building scalable web applications using modern technologies.",
        "free_text": "Remote work possible. Great company culture. Competitive salary.",
        "analysis": {
            "skills": {
                "must_have": ["React", "Node.js", "TypeScript", "PostgreSQL", "REST APIs"],
                "nice_to_have": ["Docker", "Kubernetes", "GraphQL", "AWS"]
            },
            "tech_stack": {
                "languages": ["JavaScript", "TypeScript", "Python"],
                "frameworks": ["React", "Node.js", "Express"],
                "databases": ["PostgreSQL", "Redis"],
                "tools": ["Docker", "Git", "CI/CD"]
            },
            "experience": {
                "years_min": 5,
                "years_max": 8
            },
            "responsibilities": [
                "Design and develop scalable web applications",
                "Collaborate with product team on features",
                "Mentor junior developers",
                "Review code and ensure quality"
            ],
            "qualifications": {
                "education": ["BS Computer Science or equivalent"],
                "required": ["5+ years web development", "Strong React/Node.js skills"]
            }
        }
    }
    
    example_candidates = [
        {
            "resume_id": "550e8400-e29b-41d4-a716-446655440000",
            "algorithmic_score": 87,
            "extraction": {
                "person": {
                    "name": "John Doe",
                    "emails": ["john.doe@example.com"],
                    "phones": ["+1-555-0123"],
                    "location": "Tel Aviv, Israel"
                },
                "summary": "Senior Full Stack Developer with 7 years of experience building scalable web applications. Specialized in React, Node.js, and cloud technologies.",
                "experience": [
                    {
                        "title": "Senior Full Stack Developer",
                        "company": "TechCorp",
                        "location": "Tel Aviv",
                        "start_date": "2020-01",
                        "end_date": "present",
                        "duration_years": 4.5,
                        "bullets": [
                            "Led development of microservices architecture serving 1M+ users",
                            "Mentored team of 5 junior developers",
                            "Improved API performance by 60%"
                        ],
                        "tech": ["React", "Node.js", "TypeScript", "PostgreSQL", "Docker", "AWS"],
                        "category": "tech"
                    },
                    {
                        "title": "Full Stack Developer",
                        "company": "StartupXYZ",
                        "location": "Tel Aviv",
                        "start_date": "2018-06",
                        "end_date": "2019-12",
                        "duration_years": 1.5,
                        "bullets": [
                            "Built RESTful APIs using Node.js/Express",
                            "Developed React frontend components",
                            "Implemented CI/CD pipeline"
                        ],
                        "tech": ["React", "Node.js", "MongoDB", "Express"],
                        "category": "tech"
                    }
                ],
                "experience_meta": {
                    "totals_by_category": {
                        "tech": 7.0,
                        "military": 0,
                        "hospitality": 0,
                        "other": 0
                    },
                    "primary_category": "tech",
                    "primary_years": 7.0,
                    "total_years": 7.0
                },
                "skills": [
                    {"name": "React", "source": "work_experience", "weight": 1.0, "category": "framework"},
                    {"name": "Node.js", "source": "work_experience", "weight": 1.0, "category": "runtime"},
                    {"name": "TypeScript", "source": "work_experience", "weight": 1.0, "category": "language"},
                    {"name": "PostgreSQL", "source": "work_experience", "weight": 1.0, "category": "database"},
                    {"name": "Docker", "source": "work_experience", "weight": 1.0, "category": "tool"},
                    {"name": "AWS", "source": "work_experience", "weight": 1.0, "category": "cloud"},
                    {"name": "GraphQL", "source": "skills_list", "weight": 0.6, "category": "api"},
                    {"name": "MongoDB", "source": "work_experience", "weight": 1.0, "category": "database"}
                ],
                "education": [
                    {
                        "degree": "B.Sc. Computer Science",
                        "field": "Computer Science",
                        "institution": "Tel Aviv University",
                        "start_date": "2014",
                        "end_date": "2018"
                    }
                ],
                "projects": [
                    {
                        "name": "Open Source Contributor",
                        "description": "Contributed to React ecosystem libraries",
                        "tech": ["React", "TypeScript", "Jest"]
                    }
                ],
                "languages": ["Hebrew", "English"],
                "certifications": ["AWS Solutions Architect"]
            }
        },
        {
            "resume_id": "660e8400-e29b-41d4-a716-446655440001",
            "algorithmic_score": 65,
            "extraction": {
                "person": {
                    "name": "Jane Smith",
                    "emails": ["jane.smith@example.com"],
                    "phones": ["+1-555-0456"],
                    "location": "Haifa, Israel"
                },
                "summary": "Full Stack Developer with 3 years of experience. Passionate about learning new technologies.",
                "experience": [
                    {
                        "title": "Full Stack Developer",
                        "company": "SmallCompany",
                        "location": "Haifa",
                        "start_date": "2021-03",
                        "end_date": "present",
                        "duration_years": 3.5,
                        "bullets": [
                            "Developed web applications using React and Node.js",
                            "Worked with MySQL database",
                            "Participated in agile sprints"
                        ],
                        "tech": ["React", "Node.js", "MySQL", "JavaScript"],
                        "category": "tech"
                    }
                ],
                "experience_meta": {
                    "totals_by_category": {
                        "tech": 3.5,
                        "military": 0,
                        "hospitality": 0,
                        "other": 0
                    },
                    "primary_category": "tech",
                    "primary_years": 3.5,
                    "total_years": 3.5
                },
                "skills": [
                    {"name": "React", "source": "work_experience", "weight": 1.0, "category": "framework"},
                    {"name": "Node.js", "source": "work_experience", "weight": 1.0, "category": "runtime"},
                    {"name": "JavaScript", "source": "work_experience", "weight": 1.0, "category": "language"},
                    {"name": "MySQL", "source": "work_experience", "weight": 1.0, "category": "database"},
                    {"name": "HTML", "source": "skills_list", "weight": 0.6, "category": "markup"},
                    {"name": "CSS", "source": "skills_list", "weight": 0.6, "category": "styling"}
                ],
                "education": [
                    {
                        "degree": "B.A. Information Systems",
                        "field": "Information Systems",
                        "institution": "Haifa University",
                        "start_date": "2017",
                        "end_date": "2021"
                    }
                ],
                "projects": [],
                "languages": ["Hebrew", "English"],
                "certifications": []
            }
        }
    ]
    
    # Build the exact input structure that LLM Judge sends
    user_prompt = {
        "job": example_job_data,
        "candidates": example_candidates
    }
    
    # Calculate input size
    input_json = json.dumps(user_prompt, ensure_ascii=False, indent=2)
    input_size = len(input_json)
    
    logger.info("📋 Example Input Structure:")
    logger.info(f"   Job: {example_job_data['title']}")
    logger.info(f"   Candidates: {len(example_candidates)}")
    logger.info(f"   Input size: {input_size:,} characters")
    logger.info("")
    logger.info(f"   Candidate 1: {example_candidates[0]['extraction']['person']['name']} (algo_score={example_candidates[0]['algorithmic_score']})")
    logger.info(f"   Candidate 2: {example_candidates[1]['extraction']['person']['name']} (algo_score={example_candidates[1]['algorithmic_score']})")
    logger.info("")
    
    # Prepare messages exactly like LLM Judge
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": input_json}
    ]
    
    logger.info("📤 Sending to LLM...")
    
    try:
        # Call LLM with JSON response format (like LLM Judge does)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            partial(default_llm_client.chat_json, messages, timeout=180)
        )
        
        # Parse response
        content_dict = response.data
        response_json = json.dumps(content_dict, ensure_ascii=False, indent=2)
        response_size = len(response_json)
        
        logger.info("📥 Received from LLM:")
        logger.info(f"   Response size: {response_size:,} characters")
        
        # Log evaluations summary
        evaluations = content_dict.get("evaluations", [])
        logger.info(f"   Evaluations received: {len(evaluations)}")
        for idx, ev in enumerate(evaluations, 1):
            resume_id = ev.get("resume_id", "unknown")
            final_score = ev.get("final_score", 0)
            recommendation = ev.get("recommendation", "unknown")
            logger.info(f"     [{idx}] score={final_score} rec={recommendation}")
        
        logger.info("")
        logger.info("=" * 80)
        
        return LLMJudgeTestResponse(
            input_data=user_prompt,
            llm_response=content_dict,
            model=model,
            provider=provider,
            input_size_chars=input_size,
            response_size_chars=response_size
        )
        
    except Exception as e:
        logger.error(f"❌ LLM call failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"LLM Judge simulation failed: {str(e)}"
        )

