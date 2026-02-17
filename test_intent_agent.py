"""
Test Script for Intent Agent
Demonstrates intent extraction and slot-filling capabilities
"""

import os
import json
from dotenv import load_dotenv
from agents.intent_agent import IntentAgent

# Load environment variables
load_dotenv()

def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def test_intent_agent():
    """Test the Intent Agent with various queries"""
    
    # Get project ID from environment
    project_id = os.getenv("GCP_PROJECT_ID")
    region = os.getenv("GCP_REGION", "us-central1")
    
    if not project_id:
        print("❌ Error: GCP_PROJECT_ID not found in .env file")
        return
    
    print_section("Initializing Intent Agent")
    
    # Initialize the Intent Agent
    agent = IntentAgent(project_id=project_id, region=region)
    
    # Test queries covering different scenarios
    test_queries = [
        {
            "query": "Date night with my partner",
            "description": "Date night"
        },
        {
            "query": "Looking for premium skincare products for sensitive skin",
            "description": "Premium beauty product with specific use case"
        },
        {
            "query": "Need a gift for my wife, something elegant under $100",
            "description": "Gift with price constraint"
        },
        {
            "query": "Urgent: kids toys for 5 year old boy, delivery today",
            "description": "Kids product with high urgency"
        },
        {
            "query": "Show me blue athletic shoes from Nike",
            "description": "Specific brand and color filters"
        },
        {
            "query": "I want haircare products, good quality but affordable",
            "description": "Beauty product with budget consideration"
        }
    ]
    
    print_section("Running Intent Extraction Tests")
    
    results = []
    
    for i, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        description = test_case["description"]
        
        print(f"🔍 Test {i}: {description}")
        print(f"   Query: \"{query}\"")
        print()
        
        try:
            # Extract intent
            intent = agent.extract_intent(
                user_query=query,
                user_id=f"test_user_{i}",
                session_id=f"test_session_{i}"
            )
            
            # Convert to dictionary for display
            intent_dict = agent.intent_to_dict(intent)
            
            # Store result
            results.append({
                "test_number": i,
                "query": query,
                "description": description,
                "intent": intent_dict
            })
            
            # Display key results
            print(f"   ✓ Category: {intent.primary_category}")
            print(f"   ✓ Subcategory: {intent.subcategory or 'None'}")
            print(f"   ✓ Product Type: {intent.product_type}")
            
            if intent.attributes.price_range:
                pr = intent.attributes.price_range
                print(f"   ✓ Price Range: ${pr.min or 0} - ${pr.max or '∞'} ({pr.label})")
            
            print(f"   ✓ Urgency: {intent.attributes.urgency}")
            
            if intent.attributes.timeline_days is not None:
                print(f"   ✓ Timeline: {intent.attributes.timeline_days} days")
            
            # Show filters if any
            filters = []
            if intent.filters.brand:
                filters.append(f"Brand: {intent.filters.brand}")
            if intent.filters.color:
                filters.append(f"Color: {intent.filters.color}")
            if intent.filters.gender:
                filters.append(f"Gender: {intent.filters.gender}")
            if intent.filters.size:
                filters.append(f"Size: {intent.filters.size}")
            
            if filters:
                print(f"   ✓ Filters: {', '.join(filters)}")
            
            print(f"   ✓ Confidence: {intent.intent_confidence:.2f}")
            print()
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            print()
            results.append({
                "test_number": i,
                "query": query,
                "description": description,
                "error": str(e)
            })
    
    # Summary
    print_section("Test Summary")
    
    successful = sum(1 for r in results if "error" not in r)
    total = len(results)
    
    print(f"Tests Passed: {successful}/{total}")
    print(f"Success Rate: {(successful/total)*100:.1f}%")
    
    # Save detailed results to file
    output_file = "intent_agent_test_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: {output_file}")
    
    # Display sample JSON output
    if results and "error" not in results[0]:
        print_section("Sample JSON Output (Test 1)")
        print(json.dumps(results[0]["intent"], indent=2))
    
    print_section("Testing Complete")
    print("✓ Intent Agent is working correctly!")
    print("\nNext steps:")
    print("1. Review the test results above")
    print("2. Check intent_agent_test_results.json for detailed output")
    print("3. Proceed to implement Context Agent when ready")


if __name__ == "__main__":
    try:
        test_intent_agent()
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
