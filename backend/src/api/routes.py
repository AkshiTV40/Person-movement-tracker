from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from typing import List, Optional, Dict
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

try:
    from ..config import config
    from ..services.tracking_service import TrackingService
    from ..services.youtube_service import YouTubeService
    from ..services.video_analysis_service import VideoAnalysisService
    from ..models.detector_factory import ModelType
    from ..models.pose_estimator import MediaPipePoseDetector
    from ..models.exercise_analyzer import ExerciseAnalyzerFactory, ExerciseType
    from .schemas import (
        TrackingRequest, TrackingResponse, ModelInfo, 
        DeviceInfo, SessionStats, ExerciseTrackingRequest,
        ExerciseTrackingResponse
    )
except ImportError:
    from config import config
    from services.tracking_service import TrackingService
    from services.youtube_service import YouTubeService
    from services.video_analysis_service import VideoAnalysisService
    from models.detector_factory import ModelType
    from models.pose_estimator import MediaPipePoseDetector
    from models.exercise_analyzer import ExerciseAnalyzerFactory, ExerciseType
    from api.schemas import (
        TrackingRequest, TrackingResponse, ModelInfo, 
        DeviceInfo, SessionStats, ExerciseTrackingRequest,
        ExerciseTrackingResponse
    )

app = FastAPI(
    title="Person Movement Tracker API",
    description="Real-time person detection and tracking API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
tracking_service = TrackingService()
exercise_tracking_service = None
youtube_service = YouTubeService()
video_analysis_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await tracking_service.initialize()
    global exercise_tracking_service, video_analysis_service
    from ..services.exercise_tracking_service import ExerciseTrackingService
    exercise_tracking_service = ExerciseTrackingService()
    await exercise_tracking_service.initialize()
    
    # Initialize video analysis service
    pose_detector = MediaPipePoseDetector()
    analyzer = ExerciseAnalyzerFactory.create(ExerciseType.SQUAT)
    video_analysis_service = VideoAnalysisService(pose_detector, analyzer)

@app.get("/", response_class=HTMLResponse)
async def root():
    """API root with documentation"""
    return """
    <html>
        <head>
            <title>Person Movement Tracker API</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <h1>Person Movement Tracker API</h1>
            <p>Real-time person detection and tracking service</p>
            <div class="endpoint">
                <h3>POST /api/track</h3>
                <p>Process frame with person detection and tracking</p>
            </div>
            <div class="endpoint">
                <h3>WS /ws/track</h3>
                <p>WebSocket for real-time tracking</p>
            </div>
            <div class="endpoint">
                <h3>GET /api/models</h3>
                <p>Get available models</p>
            </div>
        </body>
    </html>
    """

@app.post("/api/track", response_model=TrackingResponse)
async def track_persons(request: TrackingRequest):
    """Process image/video frame for person tracking"""
    result = await tracking_service.process_frame(
        image_data=request.image,
        session_id=request.session_id,
        model_type=request.model_type,
        enable_tracking=request.enable_tracking
    )
    
    if result['success']:
        return TrackingResponse(
            success=True,
            image=result['image'],
            detections=result['detections'],
            inference_time=result['inference_time'],
            track_count=result['track_count'],
            model=result['model']
        )
    else:
        return TrackingResponse(
            success=False,
            error=result['error']
        )

@app.post("/api/track/file")
async def track_from_file(
    file: UploadFile = File(...),
    model_type: Optional[str] = Form("yolov8"),
    enable_tracking: bool = Form(True)
):
    """Upload image file for tracking"""
    try:
        # Read file
        contents = await file.read()
        
        # Convert to base64
        import base64
        image_data = base64.b64encode(contents).decode('utf-8')
        
        # Process
        result = await tracking_service.process_frame(
            image_data=image_data,
            session_id="file_upload",
            model_type=ModelType(model_type) if model_type else None,
            enable_tracking=enable_tracking
        )
        
        return JSONResponse(content=result)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )

@app.get("/api/models", response_model=List[ModelInfo])
async def get_models():
    """Get available models"""
    from ..models.detector_factory import DetectorFactory
    
    models = DetectorFactory.get_available_models()
    
    return [
        ModelInfo(
            name=model_type.value,
            description=info['description'],
            supports_tracking=info['supports_tracking']
        )
        for model_type, info in models.items()
    ]

@app.get("/api/device", response_model=DeviceInfo)
async def get_device_info():
    """Get device information and capabilities"""
    import torch
    
    device_info = {
        'device': str(config.device),
        'cuda_available': torch.cuda.is_available(),
        'mps_available': hasattr(torch.backends, 'mps') and torch.backends.mps.is_available(),
        'cpu_count': torch.get_num_threads()
    }
    
    if torch.cuda.is_available():
        device_info['cuda_device_count'] = torch.cuda.device_count()
        device_info['cuda_device_name'] = torch.cuda.get_device_name(0)
    
    return DeviceInfo(**device_info)

@app.websocket("/ws/track")
async def websocket_track(websocket: WebSocket):
    """WebSocket for real-time tracking"""
    await websocket.accept()
    
    session_id = f"ws_{websocket.client.host}"
    
    try:
        while True:
            # Receive frame
            data = await websocket.receive_json()
            image_data = data.get('image')
            
            if not image_data:
                continue
            
            # Process frame
            result = await tracking_service.process_frame(
                image_data=image_data,
                session_id=session_id,
                enable_tracking=True
            )
            
            # Send result
            await websocket.send_json(result)
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        await websocket.send_json({'error': str(e)})

@app.get("/api/session/{session_id}/stats", response_model=SessionStats)
async def get_session_stats(session_id: str):
    """Get session statistics"""
    # This would typically come from a database
    return SessionStats(
        session_id=session_id,
        frame_count=100,
        average_inference_time=0.15,
        total_tracks=5
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "person-tracker"}

# Exercise Tracking Endpoints

@app.post("/api/exercise/track", response_model=ExerciseTrackingResponse)
async def track_exercise(request: ExerciseTrackingRequest):
    """Process frame for exercise form analysis"""
    if not exercise_tracking_service:
        return ExerciseTrackingResponse(
            success=False,
            error="Exercise tracking service not initialized"
        )
    
    result = await exercise_tracking_service.process_frame(
        image_data=request.image,
        session_id=request.session_id,
        exercise_type=request.exercise_type,
        enable_tracking=request.enable_tracking
    )
    
    if result['success']:
        return ExerciseTrackingResponse(
            success=True,
            image=result.get('image'),
            pose_data=result.get('pose_data'),
            analysis=result.get('analysis'),
            inference_time=result['inference_time']
        )
    else:
        return ExerciseTrackingResponse(
            success=False,
            error=result.get('error')
        )

@app.post("/api/exercise/track/file")
async def track_exercise_from_file(
    file: UploadFile = File(...),
    exercise_type: str = Form("squat"),
    enable_tracking: bool = Form(True)
):
    """Upload image file for exercise tracking"""
    if not exercise_tracking_service:
        return JSONResponse(
            status_code=500,
            content={'error': 'Exercise tracking service not initialized'}
        )
    
    try:
        # Read file
        contents = await file.read()
        
        # Convert to base64
        import base64
        image_data = base64.b64encode(contents).decode('utf-8')
        
        # Process
        result = await exercise_tracking_service.process_frame(
            image_data=image_data,
            session_id="file_upload",
            exercise_type=ExerciseType(exercise_type),
            enable_tracking=enable_tracking
        )
        
        return JSONResponse(content=result)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )

@app.get("/api/exercise/types")
async def get_exercise_types():
    """Get supported exercise types"""
    if not exercise_tracking_service:
        return {"exercises": []}
    
    exercises = exercise_tracking_service.get_supported_exercises()
    
    return {
        "exercises": [
            {
                "type": ex.value,
                "name": ex.value.replace("_", " ").title()
            }
            for ex in exercises
        ]
    }

@app.post("/api/exercise/reset")
async def reset_exercise_tracking(exercise_type: str):
    """Reset exercise tracking for a specific exercise"""
    if not exercise_tracking_service:
        return {"success": False, "error": "Service not initialized"}
    
    try:
        ex_type = ExerciseType(exercise_type)
        exercise_tracking_service.reset_analyzer(ex_type)
        return {"success": True, "message": f"Reset tracking for {exercise_type}"}
    except ValueError:
        return {"success": False, "error": f"Invalid exercise type: {exercise_type}"}

@app.websocket("/ws/exercise/track")
async def websocket_exercise_track(websocket: WebSocket):
    """WebSocket for real-time exercise tracking"""
    await websocket.accept()
    
    session_id = f"ws_exercise_{websocket.client.host}"
    current_exercise_type = None
    
    try:
        while True:
            # Receive frame
            data = await websocket.receive_json()
            image_data = data.get('image')
            exercise_type_str = data.get('exercise_type', 'squat')
            
            if not image_data:
                continue
            
            # Reset if exercise type changed
            if current_exercise_type != exercise_type_str:
                current_exercise_type = exercise_type_str
                try:
                    exercise_tracking_service.reset_analyzer(ExerciseType(exercise_type_str))
                except ValueError:
                    pass
            
            # Process frame
            result = await exercise_tracking_service.process_frame(
                image_data=image_data,
                session_id=session_id,
                exercise_type=ExerciseType(exercise_type_str),
                enable_tracking=True
            )
            
            # Send result
            await websocket.send_json(result)
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        await websocket.send_json({'error': str(e)})