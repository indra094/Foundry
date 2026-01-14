from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import time

def seed():
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
            "id": "u_indra_alt",
            "full_name": "Indra Alt",
            "email": "indra@094@gmail.com",
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
            # Update user data
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
                name="Auto",
                slug=org_slug
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"Created organization for {user.id}")
        
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
                hours_per_week=40,
                equity=50.0,
                status="Active"
            )
            db.add(member)
            db.commit()
            print(f"Added {user.id} to organization {org.name}")

        # Seed some data for this org
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

        # Seed Employees
        if not db.query(models.Employee).filter(models.Employee.org_id == org.id).first():
            db.add_all([
                models.Employee(id=f"emp_1_{user.id}", org_id=org.id, name="Sarah Chen", type="Human", role="Lead Engineer", status="Full-time"),
                models.Employee(id=f"emp_2_{user.id}", org_id=org.id, name="Auto-Architect", type="AI", role="System Design", status="Active"),
            ])
            print(f"Added employees for {org.name}")

    db.commit()
    db.close()
    print("Seeding complete.")

if __name__ == "__main__":
    seed()
