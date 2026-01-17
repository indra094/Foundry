from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import time
import json

def seed():
    # Ensure tables are created
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Define users
    users_to_seed = [
        {
            "id": "u_indra",
            "full_name": "Indra",
            "email": "indra094@gmail.com",
            "avatar_url": None
        },
        {
            "id": "u_inandy",
            "full_name": "Inandy",
            "email": "inandy@umass.edu",
            "avatar_url": None
        }
    ]

    for u_data in users_to_seed:
        # Check if user exists
        user = db.query(models.User).filter(models.User.email == u_data["email"]).first()
        if not user:
            user = models.User(**u_data)
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created user: {u_data['email']}")
        else:
            user.full_name = u_data["full_name"]
            user.avatar_url = u_data["avatar_url"]
            db.commit()
            print(f"Updated user: {u_data['email']}")

        # Create/Update Organization for this user
        org_slug = f"foundry-{user.id}"
        org = db.query(models.OrganizationModel).filter(models.OrganizationModel.slug == org_slug).first()
        
        # User-specific org settings
        is_indra = user.email == "indra094@gmail.com"
        org_name = "Foundry" if is_indra else "Nexus"
        industry = "Deep Tech" if is_indra else "FinTech"
        org_type = "B2B SaaS" if is_indra else "Consumer Finance"

        if not org:
            org = models.OrganizationModel(
                id=f"org_{user.id}",
                name=org_name,
                slug=org_slug,
                onboarding_step=6,
                stage="Pre-Seed",
                risk_level="Medium",
                burn_rate=15000.0 if is_indra else 8000.0,
                runway="12 months" if is_indra else "18 months",
                industry=industry,
                type=org_type
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"Created organization for {user.id}")
        else:
            org.name = org_name
            org.onboarding_step = 6
            org.risk_level = "Medium"
            org.burn_rate = 15000.0 if is_indra else 8000.0
            org.runway = "12 months" if is_indra else "18 months"
            org.industry = industry
            org.type = org_type
            db.commit()
        
        # Create/Update OrgMember (Founder)
        member = db.query(models.OrgMember).filter(
            models.OrgMember.user_id == user.id,
            models.OrgMember.org_id == org.id
        ).first()
        
        if not member:
            member = models.OrgMember(
                id=f"mem_{user.id}",
                user_id=user.id,
                org_id=org.id,
                member_type="Founder",
                role="CEO" if is_indra else "CTO",
                responsibility="Product & Strategy" if is_indra else "Engineering & Architecture",
                authority=json.dumps(['product', 'hiring', 'budget', 'strategy'] if is_indra else ['eng', 'security', 'infra']),
                hours_per_week=50,
                start_date="2026-01-01",
                planned_change="Maintain role as founder",
                salary=0.0,
                equity=50.0 if is_indra else 45.0,
                expectations=json.dumps(['Ship MVP by Q1', 'Secure 5 design partners'] if is_indra else ['Scalable backend', 'Security audit']),
                status="Active",
                cash_contribution=5000.0 if is_indra else 2000.0,
                risk_tolerance="High",
                vesting_cliff=12
            )
            db.add(member)
            db.commit()
            print(f"Added {user.id} to organization {org.name}")

        # Seed Investors (Clear existing to refresh unique set)
        db.query(models.Investor).filter(models.Investor.org_id == org.id).delete()
        if is_indra:
            db.add_all([
                models.Investor(id=f"inv_1_{user.id}", org_id=org.id, name="Sequoia Capital", type="VC", stage="Series A", status="Warm", notes="Highly interested in deep tech SaaS."),
                models.Investor(id=f"inv_2_{user.id}", org_id=org.id, name="Andreessen Horowitz", type="VC", stage="Seed", status="Target", notes="Tracking progress on MVP."),
                models.Investor(id=f"inv_3_{user.id}", org_id=org.id, name="Naval Ravikant", type="Angel", stage="Seed", status="Contacted", notes="Follow up after first 5 customers."),
            ])
        else:
            db.add_all([
                models.Investor(id=f"inv_1_{user.id}", org_id=org.id, name="Visa Ventures", type="CVC", stage="Seed", status="Target", notes="Strategic fit for FinTech."),
                models.Investor(id=f"inv_2_{user.id}", org_id=org.id, name="Y Combinator", type="Accelerator", stage="Pre-Seed", status="Applied", notes="Interview scheduled."),
            ])
        print(f"Added investors for {org.name}")

        # Seed Customers (Clear existing)
        db.query(models.Customer).filter(models.Customer.org_id == org.id).delete()
        if is_indra:
            db.add_all([
                models.Customer(id=f"cust_1_{user.id}", org_id=org.id, company="Google", role="Product Manager", status="Discovery", signal=4, notes="Validated problem-solution fit."),
                models.Customer(id=f"cust_2_{user.id}", org_id=org.id, company="Amazon", role="Engineering Lead", status="Pilot", signal=5, notes="Requested 30-day trial of core API."),
            ])
        else:
            db.add_all([
                models.Customer(id=f"cust_1_{user.id}", org_id=org.id, company="Stripe", role="Partnerships", status="Discovery", signal=4, notes="API documentation review."),
                models.Customer(id=f"cust_2_{user.id}", org_id=org.id, company="Revolut", role="Head of Product", status="Warm", signal=3, notes="Interested in regulatory module."),
            ])
        print(f"Added customers for {org.name}")

        # Seed Notifications (Clear existing)
        db.query(models.Notification).filter(models.Notification.org_id == org.id).delete()
        db.add_all([
            models.Notification(org_id=org.id, title="Alignment Score Dropped", type="Warning"),
            models.Notification(org_id=org.id, title="Founder Agreement Signed", type="Success"),
            models.Notification(org_id=org.id, title="Investor Signal: High", type="Info"),
        ])
        print(f"Added notifications for {org.name}")

        # Seed Readiness Gates (Clear existing)
        db.query(models.ReadinessGate).filter(models.ReadinessGate.org_id == org.id).delete()
        if is_indra:
            db.add(models.ReadinessGate(gate_id="incorporation", org_id=org.id, score=63, issues=json.dumps(["No signed agreement", "Zero customer validation", "Equity vesting not finalized"])))
            db.add(models.ReadinessGate(gate_id="funding", org_id=org.id, score=25, issues=json.dumps(["Need 10+ customers", "Equity split finalized", "Pitch deck draft missing"])))
        else:
            db.add(models.ReadinessGate(gate_id="incorporation", org_id=org.id, score=85, issues=json.dumps(["Finalize bylaws", "Open bank account"])))
            db.add(models.ReadinessGate(gate_id="funding", org_id=org.id, score=45, issues=json.dumps(["Increase burn rate accuracy", "Draft Investor Rights Agreement"])))
        print(f"Added readiness gates for {org.name}")

        # Seed Connections (Clear existing)
        db.query(models.Connection).filter(models.Connection.org_id == org.id).delete()
        if is_indra:
            db.add_all([
                models.Connection(org_id=org.id, name="John VC", role="Investor", company="Sequoia", relevance="High"),
                models.Connection(org_id=org.id, name="Sarah Angel", role="Angel", company="AngelList", relevance="High"),
            ])
        else:
            db.add_all([
                models.Connection(org_id=org.id, name="FinTech Mentor", role="Mentor", company="Plaid", relevance="High"),
            ])
        print(f"Added connections for {org.name}")

        # Seed Employees & AI History
        db.query(models.Employee).filter(models.Employee.org_id == org.id).delete()
        
        emp_name = "Sarah Chen" if is_indra else "Mike Ross"
        emp1 = models.Employee(id=f"emp_1_{user.id}", org_id=org.id, name=emp_name, type="Human", role="Lead Engineer" if is_indra else "Head of Compliance", status="Full-time")
        db.add(emp1)
        
        emp2 = models.Employee(id=f"emp_2_{user.id}", org_id=org.id, name="Foundry-Architect", type="AI", role="System Design", status="Active")
        db.add(emp2)
        
        db.commit()
        db.refresh(emp2)

        db.query(models.AIHistory).filter(models.AIHistory.employee_id == emp2.id).delete()
        if is_indra:
            db.add_all([
                models.AIHistory(employee_id=emp2.id, activity="Drafted lead generation script", timestamp="2h ago"),
                models.AIHistory(employee_id=emp2.id, activity="Analyzed 12 interview transcripts", timestamp="4h ago"),
                models.AIHistory(employee_id=emp2.id, activity="Updated system architecture diagram", timestamp="6h ago"),
                models.AIHistory(employee_id=emp2.id, activity="Generated 50 target leads list", timestamp="8h ago"),
            ])
        else:
            db.add_all([
                models.AIHistory(employee_id=emp2.id, activity="Reviewed compliance framework", timestamp="1h ago"),
                models.AIHistory(employee_id=emp2.id, activity="Automated KYC verification workflow", timestamp="3h ago"),
            ])
        print(f"Added AI history for {emp2.name}")

    db.commit()
    db.close()
    print("Seeding complete.")

if __name__ == "__main__":
    seed()
