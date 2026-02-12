import React, { useState } from 'react';
import { motion } from 'framer-motion';
import CameraFeed from './components/CameraFeed';
import TrackingStats from './components/TrackingStats';
import Controls from './components/Controls';
import TrackList from './components/TrackList';
import ExerciseFeedback from './components/ExerciseFeedback';
import ExerciseSelector from './components/ExerciseSelector';
import YouTubeAnalyzer from './components/YouTubeAnalyzer';
import { useCamera } from './hooks/useCamera';
import { useTracking } from './hooks/useTracking';
import { useExerciseTracking } from './hooks/useExerciseTracking';

function App() {
  const [mode, setMode] = useState('tracking'); // 'tracking', 'exercise', or 'youtube'
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
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-purple-50">
      {/* Header */}
      <header className="glass-effect border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <motion.div 
            className="flex items-center justify-between"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="flex items-center space-x-4">
              <motion.div 
                className="w-12 h-12 bg-gradient-to-r from-primary-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg"
                whileHover={{ scale: 1.1, rotate: 5 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </motion.div>
              <div>
                <h1 className="text-2xl font-bold gradient-text">Person Movement Tracker</h1>
                <p className="text-sm text-gray-600 mt-1">
                  {mode === 'tracking' ? 'Real-time detection and tracking' : 
                   mode === 'exercise' ? 'Exercise form analysis' :
                   'YouTube video analysis'}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-6">
              {/* Mode Toggle */}
              <div className="flex bg-gray-100/50 backdrop-blur-sm rounded-xl p-1 border border-gray-200/50">
                {[
                  { id: 'tracking', name: 'Tracking' },
                  { id: 'exercise', name: 'Exercise' },
                  { id: 'youtube', name: 'YouTube' }
                ].map((m) => (
                  <motion.button
                    key={m.id}
                    onClick={() => handleModeChange(m.id)}
                    className={`px-6 py-3 rounded-lg text-sm font-semibold transition-all ${
                      mode === m.id
                        ? 'bg-white text-gray-900 shadow-lg'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                  >
                    {m.name}
                  </motion.button>
                ))}
              </div>
              {mode !== 'youtube' && (
                <motion.div 
                  className="flex items-center space-x-3"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
                >
                  <div className={`w-3 h-3 rounded-full ${isActive ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
                  <span className="text-sm font-medium text-gray-700">
                    {isActive ? 'Camera Active' : 'Camera Inactive'}
                  </span>
                </motion.div>
              )}
            </div>
          </motion.div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {mode === 'youtube' ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <YouTubeAnalyzer />
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Camera Feed */}
            <div className="lg:col-span-2">
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5 }}
              >
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
              </motion.div>
            </div>

            {/* Sidebar */}
            <div className="space-y-8">
              {mode === 'tracking' ? (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6, delay: 0.2 }}
                >
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
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6, delay: 0.2 }}
                >
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
                </motion.div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;