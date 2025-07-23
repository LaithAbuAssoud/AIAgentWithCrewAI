# agents.py

import os
# Disable AgentOps completely

from crewai import Agent, Task, LLM
from pydantic import BaseModel, Field
from typing import List

# Initialize LLMs - only using CREWAI_API_KEY
api_key = os.getenv("CREWAI_API_KEY")
if not api_key:
    raise ValueError("CREWAI_API_KEY environment variable is required")

# job_matching_llm = LLM(model="gemini/gemma-3-27b-it", temperature=0.3, api_key=api_key)
# bias_detection_llm = LLM(model="gemini/gemma-3-27b-it", temperature=0.2, api_key=api_key)

llm = LLM(
    model="gemini/gemini-2.5-pro",
    # temperature=0.7,
    api_key=api_key,
)

# Pydantic models for structured outputs
class HiringDecision(BaseModel):
    decision: str = Field(..., description="Either 'select' or 'reject'")
    reasoning: str = Field(..., description="Detailed reasoning for the decision")
    score: float = Field(..., description="Confidence score from 0 to 1")

class BiasAuditResult(BaseModel):
    audit_result: str = Field(..., description="Either 'biased' or 'unbiased'")
    bias_indicators: List[str] = Field(..., description="List of potential bias indicators found")
    confidence: float = Field(..., description="Confidence in bias assessment from 0 to 1")
    recommendations: List[str] = Field(..., description="Recommendations to improve fairness")

def load_agents():
    # --- Agent 1: Job Matching ---
    job_matcher = Agent(
        role="Senior Hiring Decision Maker",
        goal="Evaluate candidates thoroughly and make final hiring decisions (SELECT or REJECT) with comprehensive reasoning based on job requirements and candidate qualifications",
        backstory=(
            "You are a senior hiring manager with 15+ years of experience in talent acquisition. "
            "Your expertise lies in making decisive hiring choices by thoroughly analyzing resumes, "
            "job requirements, and interview performance. You are known for providing clear, "
            "well-reasoned decisions that explain exactly why a candidate should be hired or not."
        ),
        llm=llm,
        verbose=True,
    )

    # --- Agent 2: Bias Auditor ---
    bias_auditor = Agent(
        role="Decision Validation Specialist",
        goal="Review hiring decisions to ensure they are fair, unbiased, and provide a final validated decision (SELECT or REJECT) with reasoning that confirms the decision is merit-based",
        backstory=(
            "You are an expert in fair hiring practices and decision validation with a background "
            "in organizational psychology and bias detection. Your role is to review hiring decisions, "
            "ensure they are based on relevant qualifications, and provide a final validated decision. "
            "You excel at identifying when decisions are truly merit-based and providing clear reasoning."
        ),
        llm=llm,
        verbose=True,
    )

    return job_matcher, bias_auditor

def create_tasks(job_matcher, bias_auditor):
    # Task 1: Job Matching Decision
    job_matching_task = Task(
        description="""
        Make a comprehensive hiring decision by analyzing:
        - Resume: Evaluate experience, skills, education, and achievements
        - Job Description: Match candidate qualifications against role requirements
        - Interview Transcript: Assess communication skills, cultural fit, and technical knowledge
        - Overall Role Fit: Determine if candidate meets the job criteria
        
        You must provide:
        1. A clear decision: SELECT or REJECT
        2. Detailed reasoning explaining your decision
        3. Specific examples from the candidate data supporting your choice
        """,
        expected_output="DECISION: [SELECT or REJECT]\n\nREASONING: A detailed explanation of why this candidate should be hired or not hired, including specific evidence from their resume, interview performance, and alignment with job requirements.",
        agent=job_matcher
    )

    # Task 2: Decision Validation and Final Recommendation
    bias_audit_task = Task(
        description="""
        Review the initial hiring decision and provide a final validated recommendation by:
        - Analyzing if the decision was based on relevant job qualifications
        - Checking for any bias or unfair reasoning in the evaluation
        - Verifying the decision aligns with merit-based criteria
        - Ensuring all relevant candidate strengths/weaknesses were considered
        
        Provide:
        1. Final validated decision: SELECT or REJECT
        2. Confirmation that the decision is fair and merit-based
        3. Complete reasoning for the final recommendation
        """,
        expected_output="A bias audit result (BIASED or UNBIASED) with explanation of any bias indicators found and recommendations for improvement.",
        agent=bias_auditor
    )

    return job_matching_task, bias_audit_task
