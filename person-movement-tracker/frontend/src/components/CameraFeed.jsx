import React from 'react';

const CameraFeed = ({ videoRef, canvasRef, isActive, isProcessing }) => {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Camera Feed</h2>
        <div className="flex items-center space-x-2">
          {isProcessing && (
            <span className="text-sm text-primary-600 animate-pulse">Processing...</span>
          )}
          <div className={`w-3 h-3 rounded-full ${isActive ? 'bg-green-500' : 'bg-red-500'}`} />
        </div>
      </div>

      <div className="relative bg-black rounded-lg overflow-hidden" style={{ aspectRatio: '16/9' }}>
        {/* Video Element */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`absolute inset-0 w-full h-full object-cover ${isActive ? 'block' : 'hidden'}`}
        />

        {/* Canvas for Drawing Detections */}
        <canvas
          ref={canvasRef}
          className={`absolute inset-0 w-full h-full ${isActive ? 'block' : 'hidden'}`}
        />

        {/* Placeholder when camera is off */}
        {!isActive && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="text-center">
              <svg className="w-16 h-16 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <p className="text-gray-400 text-lg">Camera is off</p>
              <p className="text-gray-500 text-sm mt-2">Click "Start Tracking" to begin</p>
            </div>
          </div>
        )}

        {/* Processing Indicator */}
        {isProcessing && (
          <div className="absolute top-4 right-4 bg-black/50 backdrop-blur-sm rounded-lg px-3 py-2">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
              <span className="text-white text-sm font-medium">AI Processing</span>
            </div>
          </div>
        )}
      </div>

      {/* Camera Info */}
      {isActive && (
        <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
          <div className="bg-gray-50 rounded-lg p-3">
            <span className="text-gray-500">Resolution</span>
            <p className="font-medium text-gray-900">1280 × 720</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <span className="text-gray-500">Frame Rate</span>
            <p className="font-medium text-gray-900">30 FPS</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <span className="text-gray-500">Latency</span>
            <p className="font-medium text-gray-900">{'< 100ms'}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default CameraFeed;