import io, logging, numpy as np
from PIL import Image

logger = logging.getLogger(__name__)
IMG_SIZE = 128

def load_model(path):
    import os, tensorflow as tf
    if not os.path.exists(path):
        logger.warning(f"Model not found: {path} — DEMO mode")
        return None
    interp = tf.lite.Interpreter(model_path=path)
    interp.allocate_tensors()
    logger.info(f"Model loaded: {interp.get_input_details()[0]['shape']}")
    return interp

def predict(interp, image_bytes):
    if interp is None:
        cs = sum(image_bytes[:256]) % 100
        label = "Stroke" if cs > 45 else "Normal"
        conf  = round(0.65 + (cs-45)/200 if label=="Stroke" else 0.70 + cs/250, 4)
        return label, conf
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
    arr = (np.array(img, dtype=np.float32) / 127.5 - 1.0)
    arr = np.expand_dims(arr, 0)
    inp = interp.get_input_details()[0]
    out = interp.get_output_details()[0]
    interp.set_tensor(inp['index'], arr)
    interp.invoke()
    prob  = float(interp.get_tensor(out['index']).ravel()[0])
    label = "Stroke" if prob >= 0.5 else "Normal"
    conf  = prob if label == "Stroke" else 1.0 - prob
    return label, round(conf, 6)

def batch_predict(interp, images):
    return [predict(interp, b) for b in images]

def aggregate(results):
    if len(results) == 1: return results[0]
    ss = [c for l,c in results if l=="Stroke"]
    ns = [c for l,c in results if l=="Normal"]
    if len(ss) >= len(ns):
        return "Stroke", round(sum(ss)/len(ss), 6) if ss else ("Normal", 0.5)
    return "Normal", round(sum(ns)/len(ns), 6)
