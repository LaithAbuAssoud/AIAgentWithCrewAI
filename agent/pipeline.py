# pipeline.py

import os

from crewai import Crew, Process

def build_crew(job_matcher, bias_auditor, job_matching_task, bias_audit_task):
    """
    Build a CrewAI crew with sequential process
    """
    
    crew = Crew(
        agents=[job_matcher, bias_auditor],
        tasks=[job_matching_task, bias_audit_task],
        process=Process.sequential,
        verbose=True
    )

    return crew

def run_pipeline(crew, row: dict):
    """
    Run the hiring pipeline with the given candidate data
    row keys: 'Resume', 'Job_Description', 'Transcript', 'Role'
    """
    print("🚀 Starting Fair Hiring Pipeline...")
    print(f"📋 Processing candidate for role: {row.get('Role', 'Unknown')}")
    
    try:
        # Run the crew with the input data
        results = crew.kickoff(inputs=row)
        
        print("\n✅ Pipeline completed successfully!")
        print("📊 Results have been saved to the output directory.")
        
        return results
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Try to provide more specific error information
        if "API" in str(e) or "authentication" in str(e).lower():
            print("💡 This might be an API key or authentication issue.")
            print("Make sure your CREWAI_API_KEY is valid and has the right permissions.")
        elif "model" in str(e).lower():
            print("💡 This might be a model configuration issue.")
            print("Check if the model name is correct for your API.")
        
        raise e
