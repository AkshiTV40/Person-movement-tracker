"""
Exercise Form Analyzer
Analyzes exercise form using pose landmarks and provides feedback
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import numpy as np

from .pose_estimator import PoseLandmarks, MediaPipePoseDetector


class ExerciseType(Enum):
    """Supported exercise types"""
    SQUAT = "squat"
    PUSHUP = "pushup"
    LUNGE = "lunge"
    PLANK = "plank"
    DEADLIFT = "deadlift"
    BENCH_PRESS = "bench_press"
    OVERHEAD_PRESS = "overhead_press"
    BICEP_CURL = "bicep_curl"
    TRICEP_EXTENSION = "tricep_extension"
    JUMPING_JACK = "jumping_jack"


class FormIssue:
    """Represents a form issue detected during exercise"""
    
    def __init__(self, severity: str, message: str, suggestion: str, 
                 affected_landmarks: Optional[List[str]] = None):
        self.severity = severity  # "critical", "warning", "info"
        self.message = message
        self.suggestion = suggestion
        self.affected_landmarks = affected_landmarks or []
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "message": self.message,
            "suggestion": self.suggestion,
            "affected_landmarks": self.affected_landmarks,
            "timestamp": self.timestamp
        }


class ExerciseState(Enum):
    """Exercise state during movement"""
    START = "start"
    MOVING = "moving"
    END = "end"
    HOLDING = "holding"


class RepCounter:
    """Counts repetitions for exercises"""
    
    def __init__(self, exercise_type: ExerciseType):
        self.exercise_type = exercise_type
        self.count = 0
        self.state = ExerciseState.START
        self.last_state_change = time.time()
        self.hold_start_time = None
    
    def update(self, state: ExerciseState) -> int:
        """
        Update state and count reps
        
        Args:
            state: New exercise state
            
        Returns:
            Current rep count
        """
        if state != self.state:
            # State transition
            if self.state == ExerciseState.START and state == ExerciseState.END:
                self.count += 1
            elif self.state == ExerciseState.END and state == ExerciseState.START:
                # Ready for next rep
                pass
            
            self.state = state
            self.last_state_change = time.time()
        
        return self.count
    
    def reset(self) -> None:
        """Reset the counter"""
        self.count = 0
        self.state = ExerciseState.START
        self.last_state_change = time.time()
        self.hold_start_time = None


class ExerciseAnalyzer:
    """Base class for exercise form analysis"""
    
    def __init__(self, pose_detector: MediaPipePoseDetector):
        self.pose_detector = pose_detector
        self.rep_counter = None
        self.form_issues: List[FormIssue] = []
        self.current_feedback: List[str] = []
    
    def analyze(self, pose_landmarks: PoseLandmarks, frame: np.ndarray) -> Dict[str, Any]:
        """
        Analyze exercise form
        
        Args:
            pose_landmarks: Detected pose landmarks
            frame: Current frame for visualization
            
        Returns:
            Analysis results with feedback
        """
        raise NotImplementedError("Subclasses must implement analyze method")
    
    def reset(self) -> None:
        """Reset analyzer state"""
        if self.rep_counter:
            self.rep_counter.reset()
        self.form_issues = []
        self.current_feedback = []
    
    def _add_form_issue(self, severity: str, message: str, suggestion: str,
                       affected_landmarks: Optional[List[str]] = None) -> None:
        """Add a form issue to the list"""
        issue = FormIssue(severity, message, suggestion, affected_landmarks)
        self.form_issues.append(issue)
    
    def _get_recent_issues(self, max_age: float = 2.0) -> List[FormIssue]:
        """Get recent form issues"""
        now = time.time()
        return [issue for issue in self.form_issues 
                if now - issue.timestamp < max_age]


class SquatAnalyzer(ExerciseAnalyzer):
    """Analyzer for squat exercise form"""
    
    def __init__(self, pose_detector: MediaPipePoseDetector):
        super().__init__(pose_detector)
        self.exercise_type = ExerciseType.SQUAT
        self.rep_counter = RepCounter(ExerciseType.SQUAT)
        
        # Squat parameters
        self.min_knee_angle = 70.0  # Minimum knee angle for good depth
        self.max_knee_angle = 170.0  # Maximum knee angle for standing
        self.min_hip_angle = 70.0  # Minimum hip angle for good depth
        self.max_hip_angle = 170.0  # Maximum hip angle for standing
    
    def analyze(self, pose_landmarks: PoseLandmarks, frame: np.ndarray) -> Dict[str, Any]:
        """
        Analyze squat form
        
        Args:
            pose_landmarks: Detected pose landmarks
            frame: Current frame
            
        Returns:
            Analysis results
        """
        # Get key angles
        left_knee_angle = self.pose_detector.get_angle(
            pose_landmarks, "left_hip", "left_knee", "left_ankle"
        )
        right_knee_angle = self.pose_detector.get_angle(
            pose_landmarks, "right_hip", "right_knee", "right_ankle"
        )
        left_hip_angle = self.pose_detector.get_angle(
            pose_landmarks, "left_shoulder", "left_hip", "left_knee"
        )
        right_hip_angle = self.pose_detector.get_angle(
            pose_landmarks, "right_shoulder", "right_hip", "right_knee"
        )
        
        # Average angles
        knee_angle = (left_knee_angle + right_knee_angle) / 2
        hip_angle = (left_hip_angle + right_hip_angle) / 2
        
        # Determine exercise state
        state = self._determine_state(knee_angle, hip_angle)
        
        # Update rep counter
        rep_count = self.rep_counter.update(state)
        
        # Analyze form
        self._analyze_form(pose_landmarks, knee_angle, hip_angle, 
                          left_knee_angle, right_knee_angle,
                          left_hip_angle, right_hip_angle)
        
        # Get recent issues
        recent_issues = self._get_recent_issues()
        
        return {
            "exercise": self.exercise_type.value,
            "rep_count": rep_count,
            "state": state.value,
            "angles": {
                "knee": knee_angle,
                "hip": hip_angle,
                "left_knee": left_knee_angle,
                "right_knee": right_knee_angle,
                "left_hip": left_hip_angle,
                "right_hip": right_hip_angle
            },
            "form_issues": [issue.to_dict() for issue in recent_issues],
            "feedback": self._generate_feedback(recent_issues)
        }
    
    def _determine_state(self, knee_angle: float, hip_angle: float) -> ExerciseState:
        """Determine exercise state based on angles"""
        if knee_angle > self.max_knee_angle and hip_angle > self.max_hip_angle:
            return ExerciseState.START
        elif knee_angle < self.min_knee_angle and hip_angle < self.min_hip_angle:
            return ExerciseState.END
        else:
            return ExerciseState.MOVING
    
    def _analyze_form(self, pose_landmarks: PoseLandmarks, knee_angle: float, hip_angle: float,
                      left_knee_angle: float, right_knee_angle: float,
                      left_hip_angle: float, right_hip_angle: float) -> None:
        """Analyze squat form and detect issues"""
        
        # Check depth
        if knee_angle > 100 and hip_angle > 100:
            self._add_form_issue(
                "warning",
                "Squat depth is insufficient",
                "Try to go lower - aim for thighs parallel to the ground",
                ["left_knee", "right_knee", "left_hip", "right_hip"]
            )
        
        # Check knee alignment
        knee_diff = abs(left_knee_angle - right_knee_angle)
        if knee_diff > 20:
            self._add_form_issue(
                "warning",
                "Knees are not tracking evenly",
                "Focus on keeping both knees moving at the same pace",
                ["left_knee", "right_knee"]
            )
        
        # Check hip alignment
        hip_diff = abs(left_hip_angle - right_hip_angle)
        if hip_diff > 20:
            self._add_form_issue(
                "warning",
                "Hips are not level",
                "Keep your hips level throughout the movement",
                ["left_hip", "right_hip"]
            )
        
        # Check for knee valgus (knees caving in)
        keypoints = self.pose_detector.get_keypoints(pose_landmarks)
        if "left_knee" in keypoints and "left_ankle" in keypoints:
            left_knee_x = keypoints["left_knee"][0]
            left_ankle_x = keypoints["left_ankle"][0]
            if left_knee_x < left_ankle_x - 0.05:
                self._add_form_issue(
                    "critical",
                    "Left knee is caving inward (valgus)",
                    "Push your knees out to track over your toes",
                    ["left_knee", "left_ankle"]
                )
        
        if "right_knee" in keypoints and "right_ankle" in keypoints:
            right_knee_x = keypoints["right_knee"][0]
            right_ankle_x = keypoints["right_ankle"][0]
            if right_knee_x > right_ankle_x + 0.05:
                self._add_form_issue(
                    "critical",
                    "Right knee is caving inward (valgus)",
                    "Push your knees out to track over your toes",
                    ["right_knee", "right_ankle"]
                )
        
        # Check for excessive forward lean
        if hip_angle < 60:
            self._add_form_issue(
                "warning",
                "Excessive forward lean",
                "Keep your chest up and maintain a more upright torso",
                ["left_shoulder", "left_hip"]
            )
    
    def _generate_feedback(self, issues: List[FormIssue]) -> List[str]:
        """Generate feedback messages"""
        feedback = []
        
        critical_issues = [i for i in issues if i.severity == "critical"]
        warning_issues = [i for i in issues if i.severity == "warning"]
        
        if critical_issues:
            feedback.append("⚠️ CRITICAL: Fix your form immediately!")
            for issue in critical_issues[:2]:
                feedback.append(f"• {issue.message}")
        
        if warning_issues:
            feedback.append("⚡ Form improvements needed:")
            for issue in warning_issues[:2]:
                feedback.append(f"• {issue.message}")
        
        if not issues:
            feedback.append("✅ Great form! Keep it up!")
        
        return feedback


class PushupAnalyzer(ExerciseAnalyzer):
    """Analyzer for push-up exercise form"""
    
    def __init__(self, pose_detector: MediaPipePoseDetector):
        super().__init__(pose_detector)
        self.exercise_type = ExerciseType.PUSHUP
        self.rep_counter = RepCounter(ExerciseType.PUSHUP)
        
        # Push-up parameters
        self.min_elbow_angle = 90.0  # Minimum elbow angle for good depth
        self.max_elbow_angle = 170.0  # Maximum elbow angle for extended position
    
    def analyze(self, pose_landmarks: PoseLandmarks, frame: np.ndarray) -> Dict[str, Any]:
        """
        Analyze push-up form
        
        Args:
            pose_landmarks: Detected pose landmarks
            frame: Current frame
            
        Returns:
            Analysis results
        """
        # Get key angles
        left_elbow_angle = self.pose_detector.get_angle(
            pose_landmarks, "left_shoulder", "left_elbow", "left_wrist"
        )
        right_elbow_angle = self.pose_detector.get_angle(
            pose_landmarks, "right_shoulder", "right_elbow", "right_wrist"
        )
        
        # Average elbow angle
        elbow_angle = (left_elbow_angle + right_elbow_angle) / 2
        
        # Determine exercise state
        state = self._determine_state(elbow_angle)
        
        # Update rep counter
        rep_count = self.rep_counter.update(state)
        
        # Analyze form
        self._analyze_form(pose_landmarks, elbow_angle, 
                          left_elbow_angle, right_elbow_angle)
        
        # Get recent issues
        recent_issues = self._get_recent_issues()
        
        return {
            "exercise": self.exercise_type.value,
            "rep_count": rep_count,
            "state": state.value,
            "angles": {
                "elbow": elbow_angle,
                "left_elbow": left_elbow_angle,
                "right_elbow": right_elbow_angle
            },
            "form_issues": [issue.to_dict() for issue in recent_issues],
            "feedback": self._generate_feedback(recent_issues)
        }
    
    def _determine_state(self, elbow_angle: float) -> ExerciseState:
        """Determine exercise state based on elbow angle"""
        if elbow_angle > self.max_elbow_angle:
            return ExerciseState.START
        elif elbow_angle < self.min_elbow_angle:
            return ExerciseState.END
        else:
            return ExerciseState.MOVING
    
    def _analyze_form(self, pose_landmarks: PoseLandmarks, elbow_angle: float,
                      left_elbow_angle: float, right_elbow_angle: float) -> None:
        """Analyze push-up form and detect issues"""
        
        # Check depth
        if elbow_angle > 110:
            self._add_form_issue(
                "warning",
                "Push-up depth is insufficient",
                "Lower your chest closer to the ground",
                ["left_elbow", "right_elbow"]
            )
        
        # Check elbow alignment
        elbow_diff = abs(left_elbow_angle - right_elbow_angle)
        if elbow_diff > 20:
            self._add_form_issue(
                "warning",
                "Arms are not moving evenly",
                "Focus on keeping both arms moving at the same pace",
                ["left_elbow", "right_elbow"]
            )
        
        # Check for flaring elbows
        keypoints = self.pose_detector.get_keypoints(pose_landmarks)
        if "left_shoulder" in keypoints and "left_elbow" in keypoints and "left_wrist" in keypoints:
            shoulder_x = keypoints["left_shoulder"][0]
            elbow_x = keypoints["left_elbow"][0]
            wrist_x = keypoints["left_wrist"][0]
            
            # Check if elbow is flaring out
            if abs(elbow_x - shoulder_x) > 0.15:
                self._add_form_issue(
                    "warning",
                    "Left elbow is flaring out",
                    "Keep elbows at about 45 degrees from your body",
                    ["left_shoulder", "left_elbow", "left_wrist"]
                )
        
        if "right_shoulder" in keypoints and "right_elbow" in keypoints and "right_wrist" in keypoints:
            shoulder_x = keypoints["right_shoulder"][0]
            elbow_x = keypoints["right_elbow"][0]
            wrist_x = keypoints["right_wrist"][0]
            
            if abs(elbow_x - shoulder_x) > 0.15:
                self._add_form_issue(
                    "warning",
                    "Right elbow is flaring out",
                    "Keep elbows at about 45 degrees from your body",
                    ["right_shoulder", "right_elbow", "right_wrist"]
                )
        
        # Check for sagging hips
        if "left_shoulder" in keypoints and "left_hip" in keypoints:
            shoulder_y = keypoints["left_shoulder"][1]
            hip_y = keypoints["left_hip"][1]
            
            if hip_y > shoulder_y + 0.1:
                self._add_form_issue(
                    "critical",
                    "Hips are sagging",
                    "Engage your core to keep your body in a straight line",
                    ["left_shoulder", "left_hip"]
                )
    
    def _generate_feedback(self, issues: List[FormIssue]) -> List[str]:
        """Generate feedback messages"""
        feedback = []
        
        critical_issues = [i for i in issues if i.severity == "critical"]
        warning_issues = [i for i in issues if i.severity == "warning"]
        
        if critical_issues:
            feedback.append("⚠️ CRITICAL: Fix your form immediately!")
            for issue in critical_issues[:2]:
                feedback.append(f"• {issue.message}")
        
        if warning_issues:
            feedback.append("⚡ Form improvements needed:")
            for issue in warning_issues[:2]:
                feedback.append(f"• {issue.message}")
        
        if not issues:
            feedback.append("✅ Great form! Keep it up!")
        
        return feedback


class LungeAnalyzer(ExerciseAnalyzer):
    """Analyzer for lunge exercise form"""
    
    def __init__(self, pose_detector: MediaPipePoseDetector):
        super().__init__(pose_detector)
        self.exercise_type = ExerciseType.LUNGE
        self.rep_counter = RepCounter(ExerciseType.LUNGE)
        
        # Lunge parameters
        self.min_front_knee_angle = 80.0
        self.max_front_knee_angle = 170.0
        self.min_back_knee_angle = 140.0
    
    def analyze(self, pose_landmarks: PoseLandmarks, frame: np.ndarray) -> Dict[str, Any]:
        """
        Analyze lunge form
        
        Args:
            pose_landmarks: Detected pose landmarks
            frame: Current frame
            
        Returns:
            Analysis results
        """
        # Determine which leg is forward
        keypoints = self.pose_detector.get_keypoints(pose_landmarks)
        
        left_knee_y = keypoints.get("left_knee", (0, 0))[1]
        right_knee_y = keypoints.get("right_knee", (0, 0))[1]
        
        # Assume lower knee is the front knee
        if left_knee_y < right_knee_y:
            front_knee_angle = self.pose_detector.get_angle(
                pose_landmarks, "left_hip", "left_knee", "left_ankle"
            )
            back_knee_angle = self.pose_detector.get_angle(
                pose_landmarks, "right_hip", "right_knee", "right_ankle"
            )
            front_leg = "left"
        else:
            front_knee_angle = self.pose_detector.get_angle(
                pose_landmarks, "right_hip", "right_knee", "right_ankle"
            )
            back_knee_angle = self.pose_detector.get_angle(
                pose_landmarks, "left_hip", "left_knee", "left_ankle"
            )
            front_leg = "right"
        
        # Determine exercise state
        state = self._determine_state(front_knee_angle)
        
        # Update rep counter
        rep_count = self.rep_counter.update(state)
        
        # Analyze form
        self._analyze_form(pose_landmarks, front_knee_angle, back_knee_angle, front_leg)
        
        # Get recent issues
        recent_issues = self._get_recent_issues()
        
        return {
            "exercise": self.exercise_type.value,
            "rep_count": rep_count,
            "state": state.value,
            "front_leg": front_leg,
            "angles": {
                "front_knee": front_knee_angle,
                "back_knee": back_knee_angle
            },
            "form_issues": [issue.to_dict() for issue in recent_issues],
            "feedback": self._generate_feedback(recent_issues)
        }
    
    def _determine_state(self, front_knee_angle: float) -> ExerciseState:
        """Determine exercise state based on front knee angle"""
        if front_knee_angle > self.max_front_knee_angle:
            return ExerciseState.START
        elif front_knee_angle < self.min_front_knee_angle:
            return ExerciseState.END
        else:
            return ExerciseState.MOVING
    
    def _analyze_form(self, pose_landmarks: PoseLandmarks, front_knee_angle: float,
                      back_knee_angle: float, front_leg: str) -> None:
        """Analyze lunge form and detect issues"""
        
        # Check front knee depth
        if front_knee_angle > 100:
            self._add_form_issue(
                "warning",
                "Lunge depth is insufficient",
                "Step deeper into the lunge",
                [f"{front_leg}_knee"]
            )
        
        # Check front knee alignment
        keypoints = self.pose_detector.get_keypoints(pose_landmarks)
        front_knee = keypoints.get(f"{front_leg}_knee", (0, 0))
        front_ankle = keypoints.get(f"{front_leg}_ankle", (0, 0))
        
        # Check if front knee is going past toes
        if front_knee[1] > front_ankle[1] + 0.05:
            self._add_form_issue(
                "warning",
                "Front knee is going too far past toes",
                "Keep your front knee above your ankle",
                [f"{front_leg}_knee", f"{front_leg}_ankle"]
            )
        
        # Check back knee
        if back_knee_angle > 160:
            self._add_form_issue(
                "warning",
                "Back knee is not bending enough",
                "Bend your back knee more for better stretch",
                [f"{'right' if front_leg == 'left' else 'left'}_knee"]
            )
    
    def _generate_feedback(self, issues: List[FormIssue]) -> List[str]:
        """Generate feedback messages"""
        feedback = []
        
        warning_issues = [i for i in issues if i.severity == "warning"]
        
        if warning_issues:
            feedback.append("⚡ Form improvements needed:")
            for issue in warning_issues[:2]:
                feedback.append(f"• {issue.message}")
        
        if not issues:
            feedback.append("✅ Great form! Keep it up!")
        
        return feedback


class ExerciseAnalyzerFactory:
    """Factory for creating exercise analyzers"""
    
    @staticmethod
    def create_analyzer(exercise_type: ExerciseType, 
                       pose_detector: MediaPipePoseDetector) -> ExerciseAnalyzer:
        """
        Create an exercise analyzer for the given type
        
        Args:
            exercise_type: Type of exercise
            pose_detector: Pose detector instance
            
        Returns:
            Exercise analyzer instance
        """
        analyzers = {
            ExerciseType.SQUAT: SquatAnalyzer,
            ExerciseType.PUSHUP: PushupAnalyzer,
            ExerciseType.LUNGE: LungeAnalyzer,
        }
        
        analyzer_class = analyzers.get(exercise_type)
        if analyzer_class:
            return analyzer_class(pose_detector)
        else:
            raise ValueError(f"Unsupported exercise type: {exercise_type}")
