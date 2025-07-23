# main.py

import os
from agents import load_agents, create_tasks
from pipeline import build_crew, run_pipeline

if __name__ == "__main__":
    print("🤖 Initializing Fair Hiring Pipeline...")
    
    # 1. Load / define agents
    print("👥 Loading agents...")
    matcher, auditor = load_agents()
    print(f"👤 Hiring Specialist: {matcher.role}")
    print(f"👤 Bias Auditor: {auditor.role}")

    # 2. Create tasks for each agent
    print("📋 Creating tasks...")
    job_matching_task, bias_audit_task = create_tasks(matcher, auditor)
    print(f"📄 Job Matching Task: {job_matching_task.description[:50]}...")
    print(f"📄 Bias Audit Task: {bias_audit_task.description[:50]}...")

    # 3. Build the crew workflow
    print("🔧 Building crew...")
    crew = build_crew(matcher, auditor, job_matching_task, bias_audit_task)

    # 4. Example candidate data
    sample_row = {
        "Resume": """
        Jason Jones
        Senior Software Engineer
        
        Experience:
        - 5 years at TechCorp as Senior Software Engineer
        - Led team of 4 developers on e-commerce platform
        - Proficient in Python, JavaScript, React, Django
        - Experience with AWS, Docker, and microservices
        - Bachelor's degree in Computer Science
        
        Skills:
        - Full-stack development
        - Team leadership
        - Agile methodologies
        - Database design and optimization
        """,
        "Job_Description": """
        E-Commerce Specialist
        
        We are seeking a passionate E-Commerce Specialist to join our team at the forefront 
        of machine learning and online retail innovation. 
        
        Requirements:
        - 3+ years of experience in software development
        - Strong background in web technologies
        - Experience with e-commerce platforms
        - Leadership experience preferred
        - Degree in Computer Science or related field
        
        Responsibilities:
        - Lead development of e-commerce features
        - Collaborate with cross-functional teams
        - Implement best practices for scalable systems
        """,
        "Transcript": """
        Interviewer: Good morning Jason, thank you for joining us today. Can you tell us about your experience with e-commerce platforms?

        Jason: Thank you for having me. Over the past 5 years, I've been working extensively with e-commerce systems. At TechCorp, I led the development of our main e-commerce platform which processes over 10,000 transactions daily. I've worked with payment gateways, inventory management, and customer analytics.

        Interviewer: That's impressive. How do you handle team leadership and what's your approach to mentoring junior developers?

        Jason: I believe in leading by example and creating an inclusive environment. I've mentored 3 junior developers who have all been promoted during my tenure. I focus on code reviews, pair programming, and ensuring everyone has opportunities to grow.

        Interviewer: Excellent. Do you have any questions for us?

        Jason: Yes, I'm curious about the machine learning aspects mentioned in the job description. How does the team integrate AI into the e-commerce experience?
        """,
        "Role": "E-Commerce Specialist"
    }

    # 5. Run the pipeline and display results
    print("\n" + "="*50)
    print("🚀 RUNNING HIRING PIPELINE")
    print("="*50)
    
    results = run_pipeline(crew, sample_row)
    
    print("\n" + "="*50)
    print("📊 PIPELINE RESULTS")
    print("="*50)
    print(f"✅ Results: {results}")
    print("\n📁 Check the 'hiring-pipeline-output' directory for detailed JSON reports.")
