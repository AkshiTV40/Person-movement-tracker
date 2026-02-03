import React, { useState } from 'react';
import CameraFeed from './components/CameraFeed';
import TrackingStats from './components/TrackingStats';
import Controls from './components/Controls';
import TrackList from './components/TrackList';
import ExerciseFeedback from './components/ExerciseFeedback';
import ExerciseSelector from './components/ExerciseSelector';
import { useCamera } from './hooks/useCamera';
import { useTracking } from './hooks/useTracking';
import { useExerciseTracking } from './hooks/useExerciseTracking';

function App() {
  const [mode, setMode] = useState('tracking'); // 'tracking' or 'exercise'
  const [isTracking, setIsTracking] = useState(false);
  const [selectedModel, setSelectedModel] = useState('yolov8');
  const [selectedExercise, setSelectedExercise] = useState('squat');
  const [stats, setStats] = useState({
    frameCount: 0,
    inferenceTime: 0,
    trackCount: 0,
    fps: 0
  });
  const [tracks, setTracks] = useState([]);
  const [exerciseAnalysis, setExerciseAnalysis] = useState(null);

  const { videoRef, canvasRef, startCamera, stopCamera, isActive } = useCamera();
  const { processFrame, isProcessing } = useTracking();
  const { processExerciseFrame, isExerciseProcessing, resetExercise } = useExerciseTracking();

  const handleStartTracking = async () => {
    await startCamera();
    setIsTracking(true);
  };

  const handleStopTracking = () => {
    stopCamera();
    setIsTracking(false);
  };

  const handleModelChange = (model) => {
    setSelectedModel(model);
  };

  const handleExerciseChange = (exercise) => {
    setSelectedExercise(exercise);
    resetExercise();
  };

  const handleModeChange = (newMode) => {
    setMode(newMode);
    if (isTracking) {
      handleStopTracking();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Person Movement Tracker</h1>
                <p className="text-sm text-gray-500">
                  {mode === 'tracking' ? 'Real-time detection and tracking' : 'Exercise form analysis'}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* Mode Toggle */}
              <div className="flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => handleModeChange('tracking')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    mode === 'tracking'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Tracking
                </button>
                <button
                  onClick={() => handleModeChange('exercise')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    mode === 'exercise'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Exercise
                </button>
              </div>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
                <span className="text-sm text-gray-600">
                  {isActive ? 'Camera Active' : 'Camera Inactive'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Camera Feed */}
          <div className="lg:col-span-2">
            <CameraFeed
              videoRef={videoRef}
              canvasRef={canvasRef}
              isActive={isActive}
              isProcessing={mode === 'tracking' ? isProcessing : isExerciseProcessing}
              mode={mode}
              onFrameCapture={mode === 'exercise' ? (frame) => {
                processExerciseFrame(frame, selectedExercise, setExerciseAnalysis);
              } : null}
            />
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {mode === 'tracking' ? (
              <>
                {/* Controls */}
                <Controls
                  isTracking={isTracking}
                  selectedModel={selectedModel}
                  onStartTracking={handleStartTracking}
                  onStopTracking={handleStopTracking}
                  onModelChange={handleModelChange}
                />

                {/* Stats */}
                <TrackingStats stats={stats} />

                {/* Track List */}
                <TrackList tracks={tracks} />
              </>
            ) : (
              <>
                {/* Exercise Selector */}
                <ExerciseSelector
                  selectedExercise={selectedExercise}
                  onExerciseChange={handleExerciseChange}
                  isTracking={isTracking}
                  onStartTracking={handleStartTracking}
                  onStopTracking={handleStopTracking}
                />

                {/* Exercise Feedback */}
                <ExerciseFeedback analysis={exerciseAnalysis} />
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;