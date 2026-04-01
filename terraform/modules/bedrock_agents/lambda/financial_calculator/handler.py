"""
=============================================================================
FINSIGHT AI - FINANCIAL CALCULATOR LAMBDA
=============================================================================
This Lambda function serves as an Action Group tool for Bedrock Agents.
It performs financial calculations that the Agent can invoke.

SUPPORTED OPERATIONS:
  - calculate_growth_rate: YoY growth between two values
  - calculate_ratio: Divide two numbers (P/E, D/E, etc.)
  - calculate_margin: Profit margin percentage
  - calculate_cagr: Compound Annual Growth Rate
  - compare_values: Compare two or more values

BEDROCK AGENT INTEGRATION:
  The Agent sends requests in a specific format, and we must return
  responses in the expected format for the Agent to understand.

Author: Mahendra Nali
=============================================================================
"""

import json
import logging
from typing import Dict, Any, List
from decimal import Decimal, ROUND_HALF_UP

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# =============================================================================
# FINANCIAL CALCULATION FUNCTIONS
# =============================================================================

def calculate_growth_rate(old_value: float, new_value: float) -> Dict[str, Any]:
    """
    Calculate year-over-year or period-over-period growth rate.
    
    Formula: ((new - old) / old) * 100
    
    Example:
        old_value = 383.29 (2023 revenue)
        new_value = 391.04 (2024 revenue)
        result = 2.02%
    """
    if old_value == 0:
        return {
            "success": False,
            "error": "Cannot calculate growth rate when old value is zero"
        }
    
    growth_rate = ((new_value - old_value) / abs(old_value)) * 100
    
    return {
        "success": True,
        "operation": "growth_rate",
        "old_value": old_value,
        "new_value": new_value,
        "growth_rate_percent": round(growth_rate, 2),
        "interpretation": f"{'Increased' if growth_rate > 0 else 'Decreased'} by {abs(round(growth_rate, 2))}%"
    }


def calculate_ratio(numerator: float, denominator: float, ratio_name: str = "ratio") -> Dict[str, Any]:
    """
    Calculate a financial ratio (P/E, D/E, Current Ratio, etc.)
    
    Example:
        numerator = 150 (stock price)
        denominator = 6.5 (EPS)
        ratio_name = "P/E Ratio"
        result = 23.08
    """
    if denominator == 0:
        return {
            "success": False,
            "error": f"Cannot calculate {ratio_name}: denominator is zero"
        }
    
    ratio = numerator / denominator
    
    return {
        "success": True,
        "operation": "ratio",
        "ratio_name": ratio_name,
        "numerator": numerator,
        "denominator": denominator,
        "ratio_value": round(ratio, 2)
    }


def calculate_margin(revenue: float, profit: float, margin_type: str = "profit") -> Dict[str, Any]:
    """
    Calculate profit margin percentage.
    
    Formula: (profit / revenue) * 100
    
    Example:
        revenue = 391.04 billion
        profit = 97.0 billion
        result = 24.81% profit margin
    """
    if revenue == 0:
        return {
            "success": False,
            "error": "Cannot calculate margin: revenue is zero"
        }
    
    margin = (profit / revenue) * 100
    
    return {
        "success": True,
        "operation": "margin",
        "margin_type": margin_type,
        "revenue": revenue,
        "profit": profit,
        "margin_percent": round(margin, 2),
        "interpretation": f"{margin_type.title()} margin is {round(margin, 2)}%"
    }


def calculate_cagr(start_value: float, end_value: float, years: int) -> Dict[str, Any]:
    """
    Calculate Compound Annual Growth Rate.
    
    Formula: ((end_value / start_value) ^ (1/years) - 1) * 100
    
    Example:
        start_value = 260.17 (2019 revenue)
        end_value = 391.04 (2024 revenue)
        years = 5
        result = 8.5% CAGR
    """
    if start_value <= 0 or end_value <= 0:
        return {
            "success": False,
            "error": "Values must be positive for CAGR calculation"
        }
    
    if years <= 0:
        return {
            "success": False,
            "error": "Years must be positive for CAGR calculation"
        }
    
    cagr = (pow(end_value / start_value, 1 / years) - 1) * 100
    
    return {
        "success": True,
        "operation": "cagr",
        "start_value": start_value,
        "end_value": end_value,
        "years": years,
        "cagr_percent": round(cagr, 2),
        "interpretation": f"Compound Annual Growth Rate over {years} years is {round(cagr, 2)}%"
    }


def compare_values(values: List[Dict[str, float]], metric_name: str = "value") -> Dict[str, Any]:
    """
    Compare multiple values and rank them.
    
    Example:
        values = [
            {"name": "Apple", "value": 391.04},
            {"name": "Microsoft", "value": 211.91},
            {"name": "Google", "value": 307.39}
        ]
        result = Ranked list with differences
    """
    if not values or len(values) < 2:
        return {
            "success": False,
            "error": "Need at least 2 values to compare"
        }
    
    # Sort by value descending
    sorted_values = sorted(values, key=lambda x: x.get("value", 0), reverse=True)
    
    # Calculate differences from highest
    highest = sorted_values[0]["value"]
    comparisons = []
    
    for i, item in enumerate(sorted_values):
        diff_from_highest = ((item["value"] - highest) / highest) * 100 if highest != 0 else 0
        comparisons.append({
            "rank": i + 1,
            "name": item["name"],
            "value": item["value"],
            "diff_from_highest_percent": round(diff_from_highest, 2)
        })
    
    return {
        "success": True,
        "operation": "comparison",
        "metric_name": metric_name,
        "comparisons": comparisons,
        "highest": sorted_values[0]["name"],
        "lowest": sorted_values[-1]["name"]
    }


# =============================================================================
# BEDROCK AGENT HANDLER
# =============================================================================

def parse_agent_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse the incoming request from Bedrock Agent.
    
    Bedrock Agent sends requests in this format:
    {
        "actionGroup": "financial-calculator",
        "apiPath": "/calculate-growth",
        "httpMethod": "POST",
        "parameters": [...],
        "requestBody": {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "old_value", "value": "383.29"},
                        {"name": "new_value", "value": "391.04"}
                    ]
                }
            }
        }
    }
    """
    api_path = event.get("apiPath", "")
    
    # Extract parameters from requestBody
    parameters = {}
    request_body = event.get("requestBody", {})
    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    properties = json_content.get("properties", [])
    
    for prop in properties:
        name = prop.get("name")
        value = prop.get("value")
        
        # Try to convert to number if possible
        try:
            if "." in str(value):
                parameters[name] = float(value)
            else:
                parameters[name] = int(value)
        except (ValueError, TypeError):
            parameters[name] = value
    
    # Also check for direct parameters (alternative format)
    for param in event.get("parameters", []):
        name = param.get("name")
        value = param.get("value")
        try:
            if "." in str(value):
                parameters[name] = float(value)
            else:
                parameters[name] = int(value)
        except (ValueError, TypeError):
            parameters[name] = value
    
    return {
        "api_path": api_path,
        "parameters": parameters
    }


def format_agent_response(result: Dict[str, Any], api_path: str = "") -> Dict[str, Any]:
    """
    Format the response for Bedrock Agent.
    IMPORTANT: apiPath in response MUST match the request apiPath!
    """
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": "financial-calculator",
            "apiPath": api_path,  # THIS WAS MISSING!
            "httpMethod": "POST",
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(result)
                }
            }
        }
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Bedrock Agent Action Group.
    
    Routes requests to appropriate calculation functions based on apiPath.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Parse the agent request
        parsed = parse_agent_request(event)
        api_path = parsed["api_path"]
        params = parsed["parameters"]
        
        logger.info(f"API Path: {api_path}, Parameters: {params}")
        
        # Route to appropriate function
        if api_path == "/calculate-growth" or api_path == "/calculate-growth-rate":
            result = calculate_growth_rate(
                old_value=params.get("old_value", 0),
                new_value=params.get("new_value", 0)
            )
        
        elif api_path == "/calculate-ratio":
            result = calculate_ratio(
                numerator=params.get("numerator", 0),
                denominator=params.get("denominator", 0),
                ratio_name=params.get("ratio_name", "ratio")
            )
        
        elif api_path == "/calculate-margin":
            result = calculate_margin(
                revenue=params.get("revenue", 0),
                profit=params.get("profit", 0),
                margin_type=params.get("margin_type", "profit")
            )
        
        elif api_path == "/calculate-cagr":
            result = calculate_cagr(
                start_value=params.get("start_value", 0),
                end_value=params.get("end_value", 0),
                years=params.get("years", 1)
            )
        
        elif api_path == "/compare-values":
            # Parse values from string if needed
            values = params.get("values", [])
            if isinstance(values, str):
                values = json.loads(values)
            result = compare_values(
                values=values,
                metric_name=params.get("metric_name", "value")
            )
        
        else:
            result = {
                "success": False,
                "error": f"Unknown API path: {api_path}",
                "available_paths": [
                    "/calculate-growth",
                    "/calculate-ratio",
                    "/calculate-margin",
                    "/calculate-cagr",
                    "/compare-values"
                ]
            }
        
        logger.info(f"Result: {json.dumps(result)}")
        return format_agent_response(result, api_path)  # Pass api_path!
    
        
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        error_result = {
            "success": False,
            "error": str(e)
        }
        return format_agent_response(error_result, parsed.get("api_path", ""))

# =============================================================================
# LOCAL TESTING
# =============================================================================

if __name__ == "__main__":
    # Test growth rate
    print("Testing growth rate:")
    print(calculate_growth_rate(383.29, 391.04))
    
    # Test ratio
    print("\nTesting P/E ratio:")
    print(calculate_ratio(150, 6.5, "P/E Ratio"))
    
    # Test margin
    print("\nTesting profit margin:")
    print(calculate_margin(391.04, 97.0, "net profit"))
    
    # Test CAGR
    print("\nTesting CAGR:")
    print(calculate_cagr(260.17, 391.04, 5))
    
    # Test comparison
    print("\nTesting comparison:")
    print(compare_values([
        {"name": "Apple", "value": 391.04},
        {"name": "Microsoft", "value": 211.91},
        {"name": "Google", "value": 307.39}
    ], "Revenue (Billions)"))
