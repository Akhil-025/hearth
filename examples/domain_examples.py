"""
Example usage scenarios for domain intelligence modules.
"""
import asyncio
from datetime import datetime
from uuid import uuid4


async def example_hermes_message_drafting():
    """Example: Hermes message drafting."""
    print("\n=== Hermes Example: Message Drafting ===")
    
    from hearth.domains.hermes.service import HermesService
    from hearth.domains.base import DomainRequest, DomainCapability
    
    # Create Hermes service
    hermes = HermesService()
    await hermes.start()
    
    # Create request
    request = DomainRequest(
        domain_name="hermes",
        capability=DomainCapability.DRAFT_MESSAGE,
        user_id="example_user",
        session_id="example_session",
        input_data={
            "message_type": "email",
            "recipient": "Project Manager",
            "purpose": "request",
            "key_points": [
                "Need extension on project deadline",
                "Additional requirements discovered",
                "Team needs 2 more weeks"
            ],
            "constraints": [
                "Be professional but not defensive",
                "Acknowledge original deadline",
                "Offer to discuss alternatives"
            ]
        }
    )
    
    # Process request
    result = await hermes.process_request(request)
    
    print(f"\nGenerated {len(result.structured_output['drafts'])} draft(s):")
    for i, draft in enumerate(result.structured_output['drafts'], 1):
        print(f"\nDraft {i} ({draft['characteristics']['word_count']} words):")
        print("-" * 40)
        print(draft['content'])
        print(f"Suggested use: {draft['suggested_use']}")
    
    print(f"\nTone analysis completed with confidence: {result.confidence:.2f}")
    
    await hermes.stop()


async def example_hephaestus_code_analysis():
    """Example: Hephaestus code analysis."""
    print("\n=== Hephaestus Example: Code Analysis ===")
    
    from hearth.domains.hephaestus.service import HephaestusService
    from hearth.domains.base import DomainRequest, DomainCapability
    
    # Sample code to analyze
    sample_code = """
def calculate_stats(data):
    \"\"\"Calculate statistics for data.\"\"\"
    if not data:
        return None
    
    total = sum(data)
    count = len(data)
    mean = total / count
    
    # Calculate variance
    variance = sum((x - mean) ** 2 for x in data) / count
    
    return {
        'mean': mean,
        'variance': variance,
        'count': count
    }
"""
    
    # Create Hephaestus service
    hephaestus = HephaestusService()
    await hephaestus.start()
    
    # Create request
    request = DomainRequest(
        domain_name="hephaestus",
        capability=DomainCapability.CODE_ANALYSIS,
        user_id="example_user",
        session_id="example_session",
        input_data={
            "code": sample_code,
            "language": "python",
            "analysis_focus": ["complexity", "readability", "error_handling"]
        }
    )
    
    # Process request
    result = await hephaestus.process_request(request)
    
    print(f"\nCode Analysis Results:")
    print(f"Complexity metrics: {result.structured_output['complexity_metrics']}")
    
    if result.structured_output['issue_detection']:
        print(f"\nIssues detected:")
        for issue in result.structured_output['issue_detection']:
            print(f"  • {issue['type']}: {issue['description']}")
    
    if result.structured_output['improvement_suggestions']:
        print(f"\nSuggestions:")
        for suggestion in result.structured_output['improvement_suggestions']:
            print(f"  • {suggestion}")
    
    print(f"\nAnalysis confidence: {result.confidence:.2f}")
    
    await hephaestus.stop()


async def example_hestia_with_domains():
    """Example: Hestia using domain intelligence."""
    print("\n=== Hestia with Domain Integration Example ===")
    
    from hearth.hestia.agent import HestiaAgent, UserInput
    from hearth.core.kernel import HearthKernel, KernelConfig
    
    # Create kernel and agent
    kernel = HearthKernel(KernelConfig())
    agent = HestiaAgent()
    
    # Register and start
    await kernel.register_service(agent)
    await kernel.start()
    
    # Test cases with domain capabilities
    test_cases = [
        (
            "Can you help me draft an email to my boss asking for a deadline extension?",
            "Expected: Uses Hermes for message drafting"
        ),
        (
            "What's wrong with this Python code? It keeps giving me division by zero errors.",
            "Expected: Uses Hephaestus for code analysis"
        ),
        (
            "I want to improve my morning routine. Can you analyze my current habits?",
            "Expected: Uses Apollo for habit analysis"
        ),
        (
            "I'm feeling stressed and need some relaxing music recommendations.",
            "Expected: Uses Dionysus for music recommendations"
        )
    ]
    
    for user_message, expected in test_cases:
        print(f"\nTest: {expected}")
        print(f"User: {user_message}")
        
        user_input = UserInput(
            text=user_message,
            session_id="test_session",
            user_id="test_user"
        )
        
        response = await agent.process_input(user_input)
        
        if response.domain_results:
            print(f"✓ Used domain intelligence:")
            for domain_result in response.domain_results:
                print(f"  - {domain_result['domain_name']}: {domain_result['capability']}")
        else:
            print("✗ No domain intelligence used")
        
        print(f"Response: {response.text[:100]}...")
    
    await kernel.shutdown()


async def main():
    """Run all examples."""
    print("HEARTH Domain Intelligence Examples")
    print("=" * 60)
    
    # Run examples
    await example_hermes_message_drafting()
    await example_hephaestus_code_analysis()
    await example_hestia_with_domains()
    
    print("\n" + "=" * 60)
    print("All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())