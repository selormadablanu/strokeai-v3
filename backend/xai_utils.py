import io, base64, numpy as np
from PIL import Image

ALPHA = 0.45
GRID  = 8

def _jet(v):
    r = np.clip(1.5 - np.abs(4*v-3), 0, 1)
    g = np.clip(1.5 - np.abs(4*v-2), 0, 1)
    b = np.clip(1.5 - np.abs(4*v-1), 0, 1)
    return (np.stack([r,g,b], -1)*255).astype(np.uint8)

def make_heatmap(interp, image_bytes):
    try:
        orig = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        ow, oh = orig.size
        orig_arr = np.array(orig, dtype=np.float32)

        if interp is None:
            # Demo: gaussian blob near right MCA territory
            cx, cy = int(ow*0.62), int(oh*0.38)
            Y, X   = np.ogrid[:oh, :ow]
            sigma  = min(ow, oh)*0.18
            hm = np.exp(-((X-cx)**2+(Y-cy)**2)/(2*sigma**2)).astype(np.float32)
        else:
            from model_utils import IMG_SIZE
            img_r = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((IMG_SIZE,IMG_SIZE))
            arr   = (np.array(img_r,np.float32)/127.5-1.0)
            arr   = np.expand_dims(arr, 0)
            inp_d = interp.get_input_details()[0]
            out_d = interp.get_output_details()[0]
            interp.set_tensor(inp_d['index'], arr)
            interp.invoke()
            baseline = float(interp.get_tensor(out_d['index']).ravel()[0])
            ph, pw   = IMG_SIZE//GRID, IMG_SIZE//GRID
            imp      = np.zeros((GRID,GRID), np.float32)
            for r in range(GRID):
                for c in range(GRID):
                    occ = arr.copy()
                    p   = occ[0, r*ph:(r+1)*ph, c*pw:(c+1)*pw, :]
                    occ[0, r*ph:(r+1)*ph, c*pw:(c+1)*pw, :] = p.mean(axis=(0,1), keepdims=True)
                    interp.set_tensor(inp_d['index'], occ)
                    interp.invoke()
                    imp[r,c] = max(0, baseline - float(interp.get_tensor(out_d['index']).ravel()[0]))
            if imp.max()>1e-8: imp/=imp.max()
            hm = np.array(Image.fromarray((imp*255).astype(np.uint8)).resize((ow,oh),Image.BILINEAR), np.float32)/255.0

        hm_rgb  = _jet(hm)
        blended = np.clip((1-ALPHA)*orig_arr + ALPHA*hm_rgb, 0, 255).astype(np.uint8)
        buf = io.BytesIO()
        Image.fromarray(blended).save(buf, format="PNG", optimize=True)
        return base64.standard_b64encode(buf.getvalue()).decode()
    except Exception as e:
        return None
