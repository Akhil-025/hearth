"""
Hephaestus - Engineering & Technology Intelligence Domain
"""
from typing import Any, Dict, List

from ...shared.logging.structured_logger import StructuredLogger
from ..base import BaseDomainService, DomainCapability, DomainCapabilityInfo, DomainRequest, DomainResult

from .design_reasoner import DesignReasoner, ArchitecturePattern
from .code_inspector import CodeInspector, CodeAnalysis
from .debug_advisor import DebugAdvisor, DebugStrategy
from .tech_stack_planner import TechStackPlanner, StackRecommendation
from .research_structurer import ResearchStructurer, ResearchPlan


class HephaestusService(BaseDomainService):
    """
    Hephaestus - Engineering intelligence domain.
    
    Handles: Code analysis, system design, debugging, research structuring.
    Does NOT: Run code, modify files, call external APIs.
    """
    
    def __init__(self):
        super().__init__("hephaestus", "1.0.0")
        
        # Initialize subcomponents
        self.design_reasoner = DesignReasoner()
        self.code_inspector = CodeInspector()
        self.debug_advisor = DebugAdvisor()
        self.tech_stack_planner = TechStackPlanner()
        self.research_structurer = ResearchStructurer()
        
        self.logger = StructuredLogger("domain.hephaestus")
    
    def _register_capabilities(self) -> None:
        """Register Hephaestus capabilities."""
        
        # Code analysis
        self.register_capability(
            DomainCapabilityInfo(
                capability=DomainCapability.CODE_ANALYSIS,
                description="Analyze code structure, complexity, and patterns",
                input_schema={
                    "type": "object",
                    "required": ["code", "language"],
                    "properties": {
                        "code": {"type": "string"},
                        "language": {"type": "string"},
                        "analysis_focus": {"type": "array", "items": {"type": "string"}},
                        "context": {"type": "string"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "complexity_metrics": {"type": "object"},
                        "pattern_analysis": {"type": "object"},
                        "issue_detection": {"type": "array", "items": {"type": "object"}},
                        "improvement_suggestions": {"type": "array", "items": {"type": "string"}}
                    }
                }
            )
        )
        
        # System design
        self.register_capability(
            DomainCapabilityInfo(
                capability=DomainCapability.SYSTEM_DESIGN,
                description="Reason about system architecture and design patterns",
                input_schema={
                    "type": "object",
                    "required": ["requirements", "constraints"],
                    "properties": {
                        "requirements": {"type": "array", "items": {"type": "string"}},
                        "constraints": {"type": "array", "items": {"type": "string"}},
                        "scope": {"type": "string"},
                        "existing_architecture": {"type": "object"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "architecture_options": {"type": "array", "items": {"type": "object"}},
                        "tradeoff_analysis": {"type": "object"},
                        "pattern_recommendations": {"type": "array", "items": {"type": "object"}},
                        "implementation_roadmap": {"type": "array", "items": {"type": "object"}}
                    }
                }
            )
        )
        
        # Debug assistance
        self.register_capability(
            DomainCapabilityInfo(
                capability=DomainCapability.DEBUG_ASSISTANCE,
                description="Provide structured debugging strategies and analysis",
                input_schema={
                    "type": "object",
                    "required": ["problem_description", "system_context"],
                    "properties": {
                        "problem_description": {"type": "string"},
                        "system_context": {"type": "string"},
                        "symptoms": {"type": "array", "items": {"type": "string"}},
                        "already_tried": {"type": "array", "items": {"type": "string"}},
                        "error_messages": {"type": "array", "items": {"type": "string"}}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "likely_causes": {"type": "array", "items": {"type": "object"}},
                        "debugging_strategies": {"type": "array", "items": {"type": "object"}},
                        "diagnostic_steps": {"type": "array", "items": {"type": "object"}},
                        "prevention_suggestions": {"type": "array", "items": {"type": "string"}}
                    }
                }
            )
        )
        
        # Tech stack planning
        self.register_capability(
            DomainCapabilityInfo(
                capability=DomainCapability.TECH_STACK_PLANNING,
                description="Plan technology stacks based on requirements and constraints",
                input_schema={
                    "type": "object",
                    "required": ["project_type", "requirements"],
                    "properties": {
                        "project_type": {"type": "string"},
                        "requirements": {"type": "array", "items": {"type": "string"}},
                        "constraints": {"type": "array", "items": {"type": "string"}},
                        "team_expertise": {"type": "array", "items": {"type": "string"}},
                        "existing_infrastructure": {"type": "object"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "stack_options": {"type": "array", "items": {"type": "object"}},
                        "comparison_matrix": {"type": "object"},
                        "migration_paths": {"type": "array", "items": {"type": "object"}},
                        "learning_resources": {"type": "array", "items": {"type": "object"}}
                    }
                }
            )
        )
        
        # Research structuring
        self.register_capability(
            DomainCapabilityInfo(
                capability=DomainCapability.DEBUG_ASSISTANCE,  # Reusing for now
                description="Structure research and learning plans",
                input_schema={
                    "type": "object",
                    "required": ["topic", "goal"],
                    "properties": {
                        "topic": {"type": "string"},
                        "goal": {"type": "string"},
                        "current_knowledge": {"type": "string"},
                        "time_available": {"type": "string"},
                        "learning_style": {"type": "string"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "learning_path": {"type": "array", "items": {"type": "object"}},
                        "resource_recommendations": {"type": "array", "items": {"type": "object"}},
                        "milestones": {"type": "array", "items": {"type": "object"}},
                        "knowledge_gaps": {"type": "array", "items": {"type": "string"}}
                    }
                }
            )
        )
    
    async def _process_capability(self, request: DomainRequest) -> DomainResult:
        """Process Hephaestus capability requests."""
        
        if request.capability == DomainCapability.CODE_ANALYSIS:
            return await self._process_code_analysis(request)
        elif request.capability == DomainCapability.SYSTEM_DESIGN:
            return await self._process_system_design(request)
        elif request.capability == DomainCapability.DEBUG_ASSISTANCE:
            return await self._process_debug_assistance(request)
        elif request.capability == DomainCapability.TECH_STACK_PLANNING:
            return await self._process_tech_stack_planning(request)
        else:
            # Research structuring (using debug capability for now)
            return await self._process_research_structuring(request)
    
    async def _process_code_analysis(self, request: DomainRequest) -> DomainResult:
        """Process code analysis request."""
        code = request.input_data.get("code", "")
        language = request.input_data.get("language", "python")
        analysis_focus = request.input_data.get("analysis_focus", [])
        context = request.input_data.get("context", "")
        
        # Analyze code
        analysis = self.code_inspector.analyze(
            code=code,
            language=language,
            focus_areas=analysis_focus,
            context=context
        )
        
        return DomainResult(
            request_id=request.request_id,
            domain_name=self.domain_name,
            capability=request.capability,
            analysis={
                "code_size": len(code),
                "language": language,
                "focus_areas": len(analysis_focus)
            },
            structured_output={
                "complexity_metrics": analysis.metrics,
                "pattern_analysis": analysis.patterns,
                "issue_detection": analysis.issues,
                "improvement_suggestions": analysis.suggestions
            },
            confidence=analysis.confidence
        )
    
    async def _process_system_design(self, request: DomainRequest) -> DomainResult:
        """Process system design request."""
        requirements = request.input_data.get("requirements", [])
        constraints = request.input_data.get("constraints", [])
        scope = request.input_data.get("scope", "general")
        existing_arch = request.input_data.get("existing_architecture", {})
        
        # Generate design options
        options = self.design_reasoner.generate_designs(
            requirements=requirements,
            constraints=constraints,
            scope=scope,
            existing_architecture=existing_arch
        )
        
        # Analyze tradeoffs
        tradeoffs = self.design_reasoner.analyze_tradeoffs(options)
        
        # Recommend patterns
        patterns = self.design_reasoner.recommend_patterns(
            requirements,
            constraints
        )
        
        # Create roadmap
        roadmap = self.design_reasoner.create_roadmap(
            options[0] if options else {},
            existing_arch
        )
        
        return DomainResult(
            request_id=request.request_id,
            domain_name=self.domain_name,
            capability=request.capability,
            analysis={
                "requirement_count": len(requirements),
                "constraint_count": len(constraints),
                "design_options": len(options)
            },
            structured_output={
                "architecture_options": options,
                "tradeoff_analysis": tradeoffs,
                "pattern_recommendations": patterns,
                "implementation_roadmap": roadmap
            },
            confidence=0.8
        )
    
    async def _process_debug_assistance(self, request: DomainRequest) -> DomainResult:
        """Process debug assistance request."""
        problem = request.input_data.get("problem_description", "")
        context = request.input_data.get("system_context", "")
        symptoms = request.input_data.get("symptoms", [])
        already_tried = request.input_data.get("already_tried", [])
        error_messages = request.input_data.get("error_messages", [])
        
        # Analyze problem
        analysis = self.debug_advisor.analyze_problem(
            problem_description=problem,
            system_context=context,
            symptoms=symptoms,
            already_tried=already_tried,
            error_messages=error_messages
        )
        
        # Generate strategies
        strategies = self.debug_advisor.generate_strategies(analysis)
        
        # Diagnostic steps
        steps = self.debug_advisor.create_diagnostic_plan(analysis, strategies)
        
        # Prevention suggestions
        prevention = self.debug_advisor.suggest_prevention(analysis)
        
        return DomainResult(
            request_id=request.request_id,
            domain_name=self.domain_name,
            capability=request.capability,
            analysis={
                "problem_complexity": len(problem.split()),
                "symptom_count": len(symptoms),
                "error_count": len(error_messages)
            },
            structured_output={
                "likely_causes": analysis.likely_causes,
                "debugging_strategies": strategies,
                "diagnostic_steps": steps,
                "prevention_suggestions": prevention
            },
            confidence=analysis.confidence
        )
    
    async def _process_tech_stack_planning(self, request: DomainRequest) -> DomainResult:
        """Process tech stack planning request."""
        project_type = request.input_data.get("project_type", "")
        requirements = request.input_data.get("requirements", [])
        constraints = request.input_data.get("constraints", [])
        team_expertise = request.input_data.get("team_expertise", [])
        existing_infra = request.input_data.get("existing_infrastructure", {})
        
        # Generate stack options
        stacks = self.tech_stack_planner.generate_stacks(
            project_type=project_type,
            requirements=requirements,
            constraints=constraints,
            team_expertise=team_expertise,
            existing_infrastructure=existing_infra
        )
        
        # Compare options
        comparison = self.tech_stack_planner.compare_stacks(stacks)
        
        # Migration paths if existing infra
        migrations = []
        if existing_infra:
            migrations = self.tech_stack_planner.plan_migrations(
                existing_infra,
                stacks
            )
        
        # Learning resources
        resources = self.tech_stack_planner.suggest_resources(stacks)
        
        return DomainResult(
            request_id=request.request_id,
            domain_name=self.domain_name,
            capability=request.capability,
            analysis={
                "project_type": project_type,
                "requirement_count": len(requirements),
                "stack_options": len(stacks)
            },
            structured_output={
                "stack_options": stacks,
                "comparison_matrix": comparison,
                "migration_paths": migrations,
                "learning_resources": resources
            },
            confidence=0.85
        )
    
    async def _process_research_structuring(self, request: DomainRequest) -> DomainResult:
        """Process research structuring request."""
        topic = request.input_data.get("topic", "")
        goal = request.input_data.get("goal", "")
        current_knowledge = request.input_data.get("current_knowledge", "")
        time_available = request.input_data.get("time_available", "medium")
        learning_style = request.input_data.get("learning_style", "balanced")
        
        # Create research plan
        plan = self.research_structurer.create_plan(
            topic=topic,
            goal=goal,
            current_knowledge=current_knowledge,
            time_available=time_available,
            learning_style=learning_style
        )
        
        return DomainResult(
            request_id=request.request_id,
            domain_name=self.domain_name,
            capability=DomainCapability.DEBUG_ASSISTANCE,  # Note: reusing
            analysis={
                "topic_complexity": len(topic.split()),
                "goal_clarity": len(goal.split()),
                "plan_depth": len(plan.learning_path)
            },
            structured_output={
                "learning_path": plan.learning_path,
                "resource_recommendations": plan.resources,
                "milestones": plan.milestones,
                "knowledge_gaps": plan.knowledge_gaps
            },
            confidence=plan.confidence
        )