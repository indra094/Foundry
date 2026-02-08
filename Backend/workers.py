from models import InvestorReadiness
import threading
from queue import Queue
import time
from sqlalchemy import asc

from models import User as UserModel,Job, AIIdeaAnalysis,FinancialsModel, FounderAlignmentModel, OrganizationModel as OrgModel, OrgMember as OrgMemberModel
from pydantic_types import UserSchema, Workspace, UserOrgInfo, LoginRequest, CreateUserRequest, SetUserOrgInfoRequest, SetOnboardingRequest, MarketSchema, PersonaSchema, MilestoneSchema, RoadmapSchema, AnalysisPayload, FounderAlignmentResponse, FounderAlignmentResponseModel
import json
import os
from models import upsert_job
from google import genai
from google.genai import types
from database import SessionLocal
from models import DashboardModel
import datetime


job_status = {}

def build_prompt_from_org_and_founders(org, founders):
    """
    Build a structured prompt for AI idea analysis from organization data.
    """

    # --- Basic Org Info ---
    startup_type = getattr(org, "type", None) or "Not specified"
    problem_statement = getattr(org, "problem", None) or "Not specified"
    solution_statement = getattr(org, "solution", None) or "Not specified"
    
    # Optional fields
    name = getattr(org, "name", None) or "Not specified"
    industry = getattr(org, "industry", None) or "Not specified"
    geography = getattr(org, "geography", None) or "Not specified"
    stage = getattr(org, "stage", None) or "Not specified"
    customer = getattr(org, "customer", None) or "Not specified"

    founders = founders or []

    founder_summary = ""
    if founders:
        founder_summary = "\n\nFounders:\n"
        for user, org_member in founders:
            founder_summary += f"- {user.full_name} | Role: {org_member.role} | Experience: {user.industry_experience}\n"

    # --- Prompt Template ---
    prompt = f"""
You are an expert startup analyst.

You will analyze the startup idea and generate a detailed idea validation report.


Startup Details:
- Startup Name: {name}
- Industry: {industry}
- Geography: {geography}
- Stage: {stage}
- Customer: {customer}
- Startup Field: {startup_type}
- Problem Statement: {problem_statement}
- Solution by Startup: {solution_statement}

{founder_summary}

You must output the analysis in JSON format with the following structure:

{{
  "seed_funding_probability": int,   # 0-100
  "market": {{
      "tam_value": number,           # in billions USD
      "growth_rate_percent": number, # annual growth %
      "growth_index": number,        # 0-100 score
      "insight": string
  }},
  "investor": string,         # short paragraph
  "strengths": [string],
  "weaknesses": [string],
  "personas": [
      {{
        "name": string,
        "pain": string,
        "solution": string
      }}
  ],
  "roadmap": {{
      "recommended_stage": string,
      "min_capital": number,
      "max_capital": number,
      "milestones": [
        {{
          "label": string,
          "duration_days": number,
          "is_active": boolean
        }}
      ]
  }}
}}

Make sure to:
- Provide realistic market values and growth
- Be concise but specific
- Use bullet lists for strengths/weaknesses
- Provide 3 customer personas
- Provide 3-5 milestones
"""

    return prompt


def query_model(prompt: str, model: str) -> dict:
    """
    Calls Gemini model with a prompt and returns parsed JSON response.
    """
    print("QUERYING...")
    try:
        client = genai.Client(api_key=os.environ.get("API_KEY"))
        # Call the Gemini 3 Pro Preview model
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )

        if not response or not response.text:
            raise ValueError("Empty response from model")
        
    except Exception as e:
        raise RuntimeError(f"Error generating analysis: {str(e)}")
   
    return json.loads(response.text)

def build_prompt_from_users(users):
    """
    users: list of tuples (UserModel, OrgMemberModel)
    returns: string prompt
    """
    user_lines = []

    for user, org_member in users:
        user_lines.append(
            f"- Name: {user.full_name or 'Unknown'}\n"
            f"  Email: {user.email}\n"
            f"  Member Type: {org_member.member_type}\n"
            f"  Role: {org_member.role}\n"
            f"  Permission Level: {org_member.permission_level}\n"
            f"  Responsibility: {org_member.responsibility}\n"
            f"  Authority: {org_member.authority}\n"
            f"  Hours per Week: {org_member.hours_per_week}\n"
            f"  Start Date: {org_member.start_date}\n"
            f"  Planned Change: {org_member.planned_change}\n"
            f"  Status: {org_member.status}\n"
            f"  Cash Contribution: {org_member.cash_contribution}\n"
            f"  Salary: {org_member.salary}\n"
            f"  Bonus: {org_member.bonus}\n"
            f"  Equity %: {org_member.equity}\n"
            f"  Vesting: {org_member.vesting}\n"
            f"  Vesting Cliff (years): {org_member.vesting_cliff}\n"
            f"  Risk Tolerance: {org_member.risk_tolerance}\n"
            f"  Expectations: {org_member.expectations}\n"
        )

    prompt = f"""
Analyze founder alignment for a startup based on the information provided below.

Here are the current members of the org:

{''.join(user_lines)}

Your task:
1. Evaluate alignment across founders on:
   - Vision & commitment
   - Time and effort contribution
   - Authority vs responsibility balance
   - Incentives (salary, equity, vesting)
   - Risk tolerance compatibility
   - Governance clarity
2. Identify key alignment factors and misalignment risks.
3. Assign an overall alignment score (0–100).
4. Classify the overall risk level: Low, Medium, or High.
5. Identify the single most critical alignment risk.
6. Suggest concrete corrective actions.

Return ONLY valid JSON matching the following structure:

{{
  "score": number,
  "risk_level": "Low" | "Medium" | "High",
  "factors": {{
    "commitment_alignment": string,
    "role_clarity": string,
    "authority_balance": string,
    "time_commitment_balance": string,
    "equity_and_incentives": string,
    "risk_tolerance_alignment": string,
    "governance_and_decision_making": string
  }},
  "risks": [
    {{
      "risk": string,
      "severity": "Low" | "Medium" | "High",
      "description": string,
      "affected_roles": [string]
    }}
  ],
  "actions": [
    {{
      "action": string,
      "priority": "High" | "Medium" | "Low",
      "owner": string,
      "expected_outcome": string
    }}
  ],
  "primary_risk": string,
  "insight": string
}}

Guidelines:
- Be critical but fair.
- Assume early-stage startup context unless stated otherwise.
- If data is missing, infer conservatively and note it as a risk.
- Do NOT include any explanation outside the JSON.

"""

    return prompt


def founder_alignment_worker():
    while True:
        db = SessionLocal()

        job = None

        try:
            # ✅ Pick the oldest pending job of type 'founder_alignment'
            job = (
                db.query(Job)
                .filter(Job.type == "founder_alignment")
                .order_by(asc(Job.created_time))
                .first()
            )

            if not job:
                time.sleep(1)  # No job, wait a bit
                continue

            org_id = job.org_id
            job_id = job.id

            # Update job status
            job_status[job_id] = {"status": "RUNNING"}

            users = (
                db.query(UserModel, OrgMemberModel)
                .join(OrgMemberModel, OrgMemberModel.user_id == UserModel.id)
                .filter(OrgMemberModel.org_id == org_id)
                .all()
            )

            if not users:
                raise ValueError("No users found for this organization")

            prompt = build_prompt_from_users(users)
            
            analysis = {
                "score": 64,
                "risk_level": "Medium",
                "factors": {
                    "commitment_alignment": "Moderate alignment. CEO is fully committed. CTO is part-time and plans to reduce hours further, creating future execution risk.",
                    "role_clarity": "Roles are defined, but responsibilities overlap in hiring and team building. CTO has strong technical authority but low time commitment.",
                    "authority_balance": "Authority is uneven. CEO controls budget and strategy, CTO has technical authority only, COO has operations authority but limited decision power on budget.",
                    "time_commitment_balance": "Misaligned. CEO 60 hrs/week, CTO 25 hrs/week, COO 40 hrs/week. CTO’s time commitment is too low for the equity share.",
                    "equity_and_incentives": "Equity distribution favors CEO. CTO has high equity with high salary and low time commitment. COO has low equity but moderate salary and low risk tolerance.",
                    "risk_tolerance_alignment": "Mismatch. CEO is high risk, COO is low risk, CTO is medium risk. This can create tension in fundraising and growth pace.",
                    "governance_and_decision_making": "Moderate governance clarity. Budget control rests with CEO, but other founders may need formal voting or decision rules to avoid conflict."
                },
                "risks": [
                    {
                        "risk": "CTO under-commitment",
                        "severity": "High",
                        "description": "CTO contributes only 25 hours/week and plans to reduce further. Equity is 25% which is too high for part-time contribution.",
                        "affected_roles": ["CTO", "CEO"]
                    },
                    {
                        "risk": "Equity vs salary mismatch",
                        "severity": "Medium",
                        "description": "CTO has high salary and high equity, which reduces incentive to stay long-term if growth slows. COO has lower equity but takes significant operational burden.",
                        "affected_roles": ["CTO", "COO"]
                    },
                    {
                        "risk": "Decision-making bottleneck",
                        "severity": "Medium",
                        "description": "CEO controls budget and strategy, but operational and technical leaders are not formally included in governance decisions.",
                        "affected_roles": ["CEO", "CTO", "COO"]
                    }
                ],
                "actions": [
                    {
                        "action": "Reduce CTO equity or increase time commitment",
                        "priority": "High",
                        "owner": "CEO",
                        "expected_outcome": "Align CTO’s incentives with contribution and reduce future resentment."
                    },
                    {
                        "action": "Define a formal governance model",
                        "priority": "Medium",
                        "owner": "All founders",
                        "expected_outcome": "Clear decision rights, voting rules, and escalation process."
                    },
                    {
                        "action": "Rebalance COO incentives",
                        "priority": "Medium",
                        "owner": "CEO",
                        "expected_outcome": "Ensure COO feels fairly rewarded for operational execution (equity or bonus)."
                    }
                ],
                "primary_risk": "CTO under-commitment",
                "insight": "The founder team has a strong vision but a core execution risk exists due to the CTO’s part-time commitment and high equity. This is likely to cause conflict during scaling, hiring, and product delivery."
            }

            #analysis = query_model(
            #    prompt=prompt,
            #    model="gemini-3-pro-preview"
            #)

            

            # dict-style access ONLY
            
            alignment = (
                db.query(FounderAlignmentModel)
                .filter_by(org_id=org_id)
                .first()
            )

            # If not exists, create
            if not alignment:
                alignment = FounderAlignmentModel(org_id=org_id)
                db.add(alignment)

            # Assign fields from parsed JSON
            alignment.score = analysis.get("score", 0)
            alignment.risk_level = analysis.get("risk_level", "Low")
            alignment.factors = analysis.get("factors", {})
            alignment.risks = analysis.get("risks", [])
            alignment.actions = analysis.get("actions", [])
            alignment.primary_risk = analysis.get("primary_risk")
            alignment.insight = analysis.get("insight")
            alignment.model_version = "v1"
            alignment.id = org_id
            alignment.org_id = org_id
            
            db.commit()
            # -------------------------
            # 🟢 Call upsert_job for dashboard instead of queue
            # -------------------------
            upsert_job(db, org_id, "dashboard")

            # Mark job as completed
            job_status[job_id]["status"] = "COMPLETED"
            job_status[job_id]["result"] = {
                "message": "Founder alignment created/updated",
                "org_id": org_id
            }

            # -------------------------
            # 🗑 Delete job from DB
            # -------------------------
            try:
                db.delete(job)
                db.commit()
            except Exception:
                db.rollback()  # Ignore deletion failure

        except Exception as e:
            db.rollback()
            if job:
                job_status[job_id]["status"] = "FAILED"
                job_status[job_id]["error"] = str(e)
            print("founder alignment Exception:", str(e))

        finally:
            db.close()

def idea_analysis_worker():
    while True:
        
        db = SessionLocal()

        job = None

        try:
            # ✅ Pick the oldest pending job of type 'idea_analysis'
            job = (
                db.query(Job)
                .filter(Job.type == "idea_analysis")
                .order_by(asc(Job.created_time))
                .first()
            )

            if not job:
                time.sleep(1)  # No job, wait a bit
                continue

            org_id = job.org_id
            job_id = job.id

            # Update job status
            job_status[job_id] = {"status": "RUNNING"}

            # Fetch org info
            org = db.query(OrgModel).filter_by(id=org_id).first()
            if not org:
                raise ValueError("No organization found for this ID")

            users = (
                db.query(UserModel, OrgMemberModel)
                .join(OrgMemberModel, OrgMemberModel.user_id == UserModel.id)
                .filter(OrgMemberModel.org_id == org_id)
                .all()
            )

            if not users:
                raise ValueError("No users found for this organization")
            
            prompt = build_prompt_from_org_and_founders(org, users)
            

            analysis = {
                "seed_funding_probability": 62,
                "market": {
                    "tam_value": 12.5,
                    "growth_rate_percent": 18,
                    "growth_index": 72,
                    "insight": "The global market for AI-driven customer support automation is large and growing rapidly. Adoption is strongest in mid-sized enterprises that need to reduce support costs while improving response times. Growth is driven by rising demand for 24/7 support and improved customer experience."
                },
                "investor": "This idea has strong potential due to a clear problem and a large addressable market. The product can scale well with recurring revenue, but differentiation will be critical. Investors will want proof of product-market fit and early traction in a specific niche before committing.",
                "strengths": [
                    "Large and growing market with strong demand for automation.",
                    "Recurring revenue model (SaaS) with high scalability.",
                    "Clear pain point with measurable ROI for customers.",
                    "Strong potential for defensibility through data and AI models."
                ],
                "weaknesses": [
                    "Competitive space with many existing players and open-source tools.",
                    "Requires strong AI accuracy to avoid customer dissatisfaction.",
                    "High initial cost for training data and model fine-tuning.",
                    "Sales cycle may be long in enterprise segments."
                ],
                "personas": [
                    {
                        "name": "Support Manager",
                        "pain": "High support ticket volume, long response times, and lack of automation.",
                        "solution": "AI-assisted ticket triage and automated responses to common queries."
                    },
                    {
                        "name": "Head of Customer Experience",
                        "pain": "Low CSAT scores and inconsistent support quality across channels.",
                        "solution": "Unified AI agent providing consistent answers and tracking customer satisfaction."
                    },
                    {
                        "name": "Operations Director",
                        "pain": "Support costs are too high and hiring is slow.",
                        "solution": "Reduce support headcount by automating repetitive tasks and improving efficiency."
                    }
                ],
                "roadmap": {
                    "recommended_stage": "Early product-market fit (Prototype)",
                    "min_capital": 250000,
                    "max_capital": 750000,
                    "milestones": [
                        {
                            "label": "Build MVP with basic automation workflows",
                            "duration_days": 45,
                            "is_active": True
                        },
                        {
                            "label": "Run pilot with 3 mid-sized companies",
                            "duration_days": 60,
                            "is_active": True
                        },
                        {
                            "label": "Integrate with major support platforms (Zendesk, Freshdesk)",
                            "duration_days": 75,
                            "is_active": False
                        },
                        {
                            "label": "Launch public beta + pricing plan",
                            "duration_days": 30,
                            "is_active": False
                        }
                    ]
                },
                "founder_summary": "Founders: CEO - 8 years in product management; CTO - 6 years in ML engineering; COO - 5 years in operations. Strong execution capability, but limited experience in enterprise sales.",
                "notes": "This idea is strong if it targets a specific niche and builds defensibility through proprietary data and integrations."
            }
            # -------------------------
            # 🧠 Call the model here
            # -------------------------
            #analysis = query_model(
            #    prompt=prompt,
            #    model="gemini-3-pro-preview"
            #)

            # If your model returns a dict, use it directly
            # Otherwise parse JSON here

            # -------------------------
            # 🔥 Save to DB
            # -------------------------
            
            idea = db.query(AIIdeaAnalysis).filter_by(workspace_id=org_id).first()
            if not idea:
                idea = AIIdeaAnalysis(workspace_id=org_id)
                db.add(idea)
            

            idea.seed_funding_probability = analysis.get("seed_funding_probability", 0)
            idea.market = analysis.get("market", {})
            idea.investor = analysis.get("investor", "")
            idea.strengths = analysis.get("strengths", [])
            idea.weaknesses = analysis.get("weaknesses", [])
            idea.personas = analysis.get("personas", [])
            idea.roadmap = analysis.get("roadmap", {})
            idea.version = 1

            db.commit()
            # -------------------------
            # 🟢 Call upsert_job for dashboard instead of queue
            # -------------------------
            upsert_job(db, org_id, "dashboard")

            # Mark job as completed
            job_status[job_id]["status"] = "COMPLETED"
            job_status[job_id]["result"] = {
                "message": "Idea analysis created/updated",
                "org_id": org_id
            }

            # -------------------------
            # 🗑 Delete job from DB
            # -------------------------
            try:
                db.delete(job)
                db.commit()
            except Exception:
                db.rollback()  # Ignore deletion failure

        except Exception as e:
            db.rollback()
            if job:
                job_status[job_id]["status"] = "FAILED"
                job_status[job_id]["error"] = str(e)
            print("idea analysis Exception:", str(e))

        finally:
            db.close()


def investor_readiness_worker():
    """
    Worker function to process investor readiness analysis tasks.
    """
    while True:
        db = SessionLocal()
        job = None

        try:
            # ✅ Pick the oldest pending job of type 'investor_readiness'
            job = (
                db.query(Job)
                .filter(Job.type == "investor_readiness")
                .order_by(asc(Job.created_time))
                .first()
            )

            if not job:
                time.sleep(1)  # No job, wait a bit
                continue

            org_id = job.org_id
            job_id = job.id
            job_status[job_id] = {"status": "RUNNING"}

            # Update job status
            # Process the job
            print(f"Processing investor readiness analysis for job {job_id}")
            org = db.query(OrgModel).filter_by(id=org_id).first()
            if not org:
                raise ValueError("No organization found for this ID")

            financials = (
                db.query(FinancialsModel)
                .filter(FinancialsModel.org_id == org_id)
                .first()
            )

            if not financials:
                raise ValueError("No financials found for this organization")
            
            prompt = build_prompt_from_org_and_financials(org, financials)
            
            analysis = {
                "readiness_score": 0.48,
                "pushbacks": [
                    {
                        "title": "Why this team?",
                        "points": [
                            "CEO commitment is only 10 hrs/week",
                            "CTO owns 65% equity"
                        ]
                    },
                    {
                        "title": "Who owns execution?",
                        "points": [
                            "No clear ownership of product delivery"
                        ]
                    }
                ],
                "fixes": [
                    "Increase CEO time commitment",
                    "Clarify ownership responsibilities",
                    "Strengthen product roadmap"
                ],
                "demands": [
                    {
                        "label": "Equity Split",
                        "value": "20%",
                        "icon": "equity"
                    },
                    {
                        "label": "Board Control",
                        "value": "Quarterly Board Updates",
                        "icon": "control"
                    },
                    {
                        "label": "Milestone Metrics",
                        "value": "Achieve MVP in 6 months",
                        "icon": "milestones"
                    }
                ],
                "simulated_reaction": [
                    {"label": "Reject", "value": 0.7},
                    {"label": "Soft Interest", "value": 0.2},
                    {"label": "Fund", "value": 0.1}
                ],
                "investor_type": {
                    "primary": "VC",
                    "sectorFit": "Tech",
                    "stageFit": "Seed",
                    "mismatchFlags": ["Equity Disagreement", "Team Commitment"]
                },
                "recommendation": {
                    "verdict": "Conditional",
                    "reason": "Team alignment needs improvement before full funding"
                },
                "summary_insight": "The startup shows promise but needs better team alignment and clarity on execution ownership.",
                "investor_mindset_quotes": [
                    "I invest in people, not just ideas.",
                    "Market traction is more important than a perfect plan.",
                    "Equity and control always come first."
                ],
                "demand_warning": "High investor demands may delay fundraising.",
                "next_action": {"label": "Improve Team Alignment", "targetScreen": "TeamAlignmentScreen"}
            }


            # -------------------------
            # 🧠 Call the model here
            # -------------------------
            #analysis = query_model(
            #    prompt=prompt,
            #    model="gemini-3-pro-preview"
            #)

            # If your model returns a dict, use it directly
            # Otherwise parse JSON here

            # -------------------------
            # 🔥 Save to DB
            # -------------------------
            
            insights = db.query(InvestorReadiness).filter_by(id=org_id).first()
            if not insights:
                insights = InvestorReadiness(id=org_id)
                db.add(insights)

            # Populate fields from the JSON data
            insights.readiness_score = analysis.get("readiness_score", 0) * 100
            insights.pushbacks = analysis.get("pushbacks", [])
            insights.fixes = analysis.get("fixes", [])
            insights.demands = analysis.get("demands", [])
            insights.simulated_reaction = [
                {"label": item["label"], "value": item["value"] * 100} 
                for item in analysis.get("simulated_reaction", [])
            ]
            insights.investor_type = analysis.get("investor_type", {})
            insights.recommendation = analysis.get("recommendation", {})
            insights.summary_insight = analysis.get("summary_insight", "")
            insights.investor_mindset_quotes = analysis.get("investor_mindset_quotes", [])
            insights.demand_warning = analysis.get("demand_warning", "")
            insights.next_action = analysis.get("next_action", [])


            db.commit()

            # -------------------------
            # 🟢 Call upsert_job for dashboard instead of queue
            # -------------------------
            upsert_job(db, org_id, "dashboard")

            # Mark job as completed
            job_status[job_id]["status"] = "COMPLETED"
            job_status[job_id]["result"] = {
                "message": "Investor readiness analysis created/updated",
                "org_id": org_id
            }

            # -------------------------
            # 🗑 Delete job from DB
            # -------------------------
            try:
                db.delete(job)
                db.commit()
            except Exception:
                db.rollback()  # Ignore deletion failure


        except Exception as e:
            db.rollback()
            if job:
                job_status[job_id]["status"] = "FAILED"
                job_status[job_id]["error"] = str(e)
            print("investor readiness Exception:", str(e))

        finally:
            db.close()

def dashboard_worker():
    """
    Worker function to process dashboard data.
    """
    while True:
        db = SessionLocal()
        job = None

        try:
            # ✅ Pick the oldest pending job of type 'investor_readiness'
            job = (
                db.query(Job)
                .filter(Job.type == "dashboard")
                .order_by(asc(Job.created_time))
                .first()
            )

            if not job:
                time.sleep(1)  # No job, wait a bit
                continue

            org_id = job.org_id
            job_id = job.id
            job_status[job_id] = {"status": "RUNNING"}

            # Process the job
            org = db.query(OrgModel).filter_by(id=org_id).first()
            if not org:
                raise ValueError("No organization found for this ID")

            financials = (
                db.query(FinancialsModel)
                .filter(FinancialsModel.org_id == org_id)
                .first()
            )

            members = db.query(OrgMemberModel).filter_by(org_id=org_id).all()

            alignments = db.query(FounderAlignmentModel).filter_by(org_id=org_id).first()

           
            ideaAnalysis = db.query(AIIdeaAnalysis).filter_by(workspace_id=org_id).first()

            investorReadiness = db.query(InvestorReadiness).filter_by(id=org_id).first()


            prompt = build_dashboard_prompt(org, financials, members, alignments, ideaAnalysis, investorReadiness)
            
            dashboard_data = {
                "verdict": "High Potential, Early Risk",
                "thesis": "The startup has a strong founding team with a clear market opportunity, but burn rate is high relative to runway.",
                "killer_insight": "Founders are highly aligned on vision, but key technical hires are missing, creating execution risk.",
                "killer_insight_risk": "Execution Risk",
                "killer_insight_confidence": 0.8,
                "runway_months": 6,
                "burn_rate": 50000,
                "capital_recommendation": "Consider a bridge round to extend runway while key hires are made.",
                "top_actions": [
                {
                    "title": "Hire Lead Engineer",
                    "why": "Critical technical capability gap that could delay product launch",
                    "risk": "High",
                    "screenId": "team_screen"
                },
                {
                    "title": "Reduce Monthly Burn",
                    "why": "Current burn rate risks running out of cash before revenue ramps",
                    "risk": "Medium",
                    "screenId": "financials_screen"
                }
            ],
            "data_sources": [
                "FinancialsModel",
                "OrgMemberModel",
                "FounderAlignmentModel",
                "AIIdeaAnalysis",
                "InvestorReadiness"
            ],
            "model_version": "v1"
            }


            

            # -------------------------
            # 🧠 Call the model here
            # -------------------------
            #dashboard_data = query_model(
            #    prompt=prompt,
            #    model="gemini-3-pro-preview"
            #)

            # If your model returns a dict, use it directly
            # Otherwise parse JSON here

            # -------------------------
            # 🔥 Save to DB
            # -------------------------
            
            dashboard = db.query(DashboardModel).filter_by(id=org_id).first()
            if not dashboard:
                dashboard = DashboardModel(id=org_id)
                db.add(dashboard)

            dashboard.verdict = str(dashboard_data.get("verdict", ""))
            dashboard.thesis = str(dashboard_data.get("thesis", ""))
            dashboard.killer_insight = str(dashboard_data.get("killer_insight", ""))
            dashboard.killer_insight_risk = str(dashboard_data.get("killer_insight_risk", "")) if dashboard_data.get("killer_insight_risk") else None
            dashboard.killer_insight_confidence = float(dashboard_data.get("killer_insight_confidence", 0.0)) if dashboard_data.get("killer_insight_confidence") is not None else None
            dashboard.runway_months = int(dashboard_data.get("runway_months")) if dashboard_data.get("runway_months") is not None else None
            dashboard.burn_rate = float(dashboard_data.get("burn_rate")) if dashboard_data.get("burn_rate") is not None else None
            dashboard.capital_recommendation = str(dashboard_data.get("capital_recommendation", "")) if dashboard_data.get("capital_recommendation") else None
            dashboard.top_actions = dashboard_data.get("top_actions", [])
            dashboard.data_sources = dashboard_data.get("data_sources", [])
            dashboard.model_version = str(dashboard_data.get("model_version", "v1"))


            db.commit()
            
            # Mark job as completed
            job_status[job_id]["status"] = "COMPLETED"
            job_status[job_id]["result"] = {
                "message": "Dashboard analysis created/updated",
                "org_id": org_id
            }

            # -------------------------
            # 🗑 Delete job from DB
            # -------------------------
            try:
                db.delete(job)
                db.commit()
            except Exception:
                db.rollback()  # Ignore deletion failure

        except Exception as e:
            db.rollback()
            if job:
                job_status[job_id]["status"] = "FAILED"
                job_status[job_id]["error"] = str(e)
            print("Dashboard analysis Exception:", str(e))

        finally:
            db.close()



def build_prompt_from_org_and_financials(org, financials):
    """
    Build a structured prompt for AI idea analysis from organization data.
    """

    # --- Basic Org Info ---
    startup_type = getattr(org, "type", None) or "Not specified"
    problem_statement = getattr(org, "problem", None) or "Not specified"
    solution_statement = getattr(org, "solution", None) or "Not specified"
    
    # Optional fields
    name = getattr(org, "name", None) or "Not specified"
    industry = getattr(org, "industry", None) or "Not specified"
    geography = getattr(org, "geography", None) or "Not specified"
    stage = getattr(org, "stage", None) or "Not specified"
    customer = getattr(org, "customer", None) or "Not specified"

    # Default values if not present
    monthly_revenue = getattr(financials, "monthly_revenue", "Not specified")
    revenue_trend = getattr(financials, "revenue_trend", "Not specified")
    revenue_stage = getattr(financials, "revenue_stage", "Not specified")
    
    cash_in_bank = getattr(financials, "cash_in_bank", "Not specified")
    monthly_burn = getattr(financials, "monthly_burn", "Not specified")
    cost_structure = getattr(financials, "cost_structure", "Not specified")
    
    pricing_model = getattr(financials, "pricing_model", "Not specified")
    price_per_customer = getattr(financials, "price_per_customer", "Not specified")
    customers_in_pipeline = getattr(financials, "customers_in_pipeline", "Not specified")
    
    data_confidence = getattr(financials, "data_confidence", "Rough")

    # --- Prompt Template ---
    prompt = f"""
You are an expert startup analyst with experience in venture capital and early-stage investments.

Analyze the following startup information and produce a detailed investor insights report. Be opinionated, realistic, and precise.

Startup Details:
- Startup Name: {name}
- Industry: {industry}
- Geography: {geography}
- Stage: {stage}
- Customer: {customer}
- Startup Field: {startup_type}
- Problem Statement: {problem_statement}
- Solution by Startup: {solution_statement}

Financial Details:
- Monthly Revenue: {monthly_revenue}
- Revenue Trend: {revenue_trend}
- Revenue Stage: {revenue_stage}
- Cash in Bank: {cash_in_bank}
- Monthly Burn: {monthly_burn}
- Cost Structure: {cost_structure}
- Pricing Model: {pricing_model}
- Price per Customer: {price_per_customer}
- Customers in Pipeline: {customers_in_pipeline}
- Data Confidence: {data_confidence}

Output your analysis strictly as **JSON** matching this TypeScript interface:

interface InvestorReadinessData {{
    readiness_score: number;

    pushbacks: {{
        title: string;
        points: string[];
    }}[];

    fixes: string[];

    demands: {{
        label: string;
        value: string;
        icon: "equity" | "control" | "milestones" | "governance";
    }}[];

    simulated_reaction: {{
        label: "Reject" | "Soft Interest" | "Fund";
        value: number;
    }}[];

    investor_type: {{
        primary: string;
        sectorFit: string;
        stageFit: string;
        mismatchFlags: string[];
    }};

    recommendation: {{
        verdict: "Delay Fundraising" | "Proceed" | "Conditional";
        reason: string;
    }};

    summary_insight: string;

    investor_mindset_quotes: string[];

    demand_warning: string;

    next_action: {{
        label: string;
        targetScreen: ScreenId;
    }};
}}

Guidelines:
- Provide realistic investor-style feedback with reasoning.
- readiness_score should be 0.0–1.0.
- Include 2–3 pushbacks with 2–4 points each.
- Provide 3–5 actionable fixes.
- Include 2–4 demands, using the allowed icon values.
- Provide 3 simulated investor reactions with realistic probabilities.
- investor_type should include sectorFit, stageFit, and mismatchFlags.
- recommendation should be clear and justified.
- Provide a concise one-paragraph summary_insight.
- Include 3–5 short investorMindsetQuotes.
- Add a one-line demandWarning highlighting potential risks.
- Provide nextAction with a label and targetScreen.

Make sure the JSON is **fully valid** and ready to use in TypeScript.
"""

    return prompt

def build_organization_json(org: OrgModel):
    return {
        "industry": org.industry,
        "geography": org.geography,
        "stage": org.stage,
        "problem": org.problem,
        "solution": org.solution,
        "customer": org.customer,
        "risk_level": org.risk_level
    }

def build_org_members_json(members: list[OrgMemberModel]):
    if not members:
        return []
    return [
        {
            "role": m.role,
            "hours_per_week": m.hours_per_week,
            "equity": m.equity,
            "authority": m.authority,
            "risk_tolerance": m.risk_tolerance
        }
        for m in members
    ]


def build_founder_alignment_json(fa: FounderAlignmentModel):
    if not fa:
        return {
            "score": 0,
            "risk_level": "None",
            "primary_risk": "None",
            "key_risks": [],
            "recommended_actions": []
        }
    return {
        "score": fa.score,
        "risk_level": fa.risk_level,
        "primary_risk": fa.primary_risk,
        "key_risks": fa.risks,
        "recommended_actions": fa.actions
    }

def build_financials_json(fin: FinancialsModel):
    if not fin:
        return {
            "monthly_revenue": 0,
            "revenue_trend": "None",
            "cash_in_bank": 0,
            "monthly_burn": 0,
            "runway_months": 0,
            "data_confidence": "None"
        }
    return {
        "monthly_revenue": fin.monthly_revenue,
        "revenue_trend": fin.revenue_trend,
        "cash_in_bank": fin.cash_in_bank,
        "monthly_burn": fin.monthly_burn,
        "runway_months": (
            fin.cash_in_bank // fin.monthly_burn
            if fin.cash_in_bank and fin.monthly_burn else None
        ),
        "data_confidence": fin.data_confidence
    }

def build_ai_idea_analysis_json(ai: AIIdeaAnalysis):
    if not ai:
        return {
            "seed_funding_probability": 0,
            "market_summary": "None",
            "key_strengths": [],
            "key_weaknesses": []
        }
    return {
        "seed_funding_probability": ai.seed_funding_probability,
        "market_summary": ai.market.get("summary") if ai.market else None,
        "key_strengths": ai.strengths,
        "key_weaknesses": ai.weaknesses
    }

def build_investor_readiness_json(ir: InvestorReadiness):
    if not ir:
        return {
            "readiness_score": 0,
            "summary_insight": "None",
            "top_pushbacks": [],
            "next_action": {
                "label": "None",
                "targetScreen": "None"
            }
        }
    return {
        "readiness_score": ir.readiness_score,
        "summary_insight": ir.summary_insight,
        "top_pushbacks": ir.pushbacks[:2] if ir.pushbacks else [],
        "next_action": ir.next_action
    }


def build_dashboard_prompt(org, financials, founders, alignments, ideaAnalysis, investorReadiness):
    """
    dashboard: DashboardModel
    returns: string prompt
    """
    organization_json = build_organization_json(org)
    org_members_json = build_org_members_json(founders)
    founder_alignment_json = build_founder_alignment_json(alignments)
    financials_json = build_financials_json(financials)
    ai_idea_analysis_json = build_ai_idea_analysis_json(ideaAnalysis)
    investor_readiness_json = build_investor_readiness_json(investorReadiness)
    
    prompt = f"""
You are a senior startup investor and operating partner.

Your job is to synthesize multiple analyses into a single executive dashboard.
Be decisive, opinionated, and concise. Avoid generic advice.

INPUT DATA:

Organization:
{organization_json}

Founders & Team:
{org_members_json}

Founder Alignment Analysis:
{founder_alignment_json}

Financials:
{financials_json}

AI Market & Idea Analysis:
{ai_idea_analysis_json}

Investor Readiness Analysis:
{investor_readiness_json}

---

TASK:
Generate a SINGLE executive dashboard object using the schema below.

RULES:
- Verdict must be ONE sharp phrase
- Thesis must be 1–2 sentences max
- Killer Insight must reveal a non-obvious risk or leverage point
- Confidence should reflect data consistency (0.0–1.0)
- Actions must reference the relevant screenId
- Do NOT repeat raw data
- Think like an investor deciding whether to take the meeting
- If any output field data is missing, return null or empty list for that field

OUTPUT FORMAT (JSON ONLY):

{{
  "verdict": "",
  "thesis": "",
  "killer_insight": "",
  "killer_insight_risk": "",
  "killer_insight_confidence": 0.0,
  "runway_months": null,
  "burn_rate": null,
  "capital_recommendation": "",
  "top_actions": [
    {{
      "title": "",
      "why": "",
      "risk": "",
      "screenId": ""
    }}
  ],
  "data_sources": [],
  "model_version": "v1"
}}
"""
    print(f"Processing  data for job ")
    return prompt

def start_workers():
    
    threading.Thread(target=founder_alignment_worker, daemon=True).start()
    threading.Thread(target=idea_analysis_worker, daemon=True).start()
    threading.Thread(target=investor_readiness_worker, daemon=True).start()
    threading.Thread(target=dashboard_worker, daemon=True).start()
