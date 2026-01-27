"""
Risk Envelope Enforcement - Hard constraints for financial recommendations.

Pluto must refuse recommendations violating risk envelope.
Returns structured refusal reasons.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ..core.invariants import enforce_invariants
from ..shared.logging.structured_logger import StructuredLogger
from ..shared.schemas.finance import Currency, TransactionType


class RiskViolation(Enum):
    """Types of risk envelope violations."""
    MAX_DRAWDOWN_EXCEEDED = "max_drawdown_exceeded"
    MAX_EXPOSURE_EXCEEDED = "max_exposure_exceeded"
    TIME_HORIZON_VIOLATION = "time_horizon_violation"
    NEVER_SUGGEST_VIOLATION = "never_suggest_violation"
    CONCENTRATION_RISK = "concentration_risk"
    LIQUIDITY_RISK = "liquidity_risk"
    LEVERAGE_RISK = "leverage_risk"


class RiskLevel(Enum):
    """Risk levels for envelope constraints."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class RiskConstraint(BaseModel):
    """Individual risk constraint."""
    constraint_id: str
    description: str
    risk_type: RiskViolation
    
    # Constraint values
    max_value: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    threshold: Optional[Decimal] = None
    
    # Time-based constraints
    time_horizon_days: Optional[int] = None
    evaluation_period_days: Optional[int] = None
    
    # Enforcement
    hard_limit: bool = True  # True = cannot be violated, False = warning
    requires_approval: bool = False
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True  # For Decimal


class NeverSuggestRule(BaseModel):
    """Rule for things to never suggest."""
    rule_id: str
    description: str
    condition: Dict[str, any]  # Condition that triggers the rule
    justification: str
    alternatives: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class RiskEnvelope(BaseModel):
    """Complete risk envelope configuration."""
    envelope_id: UUID = Field(default_factory=uuid4)
    user_id: str
    risk_level: RiskLevel = RiskLevel.CONSERVATIVE
    
    # Core constraints
    max_drawdown_percent: Decimal = Field(default=Decimal("20.0"), ge=Decimal("0.0"), le=Decimal("100.0"))
    max_exposure_percent: Decimal = Field(default=Decimal("30.0"), ge=Decimal("0.0"), le=Decimal("100.0"))
    time_horizon_days: int = Field(default=365, ge=1, le=3650)  # 1 year default
    
    # Additional constraints
    constraints: List[RiskConstraint] = Field(default_factory=list)
    never_suggest_rules: List[NeverSuggestRule] = Field(default_factory=list)
    
    # Current state
    current_exposure: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    current_drawdown: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    
    # Audit trail
    violations: List[Dict[str, any]] = Field(default_factory=list)
    overrides: List[Dict[str, any]] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True
    
    def update_state(
        self,
        exposure_change: Decimal = Decimal("0.0"),
        drawdown_change: Decimal = Decimal("0.0")
    ) -> None:
        """Update current risk state."""
        self.current_exposure += exposure_change
        self.current_drawdown += drawdown_change
        
        # Ensure values stay within bounds
        self.current_exposure = max(Decimal("0.0"), min(self.current_exposure, Decimal("100.0")))
        self.current_drawdown = max(Decimal("0.0"), min(self.current_drawdown, Decimal("100.0")))
        
        self.updated_at = datetime.now()


class RiskAssessment(BaseModel):
    """Result of risk assessment."""
    assessment_id: UUID = Field(default_factory=uuid4)
    envelope_id: UUID
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Assessment results
    passed: bool
    violations: List[Dict[str, any]] = Field(default_factory=list)
    warnings: List[Dict[str, any]] = Field(default_factory=list)
    
    # Recommendation
    allowed: bool
    reason: str
    alternative_suggestions: List[str] = Field(default_factory=list)
    
    # Risk metrics
    risk_score: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), le=Decimal("100.0"))
    confidence: Decimal = Field(default=Decimal("1.0"), ge=Decimal("0.0"), le=Decimal("1.0"))
    
    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True


class RiskEnforcer:
    """
    Enforces risk envelope constraints.
    
    Pluto must refuse recommendations violating envelope.
    Returns structured refusal reasons.
    """
    
    def __init__(self):
        self.logger = StructuredLogger(__name__)
        
        # Risk envelopes by user
        self.envelopes: Dict[str, RiskEnvelope] = {}
        
        # Default constraint templates
        self.default_constraints = self._create_default_constraints()
        self.default_never_suggest = self._create_default_never_suggest()
        
        # Statistics
        self.stats = {
            "assessments": 0,
            "violations": 0,
            "overrides": 0,
            "recommendations_blocked": 0
        }
        
        self.logger.info("Risk enforcer initialized")
    
    def _create_default_constraints(self) -> List[RiskConstraint]:
        """Create default risk constraints."""
        return [
            RiskConstraint(
                constraint_id="max_single_position",
                description="Maximum allocation to single position",
                risk_type=RiskViolation.CONCENTRATION_RISK,
                max_value=Decimal("10.0"),  # 10% max
                hard_limit=True,
                requires_approval=True
            ),
            RiskConstraint(
                constraint_id="min_liquidity",
                description="Minimum liquidity requirement",
                risk_type=RiskViolation.LIQUIDITY_RISK,
                min_value=Decimal("20.0"),  # 20% minimum liquidity
                hard_limit=True,
                requires_approval=False
            ),
            RiskConstraint(
                constraint_id="max_leverage",
                description="Maximum leverage ratio",
                risk_type=RiskViolation.LEVERAGE_RISK,
                max_value=Decimal("2.0"),  # 2x max leverage
                hard_limit=True,
                requires_approval=True
            ),
            RiskConstraint(
                constraint_id="volatility_limit",
                description="Maximum portfolio volatility",
                risk_type=RiskViolation.CONCENTRATION_RISK,
                max_value=Decimal("15.0"),  # 15% annual volatility
                hard_limit=False,  # Warning only
                requires_approval=False
            )
        ]
    
    def _create_default_never_suggest_rules(self) -> List[NeverSuggestRule]:
        """Create default never-suggest rules."""
        return [
            NeverSuggestRule(
                rule_id="no_penny_stocks",
                description="Never suggest penny stocks",
                condition={
                    "asset_type": "stock",
                    "price": {"$lt": 5.0},  # Under $5
                    "market_cap": {"$lt": 300_000_000}  # Under $300M
                },
                justification="High risk, low liquidity, potential for manipulation",
                alternatives=["Consider established companies with stronger fundamentals"]
            ),
            NeverSuggestRule(
                rule_id="no_high_fee_products",
                description="Never suggest high-fee financial products",
                condition={
                    "fee_percentage": {"$gt": 2.0},  # Over 2% fees
                    "product_type": {"$in": ["mutual_fund", "etf", "annuity"]}
                },
                justification="High fees erode returns significantly over time",
                alternatives=["Look for low-cost index funds or ETFs with fees under 0.5%"]
            ),
            NeverSuggestRule(
                rule_id="no_excessive_leverage",
                description="Never suggest excessive leverage",
                condition={
                    "leverage_ratio": {"$gt": 5.0},  # Over 5x leverage
                    "asset_class": {"$ne": "cash"}  # Not cash
                },
                justification="Excessive leverage can lead to total loss",
                alternatives=["Consider conservative margin use with maximum 2x leverage"]
            ),
            NeverSuggestRule(
                rule_id="no_illiquid_investments",
                description="Never suggest illiquid investments",
                condition={
                    "liquidity_days": {"$gt": 30},  # Takes over 30 days to liquidate
                    "asset_class": {"$in": ["private_equity", "real_estate", "collectibles"]}
                },
                justification="Illiquidity prevents access to funds when needed",
                alternatives=["Consider publicly traded alternatives with daily liquidity"]
            )
        ]
    
    def create_envelope(
        self,
        user_id: str,
        risk_level: RiskLevel = RiskLevel.CONSERVATIVE,
        custom_constraints: Optional[List[RiskConstraint]] = None
    ) -> RiskEnvelope:
        """Create a risk envelope for a user."""
        # Set values based on risk level
        if risk_level == RiskLevel.CONSERVATIVE:
            max_drawdown = Decimal("15.0")
            max_exposure = Decimal("25.0")
            time_horizon = 730  # 2 years
        elif risk_level == RiskLevel.MODERATE:
            max_drawdown = Decimal("25.0")
            max_exposure = Decimal("40.0")
            time_horizon = 365  # 1 year
        else:  # AGGRESSIVE
            max_drawdown = Decimal("40.0")
            max_exposure = Decimal("60.0")
            time_horizon = 180  # 6 months
        
        # Create envelope
        envelope = RiskEnvelope(
            user_id=user_id,
            risk_level=risk_level,
            max_drawdown_percent=max_drawdown,
            max_exposure_percent=max_exposure,
            time_horizon_days=time_horizon,
            constraints=self.default_constraints.copy(),
            never_suggest_rules=self.default_never_suggest.copy()
        )
        
        # Add custom constraints
        if custom_constraints:
            envelope.constraints.extend(custom_constraints)
        
        # Store envelope
        self.envelopes[user_id] = envelope
        
        self.logger.info(
            "Risk envelope created",
            user_id=user_id,
            risk_level=risk_level.value,
            max_drawdown=max_drawdown,
            max_exposure=max_exposure
        )
        
        return envelope
    
    @enforce_invariants(module="pluto", operation="risk_assessment")
    def assess_recommendation(
        self,
        user_id: str,
        recommendation: Dict[str, any],
        current_portfolio: Optional[Dict[str, any]] = None
    ) -> RiskAssessment:
        """
        Assess a recommendation against risk envelope.
        
        Args:
            user_id: User identifier
            recommendation: Recommendation to assess
            current_portfolio: Current portfolio state (optional)
        
        Returns:
            RiskAssessment with allowed status and violations
        """
        self.stats["assessments"] += 1
        
        # Get user's envelope
        envelope = self.envelopes.get(user_id)
        if not envelope:
            # Create default envelope if none exists
            envelope = self.create_envelope(user_id, RiskLevel.CONSERVATIVE)
        
        # Initialize assessment
        assessment = RiskAssessment(
            envelope_id=envelope.envelope_id,
            passed=True,
            allowed=True,
            reason="Initial assessment"
        )
        
        # Check core constraints
        core_violations = self._check_core_constraints(
            envelope, recommendation, current_portfolio
        )
        
        if core_violations:
            assessment.violations.extend(core_violations)
            assessment.passed = False
        
        # Check additional constraints
        constraint_violations = self._check_constraints(
            envelope, recommendation, current_portfolio
        )
        
        if constraint_violations:
            assessment.violations.extend(constraint_violations)
            assessment.passed = False
        
        # Check never-suggest rules
        never_suggest_violations = self._check_never_suggest(
            envelope, recommendation
        )
        
        if never_suggest_violations:
            assessment.violations.extend(never_suggest_violations)
            assessment.passed = False
        
        # Check time horizon
        time_violations = self._check_time_horizon(
            envelope, recommendation
        )
        
        if time_violations:
            assessment.violations.extend(time_violations)
            assessment.passed = False
        
        # Determine final allowed status
        if not assessment.passed:
            assessment.allowed = False
            
            # Check if any violations are hard limits
            hard_limit_violations = [
                v for v in assessment.violations 
                if v.get("hard_limit", True)
            ]
            
            if hard_limit_violations:
                assessment.allowed = False
                assessment.reason = "Hard risk limits violated"
                self.stats["recommendations_blocked"] += 1
            else:
                # Only warnings, recommendation allowed with warnings
                assessment.allowed = True
                assessment.warnings = [v for v in assessment.violations if not v.get("hard_limit", True)]
                assessment.violations = []
                assessment.reason = "Allowed with warnings"
        
        else:
            assessment.reason = "All risk checks passed"
        
        # Update statistics
        if not assessment.allowed:
            self.stats["violations"] += len(assessment.violations)
        
        # Calculate risk score
        assessment.risk_score = self._calculate_risk_score(
            envelope, recommendation, assessment.violations
        )
        
        # Generate alternative suggestions if blocked
        if not assessment.allowed and assessment.violations:
            assessment.alternative_suggestions = self._generate_alternatives(
                recommendation, assessment.violations
            )
        
        # Log assessment
        self.logger.info(
            "Risk assessment completed",
            user_id=user_id,
            allowed=assessment.allowed,
            risk_score=float(assessment.risk_score),
            violations=len(assessment.violations),
            warnings=len(assessment.warnings)
        )
        
        return assessment
    
    def _check_core_constraints(
        self,
        envelope: RiskEnvelope,
        recommendation: Dict[str, any],
        current_portfolio: Optional[Dict[str, any]]
    ) -> List[Dict[str, any]]:
        """Check core risk envelope constraints."""
        violations = []
        
        # Check max drawdown
        projected_drawdown = recommendation.get("projected_drawdown", Decimal("0.0"))
        if isinstance(projected_drawdown, (int, float)):
            projected_drawdown = Decimal(str(projected_drawdown))
        
        if projected_drawdown > envelope.max_drawdown_percent:
            violations.append({
                "constraint": "max_drawdown",
                "type": RiskViolation.MAX_DRAWDOWN_EXCEEDED.value,
                "limit": float(envelope.max_drawdown_percent),
                "actual": float(projected_drawdown),
                "excess": float(projected_drawdown - envelope.max_drawdown_percent),
                "hard_limit": True,
                "message": f"Projected drawdown {projected_drawdown}% exceeds maximum {envelope.max_drawdown_percent}%"
            })
        
        # Check max exposure
        new_exposure = recommendation.get("new_exposure", Decimal("0.0"))
        if isinstance(new_exposure, (int, float)):
            new_exposure = Decimal(str(new_exposure))
        
        total_exposure = envelope.current_exposure + new_exposure
        
        if total_exposure > envelope.max_exposure_percent:
            violations.append({
                "constraint": "max_exposure",
                "type": RiskViolation.MAX_EXPOSURE_EXCEEDED.value,
                "limit": float(envelope.max_exposure_percent),
                "actual": float(total_exposure),
                "excess": float(total_exposure - envelope.max_exposure_percent),
                "hard_limit": True,
                "message": f"Total exposure {total_exposure}% exceeds maximum {envelope.max_exposure_percent}%"
            })
        
        return violations
    
    def _check_constraints(
        self,
        envelope: RiskEnvelope,
        recommendation: Dict[str, any],
        current_portfolio: Optional[Dict[str, any]]
    ) -> List[Dict[str, any]]:
        """Check additional risk constraints."""
        violations = []
        
        for constraint in envelope.constraints:
            constraint_check = self._evaluate_constraint(
                constraint, recommendation, current_portfolio
            )
            
            if not constraint_check["passed"]:
                violation = {
                    "constraint_id": constraint.constraint_id,
                    "type": constraint.risk_type.value,
                    "description": constraint.description,
                    "hard_limit": constraint.hard_limit,
                    "requires_approval": constraint.requires_approval,
                    "message": constraint_check["message"],
                    "details": constraint_check.get("details", {})
                }
                
                if constraint.hard_limit:
                    violation["severity"] = "blocking"
                else:
                    violation["severity"] = "warning"
                
                violations.append(violation)
        
        return violations
    
    def _evaluate_const