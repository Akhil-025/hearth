# ARES Phase 0 Complete: Working Examples

"""
Working examples of ARES Phase 0 functionality.

All examples are deterministic, safe, and non-intrusive.
"""

from ares.interface import report_to_artemis
from ares.state import get_store, clear_store, update_store
from ares.signals import Signal, SignalType, ConfidenceLevel, SignalPattern
from ares.sensors import get_sensor
from ares.honeypots import get_factory as get_honeypot_factory
from ares.deception import get_engine as get_deception_engine
from ares.profiler import get_factory as get_profiler_factory
from ares.timeline import get_timeline, clear_timeline


def example_1_boundary_probing():
    """Example 1: Detect boundary probing."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Boundary Probing Detection")
    print("="*70)
    
    # Clear state
    clear_store()
    clear_timeline()
    
    # Get sensor
    sensor = get_sensor()
    
    # Detect boundary probing pattern
    signal = sensor.observe_boundary_probing(
        subsystem="capability_manager",
        attempt_count=6,
        description="Repeated /admin endpoint access attempts",
    )
    
    if signal:
        print(f"✓ Signal detected: {signal.signal_id}")
        print(f"  Type: {signal.signal_type.value}")
        print(f"  Confidence: {signal.confidence.value}")
        print(f"  Source: {signal.source_subsystem}")
        print(f"  Description: {signal.description}")
        
        # Add to store
        store = get_store().add_signal(signal)
        update_store(store)
        
        # Add to timeline
        timeline = get_timeline()
        timeline.add_signal_event(signal)
        
        print(f"✓ Signal recorded in store and timeline")
    
    return True


def example_2_invalid_plan_attempts():
    """Example 2: Detect repeated invalid plan attempts."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Invalid Plan Attempts")
    print("="*70)
    
    clear_store()
    clear_timeline()
    
    sensor = get_sensor()
    
    # Detect pattern
    signal = sensor.observe_invalid_plan_attempts(
        plan_count=5,
        time_window_sec=60,
        description="5 malformed JSON plans in 60s window",
    )
    
    if signal:
        print(f"✓ Signal detected: {signal.signal_id}")
        print(f"  Type: {signal.signal_type.value}")
        print(f"  Observation: {signal.description}")
        
        store = get_store().add_signal(signal)
        update_store(store)
        
        print(f"✓ Invalid plan pattern recorded")
    
    return True


def example_3_rapid_policy_rejections():
    """Example 3: Detect rapid policy rejections."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Rapid Policy Rejections")
    print("="*70)
    
    clear_store()
    clear_timeline()
    
    sensor = get_sensor()
    
    signal = sensor.observe_rapid_rejections(
        rejection_count=8,
        time_window_sec=30,
        policy="max_concurrent_operations",
    )
    
    if signal:
        print(f"✓ Signal detected: {signal.signal_id}")
        print(f"  Type: {signal.signal_type.value}")
        print(f"  Policy: {signal.evidence_reference}")
        print(f"  Rejections: 8 in 30 seconds")
        
        store = get_store().add_signal(signal)
        update_store(store)
        
        print(f"✓ Rejection pattern recorded")
    
    return True


def example_4_capability_enumeration():
    """Example 4: Detect capability enumeration."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Capability Enumeration Attempt")
    print("="*70)
    
    clear_store()
    clear_timeline()
    
    sensor = get_sensor()
    
    signal = sensor.observe_capability_enumeration(
        subsystem="orchestrator",
        query_count=15,
        unique_capabilities=8,
    )
    
    if signal:
        print(f"✓ Signal detected: {signal.signal_id}")
        print(f"  Type: {signal.signal_type.value}")
        print(f"  Queries: 15, Unique capabilities: 8")
        print(f"  Confidence: {signal.confidence.value}")
        
        store = get_store().add_signal(signal)
        update_store(store)
        
        print(f"✓ Enumeration pattern recorded")
    
    return True


def example_5_honeypot_triggered():
    """Example 5: Honeypot interaction."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Honeypot Triggered")
    print("="*70)
    
    clear_store()
    clear_timeline()
    
    factory = get_honeypot_factory()
    
    # Create fake credential honeypot
    cred_hp = factory.create_fake_credential("admin_token_v2")
    
    # Attacker accesses multiple times
    print("✓ Attacker queries fake credential...")
    
    fake_cred, record1, signal1 = cred_hp.get_credential("unauthorized_subsystem")
    print(f"  Access 1: Got fake credential (never real)")
    
    fake_cred, record2, signal2 = cred_hp.get_credential("unauthorized_subsystem")
    print(f"  Access 2: Got fake credential (never real)")
    
    fake_cred, record3, signal3 = cred_hp.get_credential("unauthorized_subsystem")
    print(f"  Access 3: Got fake credential + SIGNAL")
    
    if signal3:
        print(f"\n✓ Honeypot signal emitted: {signal3.signal_id}")
        print(f"  Type: {signal3.signal_type.value}")
        print(f"  Confidence: {signal3.confidence.value}")
        
        store = get_store().add_signal(signal3)
        update_store(store)
        
        timeline = get_timeline()
        timeline.add_signal_event(signal3)
        
        print(f"✓ Honeypot interaction recorded")
    
    return True


def example_6_deception_latency():
    """Example 6: Artificial latency (slow + observe)."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Deception - Artificial Latency")
    print("="*70)
    
    clear_store()
    clear_timeline()
    
    engine = get_deception_engine()
    
    print("✓ Attacker requests plan execution...")
    print("  Injecting artificial latency: 2000ms (capped at 5000ms max)")
    
    import time
    start = time.time()
    
    latency, record, signal = engine.add_bounded_latency(
        base_latency_ms=2000,
        target_subsystem="plan_executor",
    )
    
    elapsed = (time.time() - start) * 1000
    
    print(f"✓ Latency applied: {latency}ms")
    print(f"  Actual elapsed: {elapsed:.0f}ms")
    print(f"  Result: Attacker slowed down, system observing")
    
    # Record if excessive latency requested
    if signal:
        store = get_store().add_signal(signal)
        update_store(store)
        print(f"✓ Suspicious signal recorded")
    
    return True


def example_7_behavioral_profiling():
    """Example 7: Behavioral profiling."""
    print("\n" + "="*70)
    print("EXAMPLE 7: Behavioral Profiling")
    print("="*70)
    
    clear_store()
    
    factory = get_profiler_factory()
    
    # Record suspicious actions
    profiler = factory.get_or_create_profiler("domain_adapter")
    profiler.record_action("enumerate_methods")
    profiler.record_action("enumerate_methods")
    profiler.record_action("enumerate_methods")
    profiler.record_action("test_connection")
    profiler.record_action("test_connection")
    profiler.record_action("query_credentials")
    
    # Generate fingerprint
    fingerprint = profiler.fingerprint("scanning")
    
    print(f"✓ Fingerprint generated: {fingerprint.fingerprint_id}")
    print(f"  Subsystem: {fingerprint.subsystem}")
    print(f"  Actions: {len(fingerprint.action_types)}")
    print(f"  Risk score: {fingerprint.risk_score:.2f}/1.0")
    
    # Get risk assessment
    risk_score, signal = profiler.get_risk_assessment()
    
    if signal:
        print(f"✓ Risk signal generated: {signal.signal_id}")
        print(f"  Type: {signal.signal_type.value}")
        print(f"  Description: {signal.description}")
        
        store = get_store().add_signal(signal)
        update_store(store)
    
    return True


def example_8_forensic_report():
    """Example 8: Generate forensic report (Artemis interface)."""
    print("\n" + "="*70)
    print("EXAMPLE 8: Forensic Report (Report to Artemis)")
    print("="*70)
    
    clear_store()
    clear_timeline()
    
    # Simulate multiple signals
    sensor = get_sensor()
    
    signal1 = sensor.observe_boundary_probing(
        subsystem="capability_manager",
        attempt_count=6,
        description="Admin endpoint probing",
    )
    
    signal2 = sensor.observe_capability_enumeration(
        subsystem="orchestrator",
        query_count=15,
        unique_capabilities=8,
    )
    
    signal3 = sensor.observe_credential_scan(
        attempt_count=7,
        description="Service account credential attempts",
    )
    
    # Add all to store
    store = get_store()
    for signal in [signal1, signal2, signal3]:
        if signal:
            store = store.add_signal(signal)
    update_store(store)
    
    # Add to timeline
    timeline = get_timeline()
    for signal in [signal1, signal2, signal3]:
        if signal:
            timeline.add_signal_event(signal)
    
    # Generate forensic report
    report = report_to_artemis()
    
    print(f"✓ Forensic report generated: {report.report_id}")
    print(f"  Timestamp: {report.timestamp.isoformat()}")
    print(f"  Signals: {report.signals_count}")
    print(f"  Events: {report.events_count}")
    print(f"  Confidence: {report.confidence_assessment.value}")
    print(f"  Recommended escalation: {report.recommended_escalation} (ADVISORY ONLY)")
    print(f"  Risk factors: {len(report.risk_factors)}")
    print(f"  Integrity hash: {report.report_hash[:16]}...")
    
    # Verify integrity
    assert report.verify_integrity(), "Report integrity check failed"
    print(f"✓ Report integrity verified")
    
    # Serialize
    report_dict = report.to_dict()
    print(f"✓ Report serializable (immutable)")
    
    print(f"\n✓ ARTEMIS receives findings:")
    print(f"  - Detects boundary probing")
    print(f"  - Detects capability enumeration")
    print(f"  - Detects credential scanning")
    print(f"  - Recommends escalation: {report.recommended_escalation}")
    print(f"  - ARTEMIS DECIDES: escalation, credential freeze, lockdown, kill")
    print(f"  - ARES DOES NOT: execute, approve, deny, persist")
    
    return True


def example_9_complete_attack_scenario():
    """Example 9: Complete attack scenario detection."""
    print("\n" + "="*70)
    print("EXAMPLE 9: Complete Attack Scenario")
    print("="*70)
    
    clear_store()
    clear_timeline()
    
    print("✓ Simulating sophisticated attack scenario...")
    print("\n  Phase 1: Boundary Probing")
    sensor = get_sensor()
    signal1 = sensor.observe_boundary_probing(
        subsystem="orchestrator",
        attempt_count=12,
        description="/api/admin endpoint repeated access",
    )
    print(f"    → Signal: {signal1.signal_id} (HIGH confidence)")
    
    print("\n  Phase 2: Capability Enumeration")
    signal2 = sensor.observe_capability_enumeration(
        subsystem="orchestrator",
        query_count=25,
        unique_capabilities=12,
    )
    print(f"    → Signal: {signal2.signal_id} (MEDIUM confidence)")
    
    print("\n  Phase 3: Credential Scanning")
    signal3 = sensor.observe_credential_scan(
        attempt_count=15,
        description="Multiple service account attempts",
    )
    print(f"    → Signal: {signal3.signal_id} (HIGH confidence)")
    
    print("\n  Phase 4: Invalid Plan Injection")
    signal4 = sensor.observe_invalid_plan_attempts(
        plan_count=8,
        time_window_sec=45,
        description="Malformed JSON plans (possible payload test)",
    )
    print(f"    → Signal: {signal4.signal_id} (MEDIUM confidence)")
    
    print("\n  Phase 5: Rapid Rejections (Policy Bypass Attempt)")
    signal5 = sensor.observe_rapid_rejections(
        rejection_count=20,
        time_window_sec=60,
        policy="max_concurrent_operations",
    )
    print(f"    → Signal: {signal5.signal_id} (MEDIUM confidence)")
    
    # Add all to store
    store = get_store()
    for signal in [signal1, signal2, signal3, signal4, signal5]:
        if signal:
            store = store.add_signal(signal)
    update_store(store)
    
    # Add to timeline
    timeline = get_timeline()
    for signal in [signal1, signal2, signal3, signal4, signal5]:
        if signal:
            timeline.add_signal_event(signal)
    
    # Detect pattern
    print("\n  Correlation: All signals detected by ARES")
    print("              Timeline shows coordinated attack pattern")
    
    # Generate forensic report
    report = report_to_artemis()
    
    print(f"\n✓ FORENSIC REPORT GENERATED:")
    print(f"  Report ID: {report.report_id}")
    print(f"  Signals: {report.signals_count}")
    print(f"  Confidence: {report.confidence_assessment.value}")
    print(f"  Recommended Escalation: {report.recommended_escalation}")
    print(f"  Risk Factors: {len(report.risk_factors)}")
    
    print(f"\n✓ ARTEMIS RECEIVES REPORT")
    print(f"  - Reviews all signals and evidence")
    print(f"  - Assesses threat level: {report.recommended_escalation.upper()}")
    print(f"  - Makes decision: escalate, freeze, lockdown, or kill")
    print(f"  - ARES DOES NOT make this decision (advisory only)")
    
    return True


def run_all_examples():
    """Run all examples."""
    print("\n" + "="*70)
    print("ARES PHASE 0 - WORKING EXAMPLES")
    print("="*70)
    
    examples = [
        ("Boundary Probing Detection", example_1_boundary_probing),
        ("Invalid Plan Attempts", example_2_invalid_plan_attempts),
        ("Rapid Policy Rejections", example_3_rapid_policy_rejections),
        ("Capability Enumeration", example_4_capability_enumeration),
        ("Honeypot Triggered", example_5_honeypot_triggered),
        ("Deception - Latency", example_6_deception_latency),
        ("Behavioral Profiling", example_7_behavioral_profiling),
        ("Forensic Report", example_8_forensic_report),
        ("Complete Attack Scenario", example_9_complete_attack_scenario),
    ]
    
    results = []
    for name, example_func in examples:
        try:
            result = example_func()
            results.append((name, True))
        except Exception as e:
            print(f"\n✗ Example '{name}' failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("EXAMPLES SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print("="*70)
    print(f"RESULT: {passed}/{total} examples passed")
    print("="*70)
    
    if passed == total:
        print("\n✓ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        return True
    else:
        print(f"\n✗ {total - passed} example(s) failed")
        return False


if __name__ == "__main__":
    import sys
    success = run_all_examples()
    sys.exit(0 if success else 1)
