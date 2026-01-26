import threading
from queue import Queue
import time
from models import User as UserModel, AIIdeaAnalysis, FounderAlignmentModel, OrganizationModel as OrgModel, OrgMember as OrgMemberModel
from pydantic_types import UserSchema, Workspace, UserOrgInfo, LoginRequest, CreateUserRequest, SetUserOrgInfoRequest, SetOnboardingRequest, MarketSchema, PersonaSchema, MilestoneSchema, RoadmapSchema, AnalysisPayload, FounderAlignmentResponse, FounderAlignmentResponseModel
import json
import os
from google import genai
from google.genai import types
from database import SessionLocal


founder_alignment_queue = Queue()
idea_analysis_queue = Queue()
job_status = {}

def build_prompt_from_org(org, founders):
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
  "investor_verdict": string,         # short paragraph
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
            f"  Last Updated: {org_member.last_updated}\n"
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
        job = founder_alignment_queue.get()
        

        org_id = job["org_id"]
        job_id = org_id  # 1 job per org

        # ✅ initialize job status safely
        job_status[job_id] = {
            "status": "RUNNING"
        }

        db = SessionLocal()

        try:

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

            # analysis = query_model(
            #     prompt=prompt,
            #     model="gemini-3-flash-preview"
            # )

            

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

            job_status[job_id]["status"] = "COMPLETED"
            job_status[job_id]["result"] = {
                "message": "Alignment created/updated",
                "alignment_id": alignment.id
            }

        except Exception as e:
            print("Exception: ", str(e))
            db.rollback()
            job_status[job_id]["status"] = "FAILED"
            job_status[job_id]["error"] = str(e)

        finally:
            db.close()
            founder_alignment_queue.task_done()

def idea_analysis_worker():
    while True:
        job = idea_analysis_queue.get()

        org_id = job["org_id"]
        job_id = org_id  # 1 job per org

        job_status[job_id] = {
            "status": "RUNNING"
        }

        db = SessionLocal()

        try:
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
            
            prompt = build_prompt_from_org(org, users)
            

            analysis = {
                "seed_funding_probability": 62,
                "market": {
                    "tam_value": 12.5,
                    "growth_rate_percent": 18,
                    "growth_index": 72,
                    "insight": "The global market for AI-driven customer support automation is large and growing rapidly. Adoption is strongest in mid-sized enterprises that need to reduce support costs while improving response times. Growth is driven by rising demand for 24/7 support and improved customer experience."
                },
                "investor_verdict": "This idea has strong potential due to a clear problem and a large addressable market. The product can scale well with recurring revenue, but differentiation will be critical. Investors will want proof of product-market fit and early traction in a specific niche before committing.",
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
            idea.investor = analysis.get("investor_verdict", "")
            idea.strengths = analysis.get("strengths", [])
            idea.weaknesses = analysis.get("weaknesses", [])
            idea.personas = analysis.get("personas", [])
            idea.roadmap = analysis.get("roadmap", {})
            idea.version = 1

            db.commit()

            job_status[job_id]["status"] = "COMPLETED"
            job_status[job_id]["result"] = {
                "message": "Idea analysis created/updated",
                "org_id": org_id
            }

        except Exception as e:
            print("idea analysis Exception: ", str(e))
            db.rollback()
            job_status[job_id]["status"] = "FAILED"
            job_status[job_id]["error"] = str(e)

        finally:
            db.close()
            idea_analysis_queue.task_done()


def start_workers():
    
    threading.Thread(target=founder_alignment_worker, daemon=True).start()
    threading.Thread(target=idea_analysis_worker, daemon=True).start()
