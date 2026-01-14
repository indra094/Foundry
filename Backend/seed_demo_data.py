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
            "avatar_url": "https://images.unsplash.com/photo-1519345182560-3f2917c472ef?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80"
        },
        {
            "id": "u_inandy",
            "full_name": "Inandy",
            "email": "inandy@umass.edu",
            "avatar_url": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80"
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
        org_slug = f"auto-{user.id}"
        org = db.query(models.Organization).filter(models.Organization.slug == org_slug).first()
        if not org:
            org = models.Organization(
                id=f"org_{user.id}",
                name="Foundry",
                slug=f"foundry-{user.id}",
                onboarding_step=6,
                stage="Pre-Seed",
                risk_level="Medium",
                burn_rate=15000.0,
                runway="12 months"
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"Created organization for {user.id}")
        else:
            org.onboarding_step = 6
            org.risk_level = "Medium"
            org.burn_rate = 15000.0
            org.runway = "12 months"
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
                role="CEO" if u_data["full_name"] == "Indra" else "CTO",
                responsibility="Product & Strategy" if u_data["full_name"] == "Indra" else "Engineering & Architecture",
                authority=json.dumps(['product', 'hiring']),
                hours_per_week=40,
                start_date="2026-01-01",
                planned_change="none",
                salary=0.0,
                equity=50.0 if u_data["full_name"] == "Indra" else 40.0,
                expectations=json.dumps(['Ship MVP', 'Validate pricing']),
                status="Active"
            )
            db.add(member)
            db.commit()
            print(f"Added {user.id} to organization {org.name}")

        # Seed Investors
        if not db.query(models.Investor).filter(models.Investor.org_id == org.id).first():
            db.add_all([
                models.Investor(id=f"inv_1_{user.id}", org_id=org.id, name="Sequoia Capital", type="VC", stage="Series A", status="Warm"),
                models.Investor(id=f"inv_2_{user.id}", org_id=org.id, name="Andreessen Horowitz", type="VC", stage="Seed", status="Target"),
            ])
            print(f"Added investors for {org.name}")

        # Seed Customers
        if not db.query(models.Customer).filter(models.Customer.org_id == org.id).first():
            db.add_all([
                models.Customer(id=f"cust_1_{user.id}", org_id=org.id, company="Google", role="Product Manager", status="Discovery", signal=4),
                models.Customer(id=f"cust_2_{user.id}", org_id=org.id, company="Amazon", role="Engineering Lead", status="Pilot", signal=5),
            ])
            print(f"Added customers for {org.name}")

        # Seed Notifications
        if not db.query(models.Notification).filter(models.Notification.org_id == org.id).first():
            db.add_all([
                models.Notification(org_id=org.id, title="Alignment Score Dropped", type="Warning"),
                models.Notification(org_id=org.id, title="Founder Agreement Signed", type="Success"),
            ])
            print(f"Added notifications for {org.name}")

        # Seed Readiness Gates
        if not db.query(models.ReadinessGate).filter(models.ReadinessGate.gate_id == "incorporation", models.ReadinessGate.org_id == org.id).first():
            db.add(models.ReadinessGate(gate_id="incorporation", org_id=org.id, score=63, issues=json.dumps(["No signed agreement", "Zero customer validation"])))
        if not db.query(models.ReadinessGate).filter(models.ReadinessGate.gate_id == "funding", models.ReadinessGate.org_id == org.id).first():
            db.add(models.ReadinessGate(gate_id="funding", org_id=org.id, score=25, issues=json.dumps(["Need 10+ customers", "Equity split finalized"])))
        print(f"Added readiness gates for {org.name}")

        # Seed Connections
        if not db.query(models.Connection).filter(models.Connection.org_id == org.id).first():
            db.add_all([
                models.Connection(org_id=org.id, name="John VC", role="Investor", company="Sequoia", relevance="High"),
                models.Connection(org_id=org.id, name="Sarah Angel", role="Angel", company="AngelList", relevance="High"),
            ])
            print(f"Added connections for {org.name}")

        # Seed Employees & AI History
        emp1 = db.query(models.Employee).filter(models.Employee.org_id == org.id, models.Employee.name == "Sarah Chen").first()
        if not emp1:
            emp1 = models.Employee(id=f"emp_1_{user.id}", org_id=org.id, name="Sarah Chen", type="Human", role="Lead Engineer", status="Full-time")
            db.add(emp1)
        
        emp2 = db.query(models.Employee).filter(models.Employee.org_id == org.id, models.Employee.name == "Foundry-Architect").first()
        if not emp2:
            emp2 = models.Employee(id=f"emp_2_{user.id}", org_id=org.id, name="Foundry-Architect", type="AI", role="System Design", status="Active")
            db.add(emp2)
        
        db.commit()
        db.refresh(emp2)

        if not db.query(models.AIHistory).filter(models.AIHistory.employee_id == emp2.id).first():
            db.add_all([
                models.AIHistory(employee_id=emp2.id, activity="Drafted lead generation script", timestamp="2h ago"),
                models.AIHistory(employee_id=emp2.id, activity="Analyzed 12 interview transcripts", timestamp="4h ago"),
                models.AIHistory(employee_id=emp2.id, activity="Updated system architecture diagram", timestamp="6h ago"),
            ])
            print(f"Added AI history for {emp2.name}")

    db.commit()
    db.close()
    print("Seeding complete.")

if __name__ == "__main__":
    seed()
