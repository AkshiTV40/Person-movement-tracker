class PoseDetectorService {
  constructor() {
    this.pose = null;
    this.isReady = false;
    this.lastResults = null;
    this.onResultsCallback = null;
  }

  async initialize(onResults) {
    if (this.isReady) {
      if (onResults) this.onResultsCallback = onResults;
      return true;
    }

    this.onResultsCallback = onResults;

    try {
      await this.loadMediaPipeScripts();
      
      this.pose = new window.MediaPipePose({
        locateFile: (file) => {
          return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
        }
      });

      this.pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });

      this.pose.onResults((results) => {
        this.lastResults = results;
        if (this.onResultsCallback) {
          this.onResultsCallback(results);
        }
      });

      await this.pose.initialize();
      this.isReady = true;
      console.log('MediaPipe Pose initialized successfully');
      return true;
    } catch (error) {
      console.error('Error initializing MediaPipe Pose:', error);
      return false;
    }
  }

  loadMediaPipeScripts() {
    return new Promise((resolve, reject) => {
      if (window.MediaPipePose) {
        resolve();
        return;
      }

      const scripts = [
        'https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js',
        'https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js',
        'https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js'
      ];

      let loaded = 0;
      scripts.forEach(src => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = () => {
          loaded++;
          if (loaded === scripts.length) {
            resolve();
          }
        };
        script.onerror = reject;
        document.head.appendChild(script);
      });
    });
  }

  async detectPose(imageElement) {
    if (!this.isReady || !this.pose) {
      console.warn('Pose detector not initialized');
      return null;
    }

    try {
      await this.pose.send({ image: imageElement });
      return this.lastResults;
    } catch (error) {
      console.error('Error detecting pose:', error);
      return null;
    }
  }

  getKeypoints() {
    if (!this.lastResults || !this.lastResults.poseLandmarks) {
      return null;
    }
    return this.lastResults.poseLandmarks;
  }

  drawPose(canvasCtx, width, height) {
    if (!this.lastResults) return;

    if (this.lastResults.poseLandmarks && window.drawConnectors && window.drawLandmarks) {
      window.drawConnectors(canvasCtx, this.lastResults.poseLandmarks, window.PosePoseConnections, 
        { color: '#FFFFFF', lineWidth: 2 });
      window.drawLandmarks(canvasCtx, this.lastResults.poseLandmarks, 
        { color: '#00FF00', lineWidth: 2, radius: 4 });
    }
  }

  calculateAngle(a, b, c) {
    if (!a || !b || !c) return null;
    
    const radians = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x);
    let angle = Math.abs(radians * 180.0 / Math.PI);
    
    if (angle > 180.0) {
      angle = 360.0 - angle;
    }
    
    return angle;
  }

  analyzeSquat(landmarks) {
    if (!landmarks || landmarks.length < 33) {
      return { valid: false, error: 'Insufficient landmarks' };
    }

    const getPoint = (idx) => landmarks[idx];
    const leftHip = getPoint(23);
    const leftKnee = getPoint(25);
    const leftAnkle = getPoint(27);
    const rightHip = getPoint(24);
    const rightKnee = getPoint(26);
    const rightAnkle = getPoint(28);
    const leftShoulder = getPoint(11);
    const rightShoulder = getPoint(12);

    if (!leftHip || !leftKnee || !leftAnkle || !rightHip || !rightKnee || !rightAnkle) {
      return { valid: false, error: 'Missing required landmarks' };
    }

    const leftKneeAngle = this.calculateAngle(leftHip, leftKnee, leftAnkle);
    const rightKneeAngle = this.calculateAngle(rightHip, rightKnee, rightAnkle);
    const leftHipAngle = this.calculateAngle(leftShoulder, leftHip, leftKnee);
    const rightHipAngle = this.calculateAngle(rightShoulder, rightHip, rightKnee);

    const avgKneeAngle = (leftKneeAngle + rightKneeAngle) / 2;
    const avgHipAngle = (leftHipAngle + rightHipAngle) / 2;

    let state = 'standing';
    let formScore = 100;
    const issues = [];

    if (avgKneeAngle < 100 && avgHipAngle < 100) {
      state = 'bottom';
    } else if (avgKneeAngle < 140) {
      state = 'descending';
    }

    if (avgKneeAngle > 100 && avgHipAngle > 100) {
      issues.push({ severity: 'warning', message: 'Squat depth insufficient', suggestion: 'Go deeper' });
      formScore -= 15;
    }

    const kneeDiff = Math.abs(leftKneeAngle - rightKneeAngle);
    if (kneeDiff > 20) {
      issues.push({ severity: 'warning', message: 'Uneven knee bend', suggestion: 'Keep knees balanced' });
      formScore -= 10;
    }

    if (leftKnee && leftAnkle && leftKnee.x < leftAnkle.x - 0.05) {
      issues.push({ severity: 'critical', message: 'Left knee valgus', suggestion: 'Push knees out' });
      formScore -= 20;
    }

    if (rightKnee && rightAnkle && rightKnee.x > rightAnkle.x + 0.05) {
      issues.push({ severity: 'critical', message: 'Right knee valgus', suggestion: 'Push knees out' });
      formScore -= 20;
    }

    return {
      valid: true,
      state,
      formScore: Math.max(0, formScore),
      angles: { leftKnee: leftKneeAngle, rightKnee: rightKneeAngle, leftHip: leftHipAngle, rightHip: rightHipAngle },
      issues,
      repCount: state === 'bottom' ? 1 : 0
    };
  }

  analyzePushup(landmarks) {
    if (!landmarks || landmarks.length < 33) {
      return { valid: false, error: 'Insufficient landmarks' };
    }

    const getPoint = (idx) => landmarks[idx];
    const leftShoulder = getPoint(11);
    const leftElbow = getPoint(13);
    const leftWrist = getPoint(15);
    const rightShoulder = getPoint(12);
    const rightElbow = getPoint(14);
    const rightWrist = getPoint(16);
    const leftHip = getPoint(23);
    const rightHip = getPoint(24);

    if (!leftShoulder || !leftElbow || !leftWrist || !leftHip) {
      return { valid: false, error: 'Missing required landmarks' };
    }

    const leftElbowAngle = this.calculateAngle(leftShoulder, leftElbow, leftWrist);
    const rightElbowAngle = this.calculateAngle(rightShoulder, rightElbow, rightWrist);
    const avgElbowAngle = (leftElbowAngle + rightElbowAngle) / 2;

    let state = 'up';
    let formScore = 100;
    const issues = [];

    if (avgElbowAngle < 90) {
      state = 'down';
    } else if (avgElbowAngle < 140) {
      state = 'moving';
    }

    if (avgElbowAngle > 100) {
      issues.push({ severity: 'warning', message: 'Pushup depth insufficient', suggestion: 'Lower deeper' });
      formScore -= 15;
    }

    if (leftHip && rightHip && leftShoulder && rightShoulder) {
      const shoulderY = (leftShoulder.y + rightShoulder.y) / 2;
      const hipY = (leftHip.y + rightHip.y) / 2;
      
      if (hipY > shoulderY + 0.1) {
        issues.push({ severity: 'critical', message: 'Hips sagging', suggestion: 'Keep body straight' });
        formScore -= 20;
      }
    }

    return {
      valid: true,
      state,
      formScore: Math.max(0, formScore),
      angles: { leftElbow: leftElbowAngle, rightElbow: rightElbowAngle },
      issues,
      repCount: state === 'down' ? 1 : 0
    };
  }

  analyzeLunge(landmarks) {
    if (!landmarks || landmarks.length < 33) {
      return { valid: false, error: 'Insufficient landmarks' };
    }

    const getPoint = (idx) => landmarks[idx];
    const leftKnee = getPoint(25);
    const rightKnee = getPoint(26);
    const leftAnkle = getPoint(27);
    const rightAnkle = getPoint(28);
    const leftHip = getPoint(23);
    const rightHip = getPoint(24);

    if (!leftKnee || !rightKnee) {
      return { valid: false, error: 'Missing knee landmarks' };
    }

    let formScore = 100;
    const issues = [];
    let frontLeg = leftKnee.y < rightKnee.y ? 'left' : 'right';

    const frontKneeAngle = frontLeg === 'left' 
      ? this.calculateAngle(leftHip, leftKnee, leftAnkle)
      : this.calculateAngle(rightHip, rightKnee, rightAnkle);

    if (frontKneeAngle > 100) {
      issues.push({ severity: 'warning', message: 'Lunge depth insufficient', suggestion: 'Step deeper' });
      formScore -= 15;
    }

    return {
      valid: true,
      frontLeg,
      formScore: Math.max(0, formScore),
      angles: { frontKnee: frontKneeAngle },
      issues,
      repCount: frontKneeAngle < 90 ? 1 : 0
    };
  }

  analyzePlank(landmarks) {
    if (!landmarks || landmarks.length < 33) {
      return { valid: false, error: 'Insufficient landmarks' };
    }

    const getPoint = (idx) => landmarks[idx];
    const leftShoulder = getPoint(11);
    const rightShoulder = getPoint(12);
    const leftHip = getPoint(23);
    const rightHip = getPoint(24);
    const leftAnkle = getPoint(27);
    const rightAnkle = getPoint(28);

    if (!leftShoulder || !leftHip || !leftAnkle) {
      return { valid: false, error: 'Missing required landmarks' };
    }

    const shoulderY = (leftShoulder.y + rightShoulder.y) / 2;
    const hipY = (leftHip.y + rightHip.y) / 2;
    const ankleY = (leftAnkle.y + rightAnkle.y) / 2;

    let formScore = 100;
    const issues = [];
    const hipDiff = hipY - shoulderY;

    if (hipDiff > 0.15) {
      issues.push({ severity: 'critical', message: 'Hips sagging', suggestion: 'Engage core' });
      formScore -= 20;
    } else if (hipDiff < -0.15) {
      issues.push({ severity: 'warning', message: 'Hips too high', suggestion: 'Lower hips' });
      formScore -= 10;
    }

    return {
      valid: true,
      state: 'holding',
      formScore: Math.max(0, formScore),
      issues,
      repCount: 0
    };
  }

  analyze(exerciseType, landmarks) {
    switch (exerciseType) {
      case 'squat':
        return this.analyzeSquat(landmarks);
      case 'pushup':
        return this.analyzePushup(landmarks);
      case 'lunge':
        return this.analyzeLunge(landmarks);
      case 'plank':
        return this.analyzePlank(landmarks);
      default:
        return { valid: false, error: 'Unknown exercise type' };
    }
  }

  destroy() {
    if (this.pose) {
      this.pose.close();
      this.pose = null;
    }
    this.isReady = false;
    this.lastResults = null;
  }
}

export const poseDetector = new PoseDetectorService();
export default poseDetector;
