"""Ground locked scenes to pixels and export a portable, local research dataset."""
import asyncio
import csv
import io
import json
import zipfile
from pathlib import Path

import cv2
import numpy as np
from meta_sam_parser import decode_mask_to_raster

from meta_client import segment_entity, MOCK_MODE
from storage import session_dir_for


def label_storyboard(record, storyboard, session_id):
    if not storyboard.frames or not all(f.locked for f in storyboard.frames):
        raise RuntimeError("Lock every scene before labeling the dataset.")
    folder = session_dir_for(session_id)
    output = {"images": [], "annotations": [], "categories": [], "matches": [], "mock": MOCK_MODE}
    categories = {}
    for frame in storyboard.frames:
        scene = next(s for s in record.scenes if s.scene_number == frame.scene_number)
        revision = frame.revisions[-1]
        if not revision.image_path:
            if MOCK_MODE:
                continue
            raise RuntimeError("A locked frame has no image.")
        image = cv2.imread(revision.image_path)
        if image is None:
            raise RuntimeError("A storyboard image could not be read.")
        h, w = image.shape[:2]
        overlay = image.copy()
        image_id = frame.scene_number
        output["images"].append({"id": image_id, "file_name": Path(revision.image_path).name, "width": w, "height": h})
        for entity in [*scene.characters, *scene.objects]:
            if entity.id not in categories:
                categories[entity.id] = len(categories) + 1
                output["categories"].append({"id": categories[entity.id], "name": entity.name, "entity_id": entity.id})
            result = asyncio.run(segment_entity(revision.image_path, entity.name))
            masks = [] if result is None else [r for r in result.records if r.kind == "mask"]
            output["matches"].append({"scene_number": image_id, "entity_id": entity.id, "count": len(masks), "ambiguous": len(masks) > 1})
            for mask_record in masks:
                raster = np.frombuffer(decode_mask_to_raster(mask_record.mask), dtype=np.uint8).reshape(mask_record.mask.height, mask_record.mask.width)
                full = np.zeros((h, w), dtype=np.uint8)
                x, y = int(mask_record.bounds.left), int(mask_record.bounds.top)
                mh, mw = raster.shape
                if x < 0 or y < 0 or x + mw > w or y + mh > h:
                    raise RuntimeError("SAM mask bounds do not match the source image.")
                full[y:y+mh, x:x+mw] = raster
                annotation_id = len(output["annotations"]) + 1
                name = f"mask_{annotation_id:04d}.png"
                cv2.imwrite(str(folder / name), full * 255)
                # COCO uncompressed RLE is column-major, starts with a background run.
                counts, prior, run = [], 0, 0
                for value in full.ravel(order="F"):
                    if value == prior:
                        run += 1
                    else:
                        counts.append(run)
                        prior, run = int(value), 1
                counts.append(run)
                ys, xs = np.where(full)
                bbox = [int(xs.min()), int(ys.min()), int(xs.max()-xs.min()+1), int(ys.max()-ys.min()+1)] if len(xs) else [0,0,0,0]
                output["annotations"].append({"id": annotation_id, "image_id": image_id, "category_id": categories[entity.id], "entity_id": entity.id, "segmentation": {"size": [h,w], "counts": counts}, "area": int(full.sum()), "bbox": bbox, "iscrowd": 0, "mask_file": name})
                color = np.array([90, 210, 255], dtype=np.uint8)
                overlay[full > 0] = (overlay[full > 0] * .55 + color * .45).astype(np.uint8)
                cv2.putText(overlay, entity.name, (bbox[0], max(20,bbox[1])), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 2)
        cv2.imwrite(str(folder / f"overlay_{image_id:02d}.png"), overlay)
    (folder / "annotations.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output


def export_dataset(session_id, storyboard):
    """Export only named session artifacts, never credentials or unrelated files."""
    folder = session_dir_for(session_id)
    annotations_path = folder / "annotations.json"
    annotations = json.loads(annotations_path.read_text(encoding="utf-8"))
    names = {"dream_record.json", "dream_coding.json", "storyboard.json", "annotations.json"}
    names.update(image["file_name"] for image in annotations["images"])
    names.update(a["mask_file"] for a in annotations["annotations"])
    names.update(f"overlay_{f.scene_number:02d}.png" for f in storyboard.frames)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names):
            path = folder / name
            if path.is_file() and path.resolve().parent == folder.resolve():
                archive.write(path, name)
        coding_path = folder / "dream_coding.json"
        if coding_path.exists():
            rows = json.loads(coding_path.read_text(encoding="utf-8"))["rows"]
            table = io.StringIO()
            if rows:
                writer = csv.DictWriter(table, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            archive.writestr("coding.csv", table.getvalue())
    return buffer.getvalue()
