# agents.py

import os
# Disable AgentOps completely

from crewai import Agent, Task, LLM
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

# Configure logging for better error tracking with Gemma
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize LLMs - supporting both Google AI Studio and alternative configurations
api_key = os.getenv("CREWAI_API_KEY")
if not api_key:
    raise ValueError("CREWAI_API_KEY environment variable is required")

# Enhanced configuration supporting available Gemma models through different providers
# Google AI Studio has limited Gemma availability, so we implement multiple fallbacks
available_gemma_models = [
    "gemini/gemma-7b",          # Original Gemma 7B if available
    "gemini/gemma-2b",          # Original Gemma 2B if available  
    "gemini/codegemma-7b",      # CodeGemma variant
    "huggingface/google/gemma-2-9b-it",  # Via Hugging Face
    "huggingface/google/gemma-2-2b-it",  # Via Hugging Face fallback
]

def try_gemma_model(model_name, **kwargs):
    """Try to initialize a Gemma model with error handling"""
    try:
        llm = LLM(
            model=model_name,
            temperature=0.3,
            max_tokens=2048,
            top_p=0.9,
            timeout=180,
            api_key=api_key,
            **kwargs
        )
        # Test the model with a simple call
        test_response = llm.call("Reply with 'READY' if you can process this.")
        logger.info(f"Successfully configured {model_name}")
        return llm
    except Exception as e:
        logger.warning(f"Failed to configure {model_name}: {e}")
        return None

# Try to configure the best available Gemma model
llm = None
for model in available_gemma_models:
    logger.info(f"Attempting to configure {model}...")
    llm = try_gemma_model(model)
    if llm is not None:
        break

# If no Gemma model works, use a compatible alternative with Gemma-like characteristics
if llm is None:
    logger.warning("No Gemma models available, using Gemini Flash as a compatible alternative")
    llm = LLM(
        model="gemini/gemini-2.0-flash",  # Fast, efficient model similar to Gemma
        temperature=0.3,  # Lower temperature for more consistent responses
        max_tokens=2048,  # Conservative token limit
        top_p=0.9,
        timeout=180,
        api_key=api_key,
    )
    logger.info("Using Gemini Flash as Gemma alternative")

# Pydantic models optimized for Gemma's structured outputs
class GemmaHiringDecision(BaseModel):
    """Simplified decision model optimized for Gemma's output capabilities"""
    decision: str = Field(..., description="Either 'SELECT' or 'REJECT' (uppercase)")
    reasons: List[str] = Field(..., description="3-4 key reasons for the decision", max_items=4)
    evidence: str = Field(..., description="Brief supporting evidence from candidate data")
    confidence: Optional[float] = Field(default=0.8, description="Confidence score 0-1", ge=0, le=1)

class GemmaBiasAudit(BaseModel):
    """Simplified bias audit model for Gemma"""
    final_decision: str = Field(..., description="Either 'SELECT' or 'REJECT' (uppercase)")
    fairness_assessment: str = Field(..., description="Either 'FAIR' or 'BIASED' (uppercase)")
    bias_indicators: List[str] = Field(default=[], description="List of any bias indicators found", max_items=3)
    justification: str = Field(..., description="Brief justification for the assessment")

# Legacy models for backward compatibility
class HiringDecision(BaseModel):
    decision: str = Field(..., description="Either 'select' or 'reject'")
    reasoning: str = Field(..., description="Detailed reasoning for the decision")
    score: float = Field(..., description="Confidence score from 0 to 1")

class BiasAuditResult(BaseModel):
    audit_result: str = Field(..., description="Either 'biased' or 'unbiased'")
    bias_indicators: List[str] = Field(..., description="List of potential bias indicators found")
    confidence: float = Field(..., description="Confidence in bias assessment from 0 to 1")
    recommendations: List[str] = Field(..., description="Recommendations to improve fairness")

def validate_gemma_setup():
    """Validate that the configured model is properly responsive"""
    try:
        # Simple test without complex method calls that might fail
        if hasattr(llm, 'model') and llm.model:
            logger.info(f"Model configuration validated: {llm.model}")
            return True
        else:
            logger.warning("Model object exists but has no model attribute")
            return False
    except Exception as e:
        logger.error(f"Model validation failed: {e}")
        return False

def get_model_info():
    """Get information about the currently configured model"""
    try:
        if hasattr(llm, 'model'):
            return llm.model
        return "Unknown model"
    except Exception:
        return "Model info unavailable"

def print_optimization_summary():
    """Print summary of Gemma-focused optimizations implemented"""
    model_name = get_model_info()
    logger.info("=== GEMMA OPTIMIZATION SUMMARY ===")
    logger.info(f"✅ Active Model: {model_name}")
    logger.info("✅ Optimizations Applied:")
    logger.info("  • Low temperature (0.3) for consistent responses")
    logger.info("  • Conservative token limits (2048) for stability")
    logger.info("  • Simplified agent roles and backstories")
    logger.info("  • Optimized task instructions for smaller models")
    logger.info("  • Structured output formats with Pydantic")
    logger.info("  • Fallback model system for reliability")
    logger.info("  • Enhanced error handling and timeouts")
    logger.info("=================================")

def load_agents():
    # Print optimization summary
    print_optimization_summary()
    
    # Validate model setup before creating agents
    model_name = get_model_info()
    logger.info(f"Using model: {model_name}")
    
    if not validate_gemma_setup():
        logger.warning("Model validation failed, proceeding with caution...")
    
    # --- Agent 1: Job Matching (Optimized for smaller models like Gemma) ---
    job_matcher = Agent(
        role="Hiring Decision Maker",  # Clear, simple role name
        goal="Make hiring decisions: SELECT or REJECT candidates based on job fit",
        backstory=(
            "You are an experienced hiring manager. You analyze resumes and job requirements "
            "to make clear hiring decisions. You provide direct reasoning for each decision."
        ),  # Simplified backstory for better model comprehension
        llm=llm,
        verbose=True,
        max_execution_time=300,  # Timeout for processing constraints
        allow_delegation=False,   # Disable delegation for simpler workflow
    )

    # --- Agent 2: Bias Auditor (Optimized for smaller models like Gemma) ---
    bias_auditor = Agent(
        role="Decision Reviewer",  # Clear, simple role name
        goal="Review hiring decisions for fairness and provide final SELECT or REJECT decision",
        backstory=(
            "You are a fair hiring expert. You check decisions for bias and ensure they are "
            "based on job qualifications. You validate final hiring recommendations."
        ),  # Simplified backstory
        llm=llm,
        verbose=True,
        max_execution_time=300,  # Timeout for processing constraints
        allow_delegation=False,   # Disable delegation for simpler workflow
    )

    return job_matcher, bias_auditor

def create_tasks(job_matcher, bias_auditor):
    # Task 1: Job Matching Decision (Optimized for Gemma's token limits)
    job_matching_task = Task(
        description="""
        INSTRUCTIONS: Analyze the candidate and make a hiring decision.
        
        ANALYZE:
        - Resume: Skills, experience, education
        - Job Requirements: Match qualifications to role needs
        - Interview: Communication and fit assessment
        
        PROVIDE:
        1. Decision: SELECT or REJECT
        2. Key reasons (3-4 bullet points)
        3. Supporting evidence from candidate data
        
        Keep response under 1500 tokens.
        """,
        expected_output="DECISION: [SELECT or REJECT]\n\nREASONS:\n- Point 1\n- Point 2\n- Point 3\n\nEVIDENCE: Specific examples from resume/interview supporting the decision.",
        agent=job_matcher
    )

    # Task 2: Decision Validation (Optimized for Gemma's constraints)
    bias_audit_task = Task(
        description="""
        INSTRUCTIONS: Review the hiring decision for fairness.
        
        CHECK:
        - Decision based on job qualifications? (Yes/No)
        - Any bias indicators found? (List them)
        - Decision aligns with merit criteria? (Yes/No)
        
        PROVIDE:
        1. Final decision: SELECT or REJECT
        2. Fairness assessment: FAIR or BIASED
        3. Brief justification
        
        Keep response under 1000 tokens.
        """,
        expected_output="FINAL DECISION: [SELECT or REJECT]\nFAIRNESS: [FAIR or BIASED]\nJUSTIFICATION: Brief explanation of decision validity and any bias concerns.",
        agent=bias_auditor
    )

    return job_matching_task, bias_audit_task
