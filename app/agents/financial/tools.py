# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for the Financial Analysis Agent."""


async def get_revenue_stats(period: str = "current_month") -> dict:
    """Get revenue statistics for financial analysis from FinancialService.
    
    Args:
        period: Time period for revenue stats (default: current_month).
    
    Returns:
        Dictionary containing revenue amount, currency, period, and status.
    """
    from app.services.financial_service import FinancialService
    
    try:
        service = FinancialService()
        stats = await service.get_revenue_stats(period)
        return stats
    except Exception as e:
        # Fallback to informative error response
        return {
            "revenue": 0.0,
            "currency": "USD",
            "period": period,
            "error": f"Service unavailable: {str(e)}"
        }
