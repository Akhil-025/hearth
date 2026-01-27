"""
HEARTH REST API - FastAPI-based REST interface.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ...core.kernel import HearthKernel, KernelConfig
from ...hestia.agent import HestiaAgent, UserInput
from ...shared.logging.structured_logger import StructuredLogger


# Security
security = HTTPBearer()
API_KEY = "hearth-dev-key"  # TODO: Load from config

logger = StructuredLogger(__name__)


class APIError(BaseModel):
    """API error response."""
    error: str
    details: Optional[Dict] = None
    request_id: str


class ChatRequest(BaseModel):
    """Chat request."""
    message: str
    session_id: Optional[str] = None
    user_id: str = "api_user"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Chat response."""
    response_id: str
    message: str
    session_id: str
    timestamp: datetime
    processing_time_ms: float
    memory_proposals: int
    actions_executed: List[Dict] = Field(default_factory=list)


class SystemStatus(BaseModel):
    """System status response."""
    status: str
    services: Dict[str, Dict]
    uptime_seconds: float
    version: str = "0.1.0"


class HearthAPI:
    """HEARTH REST API application."""
    
    def __init__(self):
        self.app = FastAPI(
            title="HEARTH API",
            description="Personal Cognitive Operating System",
            version="0.1.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        self.kernel: Optional[HearthKernel] = None
        self.agent: Optional[HestiaAgent] = None
        self.start_time = datetime.now()
        
        self._setup_middleware()
        self._setup_routes()
        
        logger.info("HEARTH API initialized")
    
    def _setup_middleware(self):
        """Setup API middleware."""
        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],  # Frontend origin
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.on_event("startup")
        async def startup_event():
            """Initialize services on startup."""
            await self.initialize()
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            """Shutdown services on shutdown."""
            await self.shutdown()
        
        @self.app.get("/health", response_model=Dict[str, str])
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy"}
        
        @self.app.get("/status", response_model=SystemStatus)
        async def get_status(
            credentials: HTTPAuthorizationCredentials = Security(security)
        ):
            """Get system status."""
            await self._verify_api_key(credentials)
            
            if not self.kernel:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="System not initialized"
                )
            
            kernel_status = self.kernel.get_kernel_status()
            uptime = (datetime.now() - self.start_time).total_seconds()
            
            return SystemStatus(
                status="running" if kernel_status["running"] else "stopped",
                services=kernel_status["services"],
                uptime_seconds=uptime
            )
        
        @self.app.post("/chat", response_model=ChatResponse)
        async def chat(
            request: ChatRequest,
            credentials: HTTPAuthorizationCredentials = Security(security)
        ):
            """Chat with Hestia."""
            await self._verify_api_key(credentials)
            
            if not self.agent:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Agent not available"
                )
            
            # Create user input
            session_id = request.session_id or str(uuid4())
            
            user_input = UserInput(
                text=request.message,
                session_id=session_id,
                user_id=request.user_id,
                metadata=request.metadata
            )
            
            # Process input
            start_time = datetime.now()
            response = await self.agent.process_input(user_input)
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Create API response
            api_response = ChatResponse(
                response_id=response.response_id,
                message=response.text,
                session_id=session_id,
                timestamp=response.timestamp,
                processing_time_ms=processing_time,
                memory_proposals=len(response.memory_proposals),
                actions_executed=response.actions_executed
            )
            
            logger.info(
                "API chat request processed",
                session_id=session_id,
                processing_time_ms=processing_time
            )
            
            return api_response
        
        @self.app.get("/memories")
        async def get_memories(
            category: Optional[str] = None,
            limit: int = 100,
            credentials: HTTPAuthorizationCredentials = Security(security)
        ):
            """Get memories."""
            await self._verify_api_key(credentials)
            
            # TODO: Implement memory retrieval
            return {"memories": [], "count": 0}
        
        @self.app.post("/ingest")
        async def ingest_document(
            file: UploadFile,
            credentials: HTTPAuthorizationCredentials = Security(security)
        ):
            """Ingest a document."""
            await self._verify_api_key(credentials)
            
            # TODO: Implement document ingestion
            return {"status": "not implemented"}
    
    async def _verify_api_key(self, credentials: HTTPAuthorizationCredentials):
        """Verify API key."""
        if credentials.credentials != API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
    
    async def initialize(self):
        """Initialize API services."""
        try:
            # Create kernel
            config = KernelConfig(
                data_dir="./data",
                log_level="INFO",
                enable_audit=True
            )
            
            self.kernel = HearthKernel(config)
            
            # Initialize and register services
            self.agent = HestiaAgent()
            
            # TODO: Initialize other services
            from ...mnemosyne.memory_store import MemoryStore
            memory = MemoryStore("./data/memory.db")
            
            await self.kernel.register_service(memory)
            await self.kernel.register_service(self.agent)
            
            # Start kernel
            await self.kernel.start()
            
            logger.info("HEARTH API started")
            
        except Exception as e:
            logger.error("Failed to initialize API", error=str(e))
            raise
    
    async def shutdown(self):
        """Shutdown API services."""
        if self.kernel:
            await self.kernel.shutdown()
        
        logger.info("HEARTH API shutdown")


# Create application instance
app = HearthAPI().app


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )