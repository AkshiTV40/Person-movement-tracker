import React from 'react';

const EXERCISES = [
  { id: 'squat', name: 'Squat', icon: '🏋️', description: 'Lower body exercise' },
  { id: 'pushup', name: 'Push-up', icon: '💪', description: 'Upper body exercise' },
  { id: 'lunge', name: 'Lunge', icon: '🚶', description: 'Leg exercise' },
];

function ExerciseSelector({ selectedExercise, onExerciseChange, isTracking, onStartTracking, onStopTracking }) {
  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Select Exercise</h3>
      
      {/* Exercise Cards */}
      <div className="space-y-3 mb-6">
        {EXERCISES.map((exercise) => (
          <button
            key={exercise.id}
            onClick={() => onExerciseChange(exercise.id)}
            className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
              selectedExercise === exercise.id
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center">
              <span className="text-2xl mr-3">{exercise.icon}</span>
              <div>
                <div className="font-medium text-gray-900">{exercise.name}</div>
                <div className="text-sm text-gray-500">{exercise.description}</div>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Control Buttons */}
      <div className="flex space-x-3">
        {!isTracking ? (
          <button
            onClick={onStartTracking}
            className="flex-1 bg-primary-600 text-white px-4 py-3 rounded-lg font-medium hover:bg-primary-700 transition-colors flex items-center justify-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Start Tracking
          </button>
        ) : (
          <button
            onClick={onStopTracking}
            className="flex-1 bg-red-600 text-white px-4 py-3 rounded-lg font-medium hover:bg-red-700 transition-colors flex items-center justify-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
            </svg>
            Stop Tracking
          </button>
        )}
      </div>

      {/* Tips */}
      <div className="mt-4 p-3 bg-blue-50 rounded-lg">
        <h4 className="text-sm font-medium text-blue-900 mb-2">Tips for Best Results</h4>
        <ul className="text-xs text-blue-800 space-y-1">
          <li>• Stand in a well-lit area</li>
          <li>• Ensure your full body is visible</li>
          <li>• Keep the camera at eye level</li>
          <li>• Wear form-fitting clothing</li>
        </ul>
      </div>
    </div>
  );
}

export default ExerciseSelector;
