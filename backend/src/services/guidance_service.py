import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class GuidanceService:
    """Generate natural-language guidance and comparison suggestions"""

    def __init__(self, model_name: str = "Qwen/Qwen2.5-Omni-7B"):
        self.model_name = model_name
        self.model = None
        self.processor = None
        self._is_ready = False

        # Try lazy initialization; might fail in memory-constrained environments.
        try:
            from transformers import AutoProcessor, AutoModel, AutoTokenizer, pipeline

            self.processor = AutoProcessor.from_pretrained(model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)

            # Text generation pipeline may require a causal version; if AutoModel supports it, it will route.
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
            logger.info("GuidanceService initialized Qwen model")
        except Exception as e:
            logger.warning(f"Qwen model initialization failed: {e}, using fallback guidance")
            self._is_ready = False

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
