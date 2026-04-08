import logging
import os
import re
import numpy as np
from typing import Optional, Dict, Any, List

try:
    from ..config import config
    from ..models.exercise_analyzer import ExerciseType
except ImportError:
    from config import config
    from models.exercise_analyzer import ExerciseType

logger = logging.getLogger(__name__)


class GuidanceService:
    """Generate natural-language guidance and comparison suggestions using Qwen2.5-Omni"""

    def __init__(self, model_name: str = "Qwen/Qwen2.5-Omni-7B"):
        self.model_name = model_name
        self.model = None
        self.processor = None
        self._is_ready = False
        self._vision_ready = False
        self._hf_token = None

        self._hf_token = config.hf_token or os.getenv("HUGGINGFACE_API_TOKEN") or os.getenv("HF_TOKEN")
        if not self._hf_token:
            logger.warning("No HuggingFace token found - set HF_TOKEN or HUGGINGFACE_API_TOKEN")
            return

        try:
            from transformers import AutoProcessor, AutoModel, AutoTokenizer, pipeline

            self.processor = AutoProcessor.from_pretrained(model_name, use_auth_token=self._hf_token)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=self._hf_token)
            self.model = AutoModel.from_pretrained(model_name, use_auth_token=self._hf_token)

            self._generator = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self._has_cuda() else -1,
                max_length=260,
                do_sample=False,
                top_p=0.92,
                temperature=0.7,
            )
            self._is_ready = True
            self._vision_ready = True
            logger.info("GuidanceService initialized Qwen2.5-Omni model with vision capabilities")
        except Exception as e:
            logger.warning(f"Qwen model initialization failed: {e}, falling back to text-only mode")
            try:
                from transformers import AutoProcessor, AutoModel, AutoTokenizer, pipeline
                self.processor = AutoProcessor.from_pretrained(model_name, use_auth_token=self._hf_token)
                self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=self._hf_token)
                self.model = AutoModel.from_pretrained(model_name, use_auth_token=self._hf_token)
                self._generator = pipeline(
                    "text-generation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=0 if self._has_cuda() else -1,
                    max_length=260,
                )
                self._is_ready = True
            except Exception as e2:
                logger.warning(f"Text-only Qwen also failed: {e2}")

    @staticmethod
    def _has_cuda() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False

    def generate_guidance(self, exercise_type: str, user_summary: Dict[str, Any], reference_summary: Optional[Dict[str, Any]] = None) -> str:
        """Generate a textual coaching block for the exercise session"""
        if self._is_ready and self._generator:
            try:
                prompt = self._build_prompt(exercise_type, user_summary, reference_summary)
                result = self._generator(prompt, max_new_tokens=180, num_return_sequences=1)
                if result and isinstance(result, list) and "generated_text" in result[0]:
                    return result[0]["generated_text"]
            except Exception as e:
                logger.warning(f"Health check: Qwen guidance generation failed: {e}")

        # Fallback templated guidance if Qwen isn't available
        return self._fallback_guidance(exercise_type, user_summary, reference_summary)

    def _build_prompt(self, exercise_type: str, user_summary: Dict[str, Any], reference_summary: Optional[Dict[str, Any]]) -> str:
        prompt = [
            f"You are a fitness coach. Analyze the following exercise data for '{exercise_type}' and provide concrete, easy-to-follow guidance.",
            "User video summary:\n" + str(user_summary.get("summary", {})),
            "User overall form score: " + str(user_summary.get("overall_form_score", "unknown")),
        ]

        if reference_summary:
            prompt.append("Reference video summary:\n" + str(reference_summary.get("summary", {})))
            prompt.append("Reference overall form score: " + str(reference_summary.get("overall_form_score", "unknown")))

        prompt.append(
            "Suggest the top 4 improvements, a 2-sentence encouragement, and one reference action sequence for the patient."
        )

        return "\n".join(prompt)

    def _fallback_guidance(self, exercise_type: str, user_summary: Dict[str, Any], reference_summary: Optional[Dict[str, Any]] = None) -> str:
        user_score = round(user_summary.get("overall_form_score", 0), 1)
        ref_score = round(reference_summary.get("overall_form_score", 0), 1) if reference_summary else None

        improvement = "good" if user_score >= 80 else "average" if user_score >= 60 else "needs work"
        reference_note = f" compared with reference score {ref_score}" if ref_score is not None else ""

        return (
            f"Your {exercise_type} form score is {user_score}%. This is {improvement}{reference_note}. "
            "Focus on maintaining a neutral spine, balancing reps equally left and right, and keeping controlled tempo. "
            "Use the follow-through cues: set up at the top, lower in 2 seconds, pause briefly at the bottom, then push up steadily. "
            "For next session, place the feet shoulder-width, engage core, and repeat 8-12 quality reps."
        )

    @staticmethod
    def get_token_guidance() -> Dict[str, str]:
        """Return expected token types for online Qwen/LLM access."""
        return {
            "huggingface": "Set HF_TOKEN environment variable (read scope) - never commit to code",
            "qwen_cloud": "QWEN_API_KEY or ACCESS_TOKEN depending on provider",
            "openai_variant": "OPENAI_API_KEY for OpenAI-compatible layers"
        }

    def motion_to_words(self, keypoints: Dict[str, tuple], additional_context: Optional[str] = None) -> str:
        """Convert pose keypoints to a short movement description."""
        if not keypoints or len(keypoints) < 5:
            return "No valid pose detected to describe movement."

        specifics = []

        # Height variation heuristic
        if "left_knee" in keypoints and "left_hip" in keypoints and "left_ankle" in keypoints:
            knee_y = keypoints["left_knee"][1]
            hip_y = keypoints["left_hip"][1]
            ankle_y = keypoints["left_ankle"][1]

            if knee_y < hip_y and hip_y < ankle_y:
                specifics.append("partial squat position")
            elif knee_y > hip_y and hip_y > ankle_y:
                specifics.append("standing upright")

        # Upper-body lean heuristic
        if "left_shoulder" in keypoints and "left_hip" in keypoints:
            shoulder_y = keypoints["left_shoulder"][1]
            hip_y = keypoints["left_hip"][1]
            if shoulder_y > hip_y + 0.08:
                specifics.append("upper-body lean forward")
            elif shoulder_y < hip_y - 0.08:
                specifics.append("upper-body lean backward")

        text = "The user appears to be " + ", ".join(specifics) if specifics else "The user appears to be in a neutral stance"

        if additional_context:
            text += f"; context: {additional_context}"

        return text

    def classify_exercise_from_description(self, motion_description: str) -> Optional[ExerciseType]:
        """Map motion text to a likely exercise type."""
        if not motion_description:
            return None

        motion_lower = motion_description.lower()

        mapping = {
            "squat": ["squat", "knee", "hip", "lowering"],
            "pushup": ["pushup", "push-up", "hands", "elbow", "floor"],
            "lunge": ["lunge", "forward leg", "back leg"],
            "plank": ["plank", "straight line", "core"],
            "deadlift": ["deadlift", "hinge", "hip hinge"],
            "jumping_jack": ["jumping jack", "jumping", "arms over head"]
        }

        for exercise_key, keywords in mapping.items():
            for keyword in keywords:
                if keyword in motion_lower:
                    try:
                        return ExerciseType(exercise_key)
                    except ValueError:
                        continue

        return None

    def analyze_movement_from_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Use Qwen2.5-Omni vision to analyze movement from a video frame.
        
        Args:
            frame: Video frame as numpy array (H, W, C) in RGB format
            
        Returns:
            Dictionary with movement description and analysis
        """
        result = {
            "movement_description": None,
            "matched_exercise": None,
            "analysis": None,
            "confidence": 0.0,
            "suggested_query": None
        }
        
        if not self._vision_ready or self.processor is None:
            result["movement_description"] = "Vision model not initialized"
            return result
            
        try:
            import torch
            from PIL import Image
            
            pil_image = Image.fromarray(frame)
            
            prompt = """Analyze this image showing a person exercising. Describe:
1. What exercise they appear to be doing
2. Their body position and form
3. Key movement or motion pattern visible
            
Provide a clear 2-3 sentence description of the movement."""
            
            inputs = self.processor(
                text=prompt,
                images=pil_image,
                return_tensors="pt"
            )
            
            if self._has_cuda():
                device = 0
                inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model.generate(**inputs, max_new_tokens=150, do_sample=True, temperature=0.7)
            
            generated_text = self.processor.batch_decode(outputs, skip_special_tokens=True)[0]
            
            movement_desc = generated_text.split("Describe:")[-1].strip() if "Describe:" in generated_text else generated_text
            
            result["movement_description"] = movement_desc
            
            matched = self.classify_exercise_from_description(movement_desc)
            result["matched_exercise"] = matched.value if matched else "unknown"
            
            result["analysis"] = self._analyze_movement_quality(movement_desc)
            result["suggested_query"] = self.suggest_exercise_search_query(movement_desc)
            result["confidence"] = 0.85
            
        except Exception as e:
            logger.warning(f"Vision-based movement analysis failed: {e}")
            result["movement_description"] = f"Analysis failed: {str(e)}"
            
        return result
    
    def _analyze_movement_quality(self, movement_description: str) -> str:
        """Analyze movement quality based on description."""
        if not self._is_ready or not self._generator:
            return self._fallback_quality_analysis(movement_description)
            
        try:
            prompt = f"""Analyze this exercise movement and rate form quality:
Movement: {movement_description}

Provide a one-sentence form quality assessment focusing on proper technique."""
            
            model_output = self._generator(prompt, max_new_tokens=80, num_return_sequences=1)
            if model_output and isinstance(model_output, list) and "generated_text" in model_output[0]:
                return model_output[0]["generated_text"].split("Provide")[-1].strip()
        except Exception as e:
            logger.warning(f"Quality analysis failed: {e}")
            
        return self._fallback_quality_analysis(movement_description)
    
    def _fallback_quality_analysis(self, movement_description: str) -> str:
        """Fallback heuristic-based quality analysis."""
        movement_lower = movement_description.lower()
        
        if any(word in movement_lower for word in ["good", "proper", "correct", "great"]):
            return "Good form - maintain current technique"
        elif any(word in movement_lower for word in ["poor", "wrong", "incorrect", "knees", "back"]):
            return "Form issues detected - focus on controlled movement"
        else:
            return "Controlled tempo recommended throughout the movement"
    
    def suggest_exercise_search_query(self, motion_description: str) -> str:
        """Build a search query the model can use to look up similar exercises."""
        if not motion_description:
            return "exercise form guidance"

        text = re.sub(r"[^a-zA-Z0-9 ,]", "", motion_description)
        return f"find best exercise for movement: {text}"

    def remote_exercise_match(self, motion_description: str) -> Dict[str, Any]:
        """Use Qwen text generation to match the exercise and analyze movement."""
        exercise_result = {
            "motion_description": motion_description,
            "matched_exercise": None,
            "suggested_query": self.suggest_exercise_search_query(motion_description),
            "analysis": None,
            "note": "This method uses local Qwen generation; no external web search is performed by default."
        }

        if self._is_ready and self._generator:
            try:
                prompt = (
                    "Identify the most likely exercise and provide a one-sentence analysis for this motion. "
                    f"Movement description: {motion_description} \n"
                )
                model_output = self._generator(prompt, max_new_tokens=120, num_return_sequences=1)
                if model_output and isinstance(model_output, list) and "generated_text" in model_output[0]:
                    out_text = model_output[0]["generated_text"]
                    exercise_result["analysis"] = out_text

                    # infer exercise type by text
                    inferred = self.classify_exercise_from_description(out_text)
                    if inferred:
                        exercise_result["matched_exercise"] = inferred.value

            except Exception as e:
                logger.warning(f"Qwen remote exercise matching failed: {e}")

        if not exercise_result["matched_exercise"]:
            inferred = self.classify_exercise_from_description(motion_description)
            exercise_result["matched_exercise"] = inferred.value if inferred else "unknown"

        return exercise_result
