import argparse
from loguru import logger
from .config import load_config
from .camera import Camera
from .counter import count_parts
from .events import ChuckEventDetector, EventDetectionConfig
from .db import MySQLClient, MySQLConfig


def main():
    parser = argparse.ArgumentParser(description="connectVision - part counting")
    parser.add_argument("--config", type=str, default=None, help="Path to YAML config")
    parser.add_argument("--preview", action="store_true", help="Show preview window")
    args = parser.parse_args()

    cfg = load_config(args.config)
    cam_cfg = cfg.get("camera", {})
    proc_cfg = cfg.get("processing", {})
    log_cfg = cfg.get("logging", {})
    ev_cfg = cfg.get("events", {})
    sql_cfg = cfg.get("mysql", {})

    if log_cfg.get("level"):
        logger.remove()
        logger.add(lambda msg: print(msg, end=""), level=log_cfg["level"])  # simple sink

    cam = Camera(width=cam_cfg.get("width", 640), height=cam_cfg.get("height", 480))

    roi = proc_cfg.get("roi")  # [x,y,w,h] or None
    if isinstance(roi, list) and len(roi) == 4:
        roi = tuple(roi)
    else:
        roi = None

    thresh = int(proc_cfg.get("threshold", 128))
    min_area = int(proc_cfg.get("min_area", 50))

    # Event detector config
    ev_roi = ev_cfg.get("roi")
    if isinstance(ev_roi, list) and len(ev_roi) == 4:
        ev_roi = tuple(ev_roi)
    else:
        ev_roi = None
    ev_conf = EventDetectionConfig(
        roi=ev_roi,
        diff_threshold=int(ev_cfg.get("diff_threshold", 25)),
        min_event_area=int(ev_cfg.get("min_event_area", 500)),
        debounce_frames=int(ev_cfg.get("debounce_frames", 10)),
    )
    detector = ChuckEventDetector(ev_conf)

    # MySQL client
    mysql_client = MySQLClient(
        MySQLConfig(
            host=str(sql_cfg.get("host", "127.0.0.1")),
            port=int(sql_cfg.get("port", 3306)),
            user=str(sql_cfg.get("user", "root")),
            password=str(sql_cfg.get("password", "")),
            database=str(sql_cfg.get("database", "connectvision")),
            table=str(sql_cfg.get("table", "events")),
        )
    )

    try:
        import cv2
        import numpy as np
    except Exception:
        logger.error("OpenCV not available. Install requirements.")
        return

    logger.info("Starting part counting. Press Ctrl+C to stop.")
    try:
        while True:
            frame = cam.capture()
            if frame is None:
                logger.warning("No frame captured.")
                break
            cnt = count_parts(frame, roi=roi, thresh=thresh, min_area=min_area)
            event = detector.step(frame)
            if event:
                logger.info(f"Event: {event}")
                mysql_client.log_event(event)
            logger.info(f"Count: {cnt}")
            if args.preview:
                vis = frame.copy()
                if roi:
                    x, y, w, h = roi
                    cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(vis, f"Count: {cnt}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                try:
                    cv2.imshow("connectVision", vis)
                    if cv2.waitKey(1) & 0xFF == 27:
                        break
                except Exception:
                    # Headless environment
                    pass
    except KeyboardInterrupt:
        logger.info("Stopping.")
    finally:
        try:
            cam.close()
            mysql_client.close()
            cv2.destroyAllWindows()
        except Exception:
            pass


if __name__ == "__main__":
    main()
