import threading
from queue import Queue
import time
from models import User as UserModel, FounderAlignmentModel, OrganizationModel, AIIdeaAnalysis, OrgMember as OrgMemberModel
from pydantic_types import UserSchema, Workspace, UserOrgInfo, LoginRequest, CreateUserRequest, SetUserOrgInfoRequest, SetOnboardingRequest, MarketSchema, PersonaSchema, MilestoneSchema, RoadmapSchema, AnalysisPayload, FounderAlignmentResponse, FounderAlignmentResponseModel

founder_alignment_queue = Queue()
job_status = {}

def founder_alignment_worker():
    while True:
        job = founder_alignment_queue.get()
        job_id = job["job_id"]
        org_id = job["org_id"]
        job_status[job_id]["status"] = "RUNNING"

        db = SessionLocal()
        try:
            # 1) Fetch users
            users = (
                db.query(UserModel, OrgMemberModel)
                .join(OrgMemberModel, OrgMemberModel.user_id == UserModel.id)
                .filter(OrgMemberModel.org_id == org_id)
                .all()
            )

            if not users:
                raise ValueError("No users found for this organization")

            # 2) UPSERT alignment row
            alignment = db.query(FounderAlignmentModel).filter_by(org_id=org_id).first()

            if alignment:
                # Update existing row
                alignment.score = 0
                alignment.risk_level = "Low"
                alignment.factors = {}
                alignment.risks = []
                alignment.actions = []
                alignment.primary_risk = None
                alignment.insight = None
                alignment.model_version = "v1"
            else:
                # Create new row
                alignment = FounderAlignmentModel(
                    org_id=org_id,
                    score=0,
                    risk_level="Low",
                    factors={},
                    risks=[],
                    actions=[],
                    primary_risk=None,
                    insight=None,
                    model_version="v1"
                )
                db.add(alignment)

            db.commit()

            job_status[job_id]["status"] = "COMPLETED"
            job_status[job_id]["result"] = {
                "message": "Alignment created/updated",
                "alignment_id": alignment.id
            }

        except Exception as e:
            db.rollback()
            job_status[job_id]["status"] = "FAILED"
            job_status[job_id]["error"] = str(e)

        finally:
            db.close()
            founder_alignment_queue.task_done()
def start_workers():
    worker_thread = threading.Thread(target=founder_alignment_worker, daemon=True)
    worker_thread.start()
