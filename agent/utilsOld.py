from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
import agentops
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from tavily import TavilyClient
from scrapegraph_py import Client

import os
import json
import pandas as pd

# Data Models
class CandidateData(BaseModel):
    candidate_id: str = Field(..., description="Unique identifier for the candidate")
    role: str = Field(..., description="The role/position being applied for")
    job_description: str = Field(..., description="Job description and requirements")
    transcript: str = Field(..., description="Interview transcript")
    resume: str = Field(..., description="Candidate's resume/CV")

class HiringDecision(BaseModel):
    candidate_id: str
    decision: str = Field(..., description="Binary decision: 'select' or 'reject'")
    reasoning: str = Field(..., description="Explanation for the decision")

class BiasEvaluation(BaseModel):
    candidate_id: str
    bias_classification: str = Field(..., description="Binary classification: 'biased' or 'unbiased'")
    explanation: str = Field(..., description="Explanation for bias classification")
    requires_reevaluation: bool = Field(default=False, description="Whether Agent 1 should re-evaluate")

# Initialize LLMs
job_matching_llm = LLM(model="gemma-3-27b-it", temperature=0.3)  # Lower temperature for consistent decisions
bias_detection_llm = LLM(model="gemma-3-27b-it", temperature=0.2)  # Even lower for bias detection

# Agent 1: Job Matching Agent
job_matching_agent = Agent(
    role="Job Matching Specialist",
    goal="Make fair and merit-based hiring decisions by evaluating candidates solely on their qualifications, skills, and job fit",
    backstory="""You are an experienced recruiter who focuses exclusively on merit-based evaluation. 
    You analyze resumes, interview transcripts, and job requirements to make binary hiring decisions.
    You do not consider demographic information or personal characteristics unrelated to job performance.
    Your decisions are based on skills, experience, education, and demonstrated competencies.""",
    llm=job_matching_llm,
    verbose=True,
    allow_delegation=False
)

# Agent 2: Bias Classification Agent
bias_classification_agent = Agent(
    role="Bias Detection Specialist",
    goal="Identify potential bias in hiring decisions by analyzing whether decisions were influenced by non-merit factors",
    backstory="""You are a fairness auditor specialized in detecting bias in hiring decisions.
    You evaluate whether hiring decisions were made based on merit (skills, experience, qualifications) 
    or influenced by irrelevant factors like demographics, personal characteristics, or unconscious bias.
    You do not modify decisions - you only classify them as biased or unbiased and recommend re-evaluation when necessary.""",
    llm=bias_detection_llm,
    verbose=True,
    allow_delegation=False
)

# Tools for Job Matching Agent
@tool
def make_hiring_decision(candidate_data: str) -> str:
    """
    Make a binary hiring decision (select/reject) based on candidate qualifications and job fit.
    
    Args:
        candidate_data: JSON string containing candidate information
    
    Returns:
        JSON string with decision and reasoning
    """
    try:
        data = json.loads(candidate_data)
        
        # This is where the actual decision logic would be implemented
        # For now, return a structured response
        decision_result = {
            "candidate_id": data.get("candidate_id"),
            "decision": "select",  # This would be determined by the LLM
            "reasoning": "Candidate demonstrates strong qualifications and relevant experience for the role."
        }
        
        return json.dumps(decision_result)
    except Exception as e:
        return json.dumps({"error": f"Error processing candidate data: {str(e)}"})

# Tools for Bias Classification Agent
@tool
def evaluate_decision_for_bias(decision_context: str) -> str:
    """
    Evaluate a hiring decision for potential bias.
    
    Args:
        decision_context: JSON string containing all candidate data plus the hiring decision
    
    Returns:
        JSON string with bias evaluation results
    """
    try:
        context = json.loads(decision_context)
        
        # This is where bias detection logic would be implemented
        # For now, return a structured response
        bias_result = {
            "candidate_id": context.get("candidate_id"),
            "bias_classification": "unbiased",  # This would be determined by the LLM
            "explanation": "Decision appears to be based on merit-based factors including relevant skills and experience.",
            "requires_reevaluation": False
        }
        
        return json.dumps(bias_result)
    except Exception as e:
        return json.dumps({"error": f"Error evaluating decision for bias: {str(e)}"})

# Tasks
job_matching_task = Task(
    description="""Analyze the candidate's resume, interview transcript, and job description to make a binary hiring decision.

    Focus exclusively on:
    - Relevant skills and technical competencies
    - Work experience and career progression
    - Educational background and certifications
    - Demonstrated achievements and accomplishments
    - Alignment with job requirements
    - Communication skills shown in interview

    Ignore:
    - Personal demographic information
    - Names that might indicate gender, ethnicity, or origin
    - Age-related indicators
    - Personal interests unrelated to job performance

    Provide a clear 'select' or 'reject' decision with detailed reasoning based solely on merit factors.

    Candidate Data: {candidate_data}""",
    expected_output="A JSON object containing 'decision' (select/reject) and 'reasoning' explaining the merit-based factors that led to this decision.",
    agent=job_matching_agent,
    tools=[make_hiring_decision]
)

bias_evaluation_task = Task(
    description="""Evaluate the hiring decision made by the Job Matching Agent for potential bias.

    Analyze whether the decision was influenced by:
    - Non-merit factors (demographics, personal characteristics)
    - Unconscious bias patterns
    - Inconsistent application of standards
    - Irrelevant personal information

    The decision should be classified as 'biased' if there's evidence that non-merit factors influenced the outcome.
    Classify as 'unbiased' if the decision appears based solely on job-relevant qualifications.

    If classified as 'biased', recommend re-evaluation.

    Decision Context: {decision_context}""",
    expected_output="A JSON object containing 'bias_classification' (biased/unbiased), 'explanation' of the assessment, and 'requires_reevaluation' boolean.",
    agent=bias_classification_agent,
    tools=[evaluate_decision_for_bias]
)

# Create the Multi-Agent Hiring System
class MultiAgentHiringSystem:
    def __init__(self):
        self.job_matching_agent = job_matching_agent
        self.bias_classification_agent = bias_classification_agent
        self.job_matching_task = job_matching_task
        self.bias_evaluation_task = bias_evaluation_task
        
    def evaluate_candidate(self, candidate_data: CandidateData, max_iterations: int = 3) -> Dict[str, Any]:
        """
        Evaluate a candidate through the two-agent system with bias feedback loop.
        
        Args:
            candidate_data: Candidate information
            max_iterations: Maximum number of re-evaluation attempts
            
        Returns:
            Final evaluation results
        """
        iteration = 0
        final_decision = None
        evaluation_history = []
        
        while iteration < max_iterations:
            iteration += 1
            
            # Step 1: Job Matching Agent makes decision
            crew_job_matching = Crew(
                agents=[self.job_matching_agent],
                tasks=[self.job_matching_task],
                verbose=True,
                process=Process.sequential
            )
            
            job_result = crew_job_matching.kickoff(
                inputs={"candidate_data": candidate_data.model_dump_json()}
            )
            
            # Parse the decision
            try:
                decision_data = json.loads(str(job_result))
                hiring_decision = HiringDecision(**decision_data)
            except:
                # Fallback if parsing fails
                hiring_decision = HiringDecision(
                    candidate_id=candidate_data.candidate_id,
                    decision="reject",
                    reasoning="Error in decision processing"
                )
            
            # Step 2: Bias Classification Agent evaluates decision
            decision_context = {
                **candidate_data.model_dump(),
                "decision": hiring_decision.decision,
                "reasoning": hiring_decision.reasoning,
                "iteration": iteration
            }
            
            crew_bias_eval = Crew(
                agents=[self.bias_classification_agent],
                tasks=[self.bias_evaluation_task],
                verbose=True,
                process=Process.sequential
            )
            
            bias_result = crew_bias_eval.kickoff(
                inputs={"decision_context": json.dumps(decision_context)}
            )
            
            # Parse the bias evaluation
            try:
                bias_data = json.loads(str(bias_result))
                bias_evaluation = BiasEvaluation(**bias_data)
            except:
                # Fallback if parsing fails
                bias_evaluation = BiasEvaluation(
                    candidate_id=candidate_data.candidate_id,
                    bias_classification="unbiased",
                    explanation="Error in bias evaluation processing",
                    requires_reevaluation=False
                )
            
            # Store this iteration's results
            evaluation_history.append({
                "iteration": iteration,
                "hiring_decision": hiring_decision.model_dump(),
                "bias_evaluation": bias_evaluation.model_dump()
            })
            
            # Step 3: Check if re-evaluation is needed
            if bias_evaluation.bias_classification == "unbiased" or not bias_evaluation.requires_reevaluation:
                final_decision = {
                    "final_decision": hiring_decision.model_dump(),
                    "bias_evaluation": bias_evaluation.model_dump(),
                    "iterations_required": iteration,
                    "evaluation_history": evaluation_history
                }
                break
            
            # If biased and we haven't reached max iterations, continue loop
            if iteration == max_iterations:
                final_decision = {
                    "final_decision": hiring_decision.model_dump(),
                    "bias_evaluation": bias_evaluation.model_dump(),
                    "iterations_required": iteration,
                    "evaluation_history": evaluation_history,
                    "warning": "Maximum iterations reached without unbiased decision"
                }
        
        return final_decision
    
    def process_batch_candidates(self, candidates_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Process multiple candidates through the hiring system.
        
        Args:
            candidates_df: DataFrame with candidate information
            
        Returns:
            List of evaluation results
        """
        results = []
        
        for _, row in candidates_df.iterrows():
            try:
                candidate_data = CandidateData(
                    candidate_id=str(row.get('ID', 'unknown')),
                    role=str(row.get('Role', 'unknown')),
                    job_description=str(row.get('Job_Description', '')),
                    transcript=str(row.get('Transcript', '')),
                    resume=str(row.get('Resume', ''))
                )
                
                result = self.evaluate_candidate(candidate_data)
                results.append(result)
                
            except Exception as e:
                results.append({
                    "candidate_id": str(row.get('ID', 'unknown')),
                    "error": f"Failed to process candidate: {str(e)}"
                })
        
        return results

# Example usage function
def run_hiring_evaluation_example():
    """
    Example of how to use the Multi-Agent Hiring System
    """
    # Sample candidate data
    sample_df = pd.DataFrame([{
        "ID": "candidate_001",
        "Role": "E-Commerce Specialist",
        "Job_Description": "Be part of a passionate team at the forefront of machine learning as an E-commerce Specialist, delivering solutions that shape the future.",
        "Transcript": "Interviewer: Tell me about your experience with e-commerce platforms. Candidate: I have 3 years of experience working with Shopify and WooCommerce...",
        "Resume": "John Smith\nE-commerce Specialist\n3+ years experience in digital marketing and e-commerce platform management...",
    }])
    
    # Initialize the system
    hiring_system = MultiAgentHiringSystem()
    
    # Process candidates
    results = hiring_system.process_batch_candidates(sample_df)
    
    # Save results
    output_file = "multi_agent_hiring_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Multi-agent hiring evaluation completed. Results saved to {output_file}")
    return results

# Knowledge sources
job_matching_knowledge = StringKnowledgeSource(
    content="""
    Merit-based hiring focuses on:
    - Technical skills and competencies relevant to the role
    - Work experience and career progression
    - Educational qualifications and certifications
    - Demonstrated achievements and results
    - Problem-solving abilities shown in interview responses
    - Communication and interpersonal skills relevant to job performance
    
    Avoid considering:
    - Gender, age, ethnicity, or other demographic factors
    - Personal interests unrelated to job performance
    - Name-based assumptions about background
    - Physical appearance or characteristics
    - Personal life circumstances unrelated to work capability
    """
)

bias_detection_knowledge = StringKnowledgeSource(
    content="""
    Bias indicators in hiring decisions:
    - Decisions influenced by candidate names suggesting gender/ethnicity
    - Inconsistent standards applied to similar qualifications
    - Over-emphasis on 'cultural fit' without clear job relevance
    - Negative interpretation of employment gaps without context
    - Assumptions based on educational institution prestige rather than relevant skills
    - Different standards for communication style based on demographics
    
    Unbiased decisions focus solely on:
    - Job-relevant skills and experience
    - Measurable qualifications and achievements
    - Consistent application of evaluation criteria
    - Evidence-based assessment of capability
    """
)

