import asyncio
import logging
from typing import Dict, Any, List
from supabase import Client
import json
import random
from datetime import datetime
from app.routers.approvals import create_approval_request, ApprovalRequestCreate
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

class DepartmentRunner:
    """
    Orchestrates the autonomous execution of Departments.
    """
    
    def __init__(self):
        self.supabase = get_service_client()

    async def tick(self):
        """
        Runs one cycle for all RUNNING departments.
        This would typically be called by a Cron job every minute.
        """
        try:
            # 1. Fetch active departments
            res = self.supabase.table("departments").select("*").eq("status", "RUNNING").execute()
            departments = res.data
            
            logger.info(f"Department Runner ticking... found {len(departments)} active departments")
            
            results = []
            for dept in departments:
                result = await self.run_department_cycle(dept)
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Department Runner failed: {e}")
            raise e

    async def run_department_cycle(self, dept: Dict[str, Any]):
        """
        Executes logic for a specific department type.
        """
        dept_id = dept['id']
        dept_type = dept['type']
        state = dept['state']
        
        logger.info(f"Running cycle for {dept['name']} ({dept_type})")
        
        new_state = state.copy()
        activity_log = ""
        
        if dept_type == 'SALES':
            # === SIMULATED SALES AGENT LOGIC ===
            # Real implementation would call the actual SalesAgent class here.
            
            leads_processed = state.get('leads_processed', 0)
            revenue = state.get('revenue', 0)
            
            # Simulation: 10% chance to find a lead
            if random.random() < 0.3: 
                lead_name = f"Lead-{random.randint(1000, 9999)}"
                logger.info(f"Sales Dept found new lead: {lead_name}")
                
                # Create Approval Request to contact lead
                description = f"Send introduction email to {lead_name}"
                req = ApprovalRequestCreate(
                    action_type="SEND_EMAIL", 
                    payload={
                        "to": f"{lead_name.lower()}@example.com", 
                        "subject": "Partnership Opportunity",
                        "body": "Hello, we'd like to partner..."
                    }
                )
                await create_approval_request(req)
                
                activity_log = f"Found lead {lead_name}. Requested approval for outreach."
                leads_processed += 1
            else:
                activity_log = "Scanning for prospects... No new leads found this cycle."
                
            new_state['leads_processed'] = leads_processed
            new_state['revenue'] = revenue
            new_state['last_activity'] = activity_log
            
        elif dept_type == 'HR':
             # Placeholder for HR
             activity_log = "HR Monitoring employee satisfaction..."
             
        # Update State & Heartbeat
        self.supabase.table("departments").update({
            "state": new_state,
            "last_heartbeat": datetime.utcnow().isoformat()
        }).eq("id", dept_id).execute()
        
        return {
            "dept_id": dept_id,
            "activity": activity_log
        }

# Global instance
runner = DepartmentRunner()
